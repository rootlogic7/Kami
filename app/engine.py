import torch
from diffusers import (
    StableDiffusionXLPipeline, 
    AutoencoderKL,
    DPMSolverMultistepScheduler
)
from compel import CompelForSDXL
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import os
import gc
import re
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Any, Union

# Import Database Function
from app.database import add_image_record, init_db

logger = logging.getLogger(__name__)

class T2IEngine:
    """
    Core backend for Text-to-Image (T2I) generation using SDXL.
    Handles model loading, VAE management, and the generation pipeline.
    Thread-safe implementation for hybrid (local/remote) usage.
    """
    
    def __init__(self, 
                 base_model_id: str = "stabilityai/stable-diffusion-xl-base-1.0", 
                 refiner_model_id: str = "stabilityai/stable-diffusion-xl-refiner-1.0",
                 device: str = "cuda"):
        self.base_model_id = base_model_id
        self.refiner_model_id = refiner_model_id
        self.device = device
        
        self.base_pipeline: Optional[StableDiffusionXLPipeline] = None
        self.refiner_pipeline: Optional[StableDiffusionXLImg2ImgPipeline] = None
        self.vae: Optional[AutoencoderKL] = None
        
        # Mutex lock to prevent concurrent generations from multiple clients
        self.lock = threading.Lock()
        
        # Ensure DB exists
        init_db()
        
    def _load_vae(self) -> AutoencoderKL:
        """Loads the VAE model if not already loaded."""
        if self.vae is not None: 
            return self.vae
            
        logger.info("Loading VAE (fp16-fix)...")
        try:
            self.vae = AutoencoderKL.from_pretrained(
                "madebyollin/sdxl-vae-fp16-fix", 
                torch_dtype=torch.float16
            )
            return self.vae
        except Exception as e:
            logger.error(f"Failed to load VAE: {e}")
            raise

    def load_base_model(self, lora_path: Optional[str] = None) -> None:
        """
        Loads the base SDXL model and optionally applies a LoRA.
        Reloads the pipeline if the LoRA configuration changes.
        """
        # Check if reload is needed based on LoRA presence or change
        if self.base_pipeline is not None:
            has_lora_loaded = getattr(self.base_pipeline, "has_lora", False)
            lora_needs_reload = (lora_path and not has_lora_loaded) or \
                                (not lora_path and has_lora_loaded)
            if lora_needs_reload:
                logger.info("Reloading pipeline due to LoRA change configuration.")
                self.base_pipeline = None
            else:
                return

        logger.info(f"Loading Base Model: {self.base_model_id}")
        vae = self._load_vae()

        try:
            if self.base_model_id.endswith((".safetensors", ".ckpt")):
                self.base_pipeline = StableDiffusionXLPipeline.from_single_file(
                    self.base_model_id, vae=vae, torch_dtype=torch.float16, use_safetensors=True
                )
            else:
                self.base_pipeline = StableDiffusionXLPipeline.from_pretrained(
                    self.base_model_id, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
                )
            
            # Configure Scheduler
            self.base_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.base_pipeline.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++"
            )
            
            # Memory optimizations
            self.base_pipeline.enable_vae_tiling()
            self.base_pipeline.enable_vae_slicing()
            
            if torch.cuda.is_available():
                try: 
                    self.base_pipeline.enable_xformers_memory_efficient_attention()
                except Exception: 
                    logger.warning("xformers not available, using attention slicing.")
                    self.base_pipeline.enable_attention_slicing()

            self.base_pipeline.enable_model_cpu_offload()
            
            # LoRA Handling
            self.base_pipeline.has_lora = False
            if lora_path and os.path.exists(lora_path):
                logger.info(f"Loading LoRA weights from: {lora_path}")
                self.base_pipeline.load_lora_weights(lora_path)
                self.base_pipeline.has_lora = True
                
        except Exception as e:
            logger.error(f"Error loading base model: {e}")
            raise

    def load_refiner_model(self) -> None:
        """Loads the SDXL Refiner model if not already loaded."""
        if self.refiner_pipeline: return
        
        logger.info(f"Loading Refiner: {self.refiner_model_id}")
        try:
            vae = self._load_vae()
            self.refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_pretrained(
                self.refiner_model_id, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
            )
            self.refiner_pipeline.enable_vae_tiling()
            self.refiner_pipeline.enable_vae_slicing()
            self.refiner_pipeline.enable_model_cpu_offload()
        except Exception as e:
            logger.error(f"Error loading refiner: {e}")
            raise

    def _sanitize_prompt(self, prompt: str, max_len: int = 120) -> str:
        """Sanitizes the prompt text for use in filenames."""
        clean = re.sub(r'\b(score|source|rating)_\w+', '', prompt, flags=re.IGNORECASE)
        clean = re.sub(r'\b(masterpiece|best quality)\b', '', clean, flags=re.IGNORECASE)
        sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', clean).strip('_').lower()
        return sanitized[:max_len].rstrip('_') if sanitized else "image"

    def _create_output_path(self, prompt: str, use_refiner: bool, lora_path: Optional[str] = None) -> str:
        """Generates a unique file path for the output image."""
        name = self._sanitize_prompt(prompt)
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        suffix = ""
        if lora_path: suffix += "_lora"
        if use_refiner: suffix += "_refiner"
        
        filename = f"{time_str}_{name}{suffix}.png"
        output_dir = os.path.join("output_images", date_str)
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename)

    def _save_image(self, 
                    image: Image.Image, 
                    output_path: str, 
                    prompt: str, 
                    negative_prompt: str, 
                    steps: int, 
                    guidance_scale: float, 
                    seed_value: Union[str, int], 
                    freeu_args: Optional[Dict[str, float]], 
                    lora_path: Optional[str]) -> None:
        """Saves the generated image with PNG metadata and registers it in the database."""
        metadata = PngInfo()
        parameters_txt = (
            f"{prompt}\nNegative prompt: {negative_prompt}\n"
            f"Steps: {steps}, CFG scale: {guidance_scale}, Seed: {seed_value}, "
            f"Mode: T2I, Model: {os.path.basename(self.base_model_id)}, "
            f"Scheduler: DPM++ 2M Karras, FreeU: {bool(freeu_args)}, "
            f"LoRA: {os.path.basename(lora_path) if lora_path else 'None'}"
        )
        metadata.add_text("parameters", parameters_txt)
        metadata.add_text("Software", "Kami - Local SDXL Station")
        
        try:
            image.save(output_path, pnginfo=metadata)
            logger.info(f"Image saved to: {output_path}")
            
            # DB Update
            add_image_record(
                path=output_path,
                prompt=prompt,
                neg=negative_prompt,
                model=os.path.basename(self.base_model_id),
                steps=steps,
                cfg=guidance_scale,
                seed=seed_value
            )
        except Exception as e:
            logger.error(f"Failed to save image or update DB: {e}")

    def generate(self, 
                 prompt: str, 
                 negative_prompt: str = "", 
                 steps: int = 30, 
                 guidance_scale: float = 7.5, 
                 seed: Optional[int] = None, 
                 use_refiner: bool = False, 
                 lora_path: Optional[str] = None, 
                 lora_scale: float = 1.0, 
                 freeu_args: Optional[Dict[str, float]] = None) -> str:
        """
        Main generation entry point. Thread-safe using self.lock.
        
        Returns:
            str: The file path of the generated image.
        """
        # Acquire lock to ensure only one generation happens at a time
        if not self.lock.acquire(blocking=False):
            logger.warning("Engine is busy. Waiting for lock...")
            self.lock.acquire()
            
        try:
            output_path = self._create_output_path(prompt, use_refiner, lora_path)
            
            self.load_base_model(lora_path) 
            if use_refiner: self.load_refiner_model()

            if self.base_pipeline is None:
                raise RuntimeError("Base pipeline failed to initialize")

            # Apply FreeU settings
            if freeu_args:
                self.base_pipeline.enable_freeu(
                    s1=freeu_args.get('s1', 0.9), s2=freeu_args.get('s2', 0.2), 
                    b1=freeu_args.get('b1', 1.3), b2=freeu_args.get('b2', 1.4)
                )
            else:
                self.base_pipeline.disable_freeu()

            generator = torch.Generator("cpu").manual_seed(seed) if seed is not None else None
            seed_value = str(seed) if seed is not None else "Random"

            logger.info(f"Starting Generation: '{prompt[:50]}...' (Seed: {seed_value})")
            
            with torch.no_grad():
                # Compel Long Prompt Handling
                self.base_pipeline.text_encoder.to(self.device)
                self.base_pipeline.text_encoder_2.to(self.device)
                
                compel = CompelForSDXL(self.base_pipeline)
                if hasattr(compel, 'conditioning_provider'):
                    compel.conditioning_provider.device = self.device
                    
                cond = compel(prompt, negative_prompt=negative_prompt)
                
                # Offload encoders to CPU
                self.base_pipeline.text_encoder.to("cpu")
                self.base_pipeline.text_encoder_2.to("cpu")
                del compel; gc.collect(); torch.cuda.empty_cache()

                kwargs = {"scale": lora_scale} if getattr(self.base_pipeline, "has_lora", False) else None

                if not use_refiner:
                    image = self.base_pipeline(
                        prompt_embeds=cond.embeds, pooled_prompt_embeds=cond.pooled_embeds,
                        negative_prompt_embeds=cond.negative_embeds, negative_pooled_prompt_embeds=cond.negative_pooled_embeds,
                        num_inference_steps=steps, guidance_scale=guidance_scale, generator=generator, cross_attention_kwargs=kwargs
                    ).images[0]
                else:
                    latents = self.base_pipeline(
                        prompt_embeds=cond.embeds, pooled_prompt_embeds=cond.pooled_embeds,
                        negative_prompt_embeds=cond.negative_embeds, negative_pooled_prompt_embeds=cond.negative_pooled_embeds,
                        num_inference_steps=steps, guidance_scale=guidance_scale, generator=generator,
                        denoising_end=0.8, output_type="latent", cross_attention_kwargs=kwargs
                    ).images
                    
                    gc.collect(); torch.cuda.empty_cache()
                    
                    if self.refiner_pipeline is None:
                        raise RuntimeError("Refiner pipeline not initialized")

                    image = self.refiner_pipeline(
                        prompt=prompt, negative_prompt=negative_prompt, num_inference_steps=steps, 
                        guidance_scale=guidance_scale, generator=generator, denoising_start=0.8, image=latents
                    ).images[0]

                self._save_image(image, output_path, prompt, negative_prompt, steps, guidance_scale, seed_value, freeu_args, lora_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
        finally:
            self.lock.release()
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def cleanup(self) -> None:
        """Fully unloads models and clears VRAM."""
        self.base_pipeline = None; self.refiner_pipeline = None; self.vae = None
        gc.collect(); torch.cuda.empty_cache()
        logger.info("Engine cleanup complete.")
