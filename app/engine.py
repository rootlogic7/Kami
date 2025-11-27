import torch
from diffusers import (
    StableDiffusionXLPipeline, 
    StableDiffusionXLImg2ImgPipeline, 
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
from datetime import datetime

# Import Database Function
from app.database import add_image_record, init_db

logger = logging.getLogger(__name__)

class T2IEngine:
    """Core backend for T2I and I2I generation."""
    
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
        
        # Ensure DB exists
        init_db()
        
    def _load_vae(self):
        if self.vae is not None: return self.vae
        logger.info("Loading VAE...")
        self.vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
        return self.vae

    def load_base_model(self, lora_path=None):
        if self.base_pipeline is not None:
            lora_needs_reload = (lora_path and not self.base_pipeline.has_lora) or \
                                (not lora_path and self.base_pipeline.has_lora)
            if lora_needs_reload:
                self.base_pipeline = None
            else:
                return

        logger.info(f"Loading Base Model: {self.base_model_id}")
        vae = self._load_vae()

        if self.base_model_id.endswith((".safetensors", ".ckpt")):
            self.base_pipeline = StableDiffusionXLPipeline.from_single_file(
                self.base_model_id, vae=vae, torch_dtype=torch.float16, use_safetensors=True
            )
        else:
            self.base_pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.base_model_id, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
            )
        
        self.base_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.base_pipeline.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++"
        )
        self.base_pipeline.enable_vae_tiling()
        self.base_pipeline.enable_vae_slicing()
        
        if torch.cuda.is_available():
            try: self.base_pipeline.enable_xformers_memory_efficient_attention()
            except: self.base_pipeline.enable_attention_slicing()

        self.base_pipeline.enable_model_cpu_offload()
        
        self.base_pipeline.has_lora = False
        if lora_path and os.path.exists(lora_path):
            self.base_pipeline.load_lora_weights(lora_path)
            self.base_pipeline.has_lora = True

    def load_refiner_model(self):
        if self.refiner_pipeline: return
        logger.info("Loading Refiner...")
        vae = self._load_vae()
        self.refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            self.refiner_model_id, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
        )
        self.refiner_pipeline.enable_vae_tiling()
        self.refiner_pipeline.enable_vae_slicing()
        self.refiner_pipeline.enable_model_cpu_offload()

    def _sanitize_prompt(self, prompt, max_len=120):
        clean = re.sub(r'\b(score|source|rating)_\w+', '', prompt, flags=re.IGNORECASE)
        clean = re.sub(r'\b(masterpiece|best quality)\b', '', clean, flags=re.IGNORECASE)
        sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', clean).strip('_').lower()
        return sanitized[:max_len].rstrip('_') if sanitized else "image"

    def _create_output_path(self, prompt, use_refiner, lora_path=None, is_i2i=False):
        name = self._sanitize_prompt(prompt)
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        suffix = ""
        if is_i2i: suffix += "_i2i"
        if lora_path: suffix += "_lora"
        if use_refiner: suffix += "_refiner"
        
        filename = f"{time_str}_{name}{suffix}.png"
        output_dir = os.path.join("output_images", date_str)
        os.makedirs(output_dir, exist_ok=True)
        return os.path.join(output_dir, filename)

    def _save_image(self, image, output_path, prompt, negative_prompt, steps, guidance_scale, seed_value, freeu_args, lora_path, mode_info):
        metadata = PngInfo()
        parameters_txt = (
            f"{prompt}\nNegative prompt: {negative_prompt}\n"
            f"Steps: {steps}, CFG scale: {guidance_scale}, Seed: {seed_value}, "
            f"Mode: {mode_info}, Model: {os.path.basename(self.base_model_id)}, "
            f"Scheduler: DPM++ 2M Karras, FreeU: {bool(freeu_args)}, "
            f"LoRA: {os.path.basename(lora_path) if lora_path else 'None'}"
        )
        metadata.add_text("parameters", parameters_txt)
        metadata.add_text("Software", "Python Local T2I Engine")
        image.save(output_path, pnginfo=metadata)
        
        # --- DB UPDATE ---
        add_image_record(
            path=output_path,
            prompt=prompt,
            neg=negative_prompt,
            model=os.path.basename(self.base_model_id),
            steps=steps,
            cfg=guidance_scale,
            seed=seed_value
        )
        logger.info(f"Image saved and indexed: {output_path}")

    def generate(self, prompt, negative_prompt="", steps=30, guidance_scale=7.5, seed=None, 
                 use_refiner=False, lora_path=None, lora_scale=1.0, freeu_args=None):
        output_path = self._create_output_path(prompt, use_refiner, lora_path, False)
        self.load_base_model(lora_path) 
        if use_refiner: self.load_refiner_model()

        if freeu_args:
            self.base_pipeline.enable_freeu(s1=freeu_args['s1'], s2=freeu_args['s2'], b1=freeu_args['b1'], b2=freeu_args['b2'])
        else:
            self.base_pipeline.disable_freeu()

        generator = torch.Generator("cpu").manual_seed(seed) if seed is not None else None
        seed_value = str(seed) if seed is not None else "Random"

        logger.info(f"Generating T2I: {prompt[:50]}...")
        
        try:
            with torch.no_grad():
                # Manual Device Management for Compel + Offload
                self.base_pipeline.text_encoder.to(self.device)
                self.base_pipeline.text_encoder_2.to(self.device)
                
                compel = CompelForSDXL(self.base_pipeline)
                if hasattr(compel, 'conditioning_provider'):
                    compel.conditioning_provider.device = self.device
                    
                cond = compel(prompt, negative_prompt=negative_prompt)
                
                self.base_pipeline.text_encoder.to("cpu")
                self.base_pipeline.text_encoder_2.to("cpu")
                del compel; gc.collect(); torch.cuda.empty_cache()

                kwargs = {"scale": lora_scale} if self.base_pipeline.has_lora else None

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
                    image = self.refiner_pipeline(
                        prompt=prompt, negative_prompt=negative_prompt, num_inference_steps=steps, 
                        guidance_scale=guidance_scale, generator=generator, denoising_start=0.8, image=latents
                    ).images[0]

                self._save_image(image, output_path, prompt, negative_prompt, steps, guidance_scale, seed_value, freeu_args, lora_path, "T2I")
            
        except Exception as e:
            logger.error(f"Generation Error: {e}"); raise
        finally:
            gc.collect(); torch.cuda.empty_cache()
        return output_path

    def generate_i2i(self, prompt, input_image, strength=0.75, negative_prompt="", steps=30, guidance_scale=7.5, seed=None,
                     use_refiner=False, lora_path=None, lora_scale=1.0, freeu_args=None):
        output_path = self._create_output_path(prompt, use_refiner, lora_path, True)
        self.load_base_model(lora_path)
        if use_refiner: self.load_refiner_model()

        if freeu_args:
            self.base_pipeline.enable_freeu(s1=freeu_args['s1'], s2=freeu_args['s2'], b1=freeu_args['b1'], b2=freeu_args['b2'])
        else:
            self.base_pipeline.disable_freeu()

        generator = torch.Generator("cpu").manual_seed(seed) if seed is not None else None
        seed_value = str(seed) if seed is not None else "Random"

        logger.info(f"Generating I2I: {prompt[:50]}...")
        
        try:
            with torch.no_grad():
                self.base_pipeline.text_encoder.to(self.device)
                self.base_pipeline.text_encoder_2.to(self.device)
                
                compel = CompelForSDXL(self.base_pipeline)
                if hasattr(compel, 'conditioning_provider'):
                    compel.conditioning_provider.device = self.device
                
                cond = compel(prompt, negative_prompt=negative_prompt)
                
                self.base_pipeline.text_encoder.to("cpu")
                self.base_pipeline.text_encoder_2.to("cpu")
                del compel; gc.collect(); torch.cuda.empty_cache()

                kwargs = {"scale": lora_scale} if self.base_pipeline.has_lora else None
                i2i_pipe = StableDiffusionXLImg2ImgPipeline(**self.base_pipeline.components)

                if not use_refiner:
                    image = i2i_pipe(
                        image=input_image, strength=strength,
                        prompt_embeds=cond.embeds, pooled_prompt_embeds=cond.pooled_embeds,
                        negative_prompt_embeds=cond.negative_embeds, negative_pooled_prompt_embeds=cond.negative_pooled_embeds,
                        num_inference_steps=steps, guidance_scale=guidance_scale, generator=generator, cross_attention_kwargs=kwargs
                    ).images[0]
                else:
                    latents = i2i_pipe(
                        image=input_image, strength=strength,
                        prompt_embeds=cond.embeds, pooled_prompt_embeds=cond.pooled_embeds,
                        negative_prompt_embeds=cond.negative_embeds, negative_pooled_prompt_embeds=cond.negative_pooled_embeds,
                        num_inference_steps=steps, guidance_scale=guidance_scale, generator=generator,
                        denoising_end=0.8, output_type="latent", cross_attention_kwargs=kwargs
                    ).images
                    gc.collect(); torch.cuda.empty_cache()
                    image = self.refiner_pipeline(
                        prompt=prompt, negative_prompt=negative_prompt, num_inference_steps=steps, 
                        guidance_scale=guidance_scale, generator=generator, denoising_start=0.8, image=latents
                    ).images[0]
                
                del i2i_pipe
                self._save_image(image, output_path, prompt, negative_prompt, steps, guidance_scale, seed_value, freeu_args, lora_path, f"I2I (Str:{strength})")
            
        except Exception as e:
            logger.error(f"I2I Error: {e}"); raise
        finally:
            gc.collect(); torch.cuda.empty_cache()
        return output_path

    def cleanup(self):
        self.base_pipeline = None; self.refiner_pipeline = None; self.vae = None
        gc.collect(); torch.cuda.empty_cache()
