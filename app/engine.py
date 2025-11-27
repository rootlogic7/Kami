import torch
from diffusers import (
    StableDiffusionXLPipeline, 
    StableDiffusionXLImg2ImgPipeline, 
    AutoencoderKL,
    DPMSolverMultistepScheduler
)
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
    Optimized for long prompts and low VRAM (8GB) usage.
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
        """Loads the Base Pipeline and applies optimizations for 8GB VRAM."""
        
        # Check if reload is necessary due to LoRA state change
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

        # Load pipeline based on file type
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
        # 1. Scheduler: DPM++ 2M Karras
        self.base_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.base_pipeline.scheduler.config,
            use_karras_sigmas=True,
            algorithm_type="dpmsolver++"
        )

        # 2. VAE Optimizations (Crucial for OOM prevention)
        self.base_pipeline.enable_vae_tiling()
        self.base_pipeline.enable_vae_slicing()
        
        # 3. Memory Efficient Attention
        if torch.cuda.is_available():
            try:
                self.base_pipeline.enable_xformers_memory_efficient_attention()
            except Exception:
                self.base_pipeline.enable_attention_slicing()

        # 4. Low VRAM Strategy: Sequential CPU Offload
        self.base_pipeline.enable_sequential_cpu_offload()
        logger.info("Enabled sequential CPU offload for low VRAM.")

        # LoRA Handling
        self.base_pipeline.has_lora = False
        if lora_path and os.path.exists(lora_path):
            logger.info(f"Loading LoRA from: {lora_path}")
            self.base_pipeline.load_lora_weights(lora_path)
            self.base_pipeline.has_lora = True

        logger.info("Base Model loaded and optimized successfully.")

    def load_refiner_model(self):
        """Loads the Refiner Pipeline if not already active."""
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
        
        # Apply strict offloading to refiner as well
        self.refiner_pipeline.enable_sequential_cpu_offload()
        logger.info("Refiner Model loaded successfully with sequential offload.")

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

    def get_long_prompt_embeds(self, pipeline, prompt, negative_prompt):
        """
        Calculates embeddings for long prompts with memory safety.
        Assumes implicit torch.no_grad() context from caller.
        """
        if not prompt: prompt = ""
        if not negative_prompt: negative_prompt = ""

        tokenizers = [pipeline.tokenizer, pipeline.tokenizer_2] if hasattr(pipeline, "tokenizer_2") else [pipeline.tokenizer]
        text_encoders = [pipeline.text_encoder, pipeline.text_encoder_2] if hasattr(pipeline, "text_encoder_2") else [pipeline.text_encoder]

        # 1. Tokenize (CPU is fine for this)
        def tokenize(tokenizer, text):
            return tokenizer(text, return_tensors="pt", truncation=False).input_ids.to(self.device)

        input_ids_list_pos = []
        input_ids_list_neg = []
        
        for tokenizer in tokenizers:
            input_ids_list_pos.append(tokenize(tokenizer, prompt))
            input_ids_list_neg.append(tokenize(tokenizer, negative_prompt))

        # 2. Determine max length and target length
        max_len = 0
        for ids in input_ids_list_pos + input_ids_list_neg:
            if ids.shape[-1] > max_len: max_len = ids.shape[-1]

        target_len = 77
        if max_len > 77:
            target_len = math.ceil(max_len / 77) * 77

        # 3. Helper to pad and encode
        def encode_padded(tokenizer, text_encoder, input_ids, target_length):
            curr_len = input_ids.shape[-1]
            if curr_len < target_length:
                pad_len = target_length - curr_len
                pad_tensor = torch.full((1, pad_len), tokenizer.pad_token_id, dtype=torch.long, device=self.device)
                input_ids = torch.cat([input_ids, pad_tensor], dim=1)
            
            embeds = []
            for i in range(0, target_length, 77):
                chunk = input_ids[:, i:i+77]
                out = text_encoder(chunk, output_hidden_states=True)
                embeds.append(out.hidden_states[-2])
            
            return torch.cat(embeds, dim=1)

        # 4. Process embeddings
        prompt_embeds_list = []
        neg_embeds_list = []

        for i, (tokenizer, text_encoder) in enumerate(zip(tokenizers, text_encoders)):
            pos_emb = encode_padded(tokenizer, text_encoder, input_ids_list_pos[i], target_len)
            prompt_embeds_list.append(pos_emb)
            
            neg_emb = encode_padded(tokenizer, text_encoder, input_ids_list_neg[i], target_len)
            neg_embeds_list.append(neg_emb)
            
            # Memory Cleanup after each encoder usage
            gc.collect()
            torch.cuda.empty_cache()

        if len(prompt_embeds_list) == 2:
            prompt_embeds = torch.cat([prompt_embeds_list[0], prompt_embeds_list[1]], dim=-1)
            negative_prompt_embeds = torch.cat([neg_embeds_list[0], neg_embeds_list[1]], dim=-1)
        else:
            prompt_embeds = prompt_embeds_list[0]
            negative_prompt_embeds = neg_embeds_list[0]

        # 5. Pooled Embeddings
        tokenizer_2 = pipeline.tokenizer_2 if hasattr(pipeline, "tokenizer_2") else pipeline.tokenizer
        text_encoder_2 = pipeline.text_encoder_2 if hasattr(pipeline, "text_encoder_2") else pipeline.text_encoder
        
        def get_pooled(txt):
            inputs = tokenizer_2(txt, padding="max_length", max_length=77, truncation=True, return_tensors="pt").to(self.device)
            return text_encoder_2(inputs.input_ids, output_hidden_states=True).text_embeds
        
        pooled_pos = get_pooled(prompt)
        pooled_neg = get_pooled(negative_prompt)

        # Final cleanup
        gc.collect()
        torch.cuda.empty_cache()
        
        return prompt_embeds, negative_prompt_embeds, pooled_pos, pooled_neg

    def generate(self, prompt, negative_prompt="", steps=30, guidance_scale=7.5, seed=None, 
                 use_refiner=False, lora_path=None, lora_scale=1.0, 
                 freeu_args=None):
        """
        Generates an image from the prompt. 
        Supports FreeU via freeu_args (dict).
        """
        output_path = self._create_output_path(prompt, use_refiner, lora_path)

        # Ensure required models are loaded
        self.load_base_model(lora_path=lora_path) 
        if use_refiner:
            self.load_refiner_model()

        # Apply FreeU settings dynamically
        if freeu_args:
            logger.info(f"Enabling FreeU with args: {freeu_args}")
            # s1: stage 1 backbone factor, s2: stage 2 backbone factor
            # b1: stage 1 skip factor, b2: stage 2 skip factor
            self.base_pipeline.enable_freeu(
                s1=freeu_args.get('s1', 0.9), 
                s2=freeu_args.get('s2', 0.2), 
                b1=freeu_args.get('b1', 1.3), 
                b2=freeu_args.get('b2', 1.4)
            )
        else:
            # Disable FreeU if not requested
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
                # --- Handle Long Prompts ---
                pos_embeds, neg_embeds, pooled_pos, pooled_neg = self.get_long_prompt_embeds(
                    self.base_pipeline, prompt, negative_prompt
                )

                cross_attn_kwargs = {}
                if self.base_pipeline.has_lora:
                    cross_attn_kwargs["scale"] = lora_scale

                # --- Final Pre-Generation Cleanup ---
                gc.collect()
                torch.cuda.empty_cache()

                # --- Inference Process ---
                if not use_refiner:
                    image = self.base_pipeline(
                        prompt_embeds=pos_embeds,
                        negative_prompt_embeds=neg_embeds,
                        pooled_prompt_embeds=pooled_pos,
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
                        negative_prompt_embeds=neg_embeds,
                        pooled_prompt_embeds=pooled_pos,
                        negative_pooled_prompt_embeds=pooled_neg,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        denoising_end=high_noise_frac, 
                        output_type="latent",
                        cross_attention_kwargs=cross_attn_kwargs if self.base_pipeline.has_lora else None
                    ).images
                    
                    # Manual cleanup between Base and Refiner
                    gc.collect()
                    torch.cuda.empty_cache()
                    
                    # Note: FreeU is usually not applied to Refiner in this workflow to keep style consistent
                    # But can be added if desired.
                    
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
