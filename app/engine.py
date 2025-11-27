import torch
from diffusers import (
    StableDiffusionXLPipeline, 
    StableDiffusionXLImg2ImgPipeline, 
    AutoencoderKL,
    DPMSolverMultistepScheduler
)
# WICHTIG: Wir nutzen den spezialisierten Wrapper, um 'empty_z' Fehler zu vermeiden
from compel import CompelForSDXL
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import os
import gc
import re
import math
import logging
from datetime import datetime

# Initialize logger for this module
logger = logging.getLogger(__name__)

class T2IEngine:
    """
    Core class for Text-to-Image generation using Stable Diffusion XL.
    Handles model loading, memory management, and image generation.
    Uses CompelForSDXL for robust prompt weighting.
    """
    
    def __init__(self, 
                 base_model_id="stabilityai/stable-diffusion-xl-base-1.0", 
                 refiner_model_id="stabilityai/stable-diffusion-xl-refiner-1.0",
                 device="cuda"):
        self.base_model_id = base_model_id
        self.refiner_model_id = refiner_model_id
        self.device = device
        
        self.base_pipeline = None
        self.refiner_pipeline = None
        self.vae = None
        # Wir speichern Compel nicht persistent, um Device-Konflikte bei Offloading zu vermeiden
        
    def _load_vae(self):
        """Loads the VAE separately so it can be shared between Base and Refiner."""
        if self.vae is not None:
            return self.vae
            
        logger.info("Loading VAE (fp16 fix)...")
        try:
            self.vae = AutoencoderKL.from_pretrained(
                "madebyollin/sdxl-vae-fp16-fix", 
                torch_dtype=torch.float16
            )
            return self.vae
        except Exception as e:
            logger.error(f"Failed to load VAE: {e}")
            raise

    def load_base_model(self, lora_path=None):
        """Loads the Base Pipeline."""
        
        if self.base_pipeline is not None:
            lora_needs_reload = (lora_path and not self.base_pipeline.has_lora) or \
                                (not lora_path and self.base_pipeline.has_lora)
            if lora_needs_reload:
                logger.info("Model state change detected (LoRA). Reloading Base Pipeline...")
                self.base_pipeline = None 
                self.load_base_model(lora_path=lora_path)
            return

        logger.info(f"Loading Base Model: {self.base_model_id}...")
        vae = self._load_vae()

        if self.base_model_id.endswith(".safetensors") or self.base_model_id.endswith(".ckpt"):
            logger.info("Detected local checkpoint file. Using 'from_single_file'...")
            self.base_pipeline = StableDiffusionXLPipeline.from_single_file(
                self.base_model_id,
                vae=vae,
                torch_dtype=torch.float16,
                use_safetensors=True,
            )
        else:
            self.base_pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.base_model_id,
                vae=vae,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16"
            )
        
        # --- Optimizations ---
        self.base_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.base_pipeline.scheduler.config,
            use_karras_sigmas=True,
            algorithm_type="dpmsolver++"
        )

        self.base_pipeline.enable_vae_tiling()
        self.base_pipeline.enable_vae_slicing()
        
        if torch.cuda.is_available():
            try:
                self.base_pipeline.enable_xformers_memory_efficient_attention()
            except Exception:
                self.base_pipeline.enable_attention_slicing()

        # Enable offloading (Crucial for 8GB)
        self.base_pipeline.enable_model_cpu_offload()
        logger.info("Enabled model CPU offload.")

        # LoRA Handling
        self.base_pipeline.has_lora = False
        if lora_path and os.path.exists(lora_path):
            logger.info(f"Loading LoRA from: {lora_path}")
            self.base_pipeline.load_lora_weights(lora_path)
            self.base_pipeline.has_lora = True

        logger.info("Base Model loaded successfully.")

    def load_refiner_model(self):
        """Loads the Refiner Pipeline."""
        if self.refiner_pipeline is not None:
            return

        logger.info(f"Loading Refiner Model: {self.refiner_model_id}...")
        vae = self._load_vae()
        
        self.refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            self.refiner_model_id,
            vae=vae, 
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16"
        )
        self.refiner_pipeline.enable_vae_tiling()
        self.refiner_pipeline.enable_vae_slicing()
        
        self.refiner_pipeline.enable_model_cpu_offload() 
        logger.info("Refiner Model loaded successfully.")

    def _sanitize_prompt(self, prompt, max_len=120):
        """Sanitizes the prompt for filename usage."""
        clean_prompt = re.sub(r'\b(score|source|rating)_\w+', '', prompt, flags=re.IGNORECASE)
        clean_prompt = re.sub(r'\b(masterpiece|best quality)\b', '', clean_prompt, flags=re.IGNORECASE)
        sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', clean_prompt)
        sanitized = re.sub(r'_+', '_', sanitized).strip('_').lower()
        
        if len(sanitized) > max_len:
            sanitized = sanitized[:max_len].rstrip('_')
            
        if not sanitized:
             sanitized = "generated_image"
             
        return sanitized

    def _create_output_path(self, prompt, use_refiner, lora_path=None):
        """Generates a unique file path for the output image."""
        sanitized_name = self._sanitize_prompt(prompt)
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        refiner_suffix = "_refiner" if use_refiner else ""
        lora_suffix = "_lora" if lora_path else "" 
        
        filename = f"{time_str}_{sanitized_name}{lora_suffix}{refiner_suffix}.png"
        output_dir = os.path.join("output_images", date_str)
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename)

    def generate(self, prompt, negative_prompt="", steps=30, guidance_scale=7.5, seed=None, 
                 use_refiner=False, lora_path=None, lora_scale=1.0, 
                 freeu_args=None):
        """
        Generates an image from the prompt using CompelForSDXL.
        Includes robust device handling to fix 'Index on CPU' and 'empty_z' errors.
        """
        output_path = self._create_output_path(prompt, use_refiner, lora_path)

        self.load_base_model(lora_path=lora_path) 
        if use_refiner:
            self.load_refiner_model()

        # Apply FreeU
        if freeu_args:
            logger.info(f"Enabling FreeU with args: {freeu_args}")
            self.base_pipeline.enable_freeu(
                s1=freeu_args.get('s1', 0.9), 
                s2=freeu_args.get('s2', 0.2), 
                b1=freeu_args.get('b1', 1.3), 
                b2=freeu_args.get('b2', 1.4)
            )
        else:
            self.base_pipeline.disable_freeu()

        if seed is None:
            generator = None
            seed_value = "Random"
        else:
            generator = torch.Generator(device="cpu").manual_seed(seed)
            seed_value = str(seed)

        logger.info(f"Generating image. Prompt: '{prompt[:50]}...', Steps: {steps}, FreeU: {bool(freeu_args)}")
        
        try:
            with torch.no_grad():
                # --- MANUAL DEVICE MANAGEMENT START ---
                # 1. Force Text Encoders to GPU.
                # Because we use 'enable_model_cpu_offload', the encoders are normally on CPU.
                # Compel needs them on GPU to work correctly.
                logger.debug("Moving text encoders to GPU for Compel...")
                self.base_pipeline.text_encoder.to(self.device)
                self.base_pipeline.text_encoder_2.to(self.device)

                # 2. Initialize CompelForSDXL FRESH.
                # We pass the pipeline (now with GPU encoders), so Compel correctly detects CUDA.
                # This fixes "Index on CPU" errors.
                # Using CompelForSDXL fixes "empty_z" errors.
                compel = CompelForSDXL(self.base_pipeline)

                # 3. Generate Embeddings
                # CompelForSDXL returns a wrapper object with all necessary tensors.
                conditioning = compel(prompt, negative_prompt=negative_prompt)
                
                # Extract tensors (they will be on CUDA because encoders were on CUDA)
                pos_embeds = conditioning.embeds
                pooled_pos = conditioning.pooled_embeds
                neg_embeds = conditioning.negative_embeds
                pooled_neg = conditioning.negative_pooled_embeds

                # 4. Cleanup: Move encoders back to CPU to free VRAM for the UNet
                logger.debug("Moving text encoders back to CPU...")
                self.base_pipeline.text_encoder.to("cpu")
                self.base_pipeline.text_encoder_2.to("cpu")
                
                # Explicit cleanup of Compel
                del compel
                gc.collect()
                torch.cuda.empty_cache()
                # --- MANUAL DEVICE MANAGEMENT END ---

                cross_attn_kwargs = {}
                if self.base_pipeline.has_lora:
                    cross_attn_kwargs["scale"] = lora_scale

                # --- Inference Process ---
                if not use_refiner:
                    image = self.base_pipeline(
                        prompt_embeds=pos_embeds,
                        pooled_prompt_embeds=pooled_pos,
                        negative_prompt_embeds=neg_embeds,
                        negative_pooled_prompt_embeds=pooled_neg,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        cross_attention_kwargs=cross_attn_kwargs if self.base_pipeline.has_lora else None
                    ).images[0]
                else:
                    high_noise_frac = 0.8
                    
                    latents = self.base_pipeline(
                        prompt_embeds=pos_embeds,
                        pooled_prompt_embeds=pooled_pos,
                        negative_prompt_embeds=neg_embeds,
                        negative_pooled_prompt_embeds=pooled_neg,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        denoising_end=high_noise_frac, 
                        output_type="latent",
                        cross_attention_kwargs=cross_attn_kwargs if self.base_pipeline.has_lora else None
                    ).images
                    
                    gc.collect()
                    torch.cuda.empty_cache()
                    
                    image = self.refiner_pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        denoising_start=high_noise_frac, 
                        image=latents,
                    ).images[0]

                # --- Save with Metadata ---
                metadata = PngInfo()
                parameters_txt = (
                    f"{prompt}\n"
                    f"Negative prompt: {negative_prompt}\n"
                    f"Steps: {steps}, CFG scale: {guidance_scale}, Seed: {seed_value}, "
                    f"Model: {os.path.basename(self.base_model_id)}, "
                    f"Scheduler: DPM++ 2M Karras, "
                    f"FreeU: {bool(freeu_args)}, "
                    f"LoRA: {os.path.basename(lora_path) if lora_path else 'None'}"
                )
                metadata.add_text("parameters", parameters_txt)
                metadata.add_text("Software", "Python Local T2I Engine")

                image.save(output_path, pnginfo=metadata)
                logger.info(f"Image saved successfully to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise
        finally:
            gc.collect()
            torch.cuda.empty_cache()
        
        return output_path

    def cleanup(self):
        """Explicitly unloads pipelines."""
        logger.info("Unloading pipelines and clearing VRAM...")
        
        if self.base_pipeline is not None:
            del self.base_pipeline
            self.base_pipeline = None
        
        if self.refiner_pipeline is not None:
            del self.refiner_pipeline
            self.refiner_pipeline = None
            
        if self.vae is not None:
             del self.vae
             self.vae = None
        
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("VRAM cleanup complete.")
