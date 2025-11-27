import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline, AutoencoderKL
from PIL import Image
from PIL.PngImagePlugin import PngInfo  # Required for metadata
import os
import gc
import re
from datetime import datetime

class T2IEngine:
    """
    Core class for Text-to-Image generation using Stable Diffusion XL.
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
            
        print("Loading VAE (fp16 fix)...")
        self.vae = AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix", 
            torch_dtype=torch.float16
        )
        return self.vae

    def load_base_model(self, lora_path=None):
        """Loads the Base Pipeline and optionally applies LoRA weights."""
        
        # Check if reload is necessary due to LoRA change
        if self.base_pipeline is not None:
            lora_needs_reload = (lora_path and not self.base_pipeline.has_lora) or \
                                (not lora_path and self.base_pipeline.has_lora)
            if lora_needs_reload:
                print("Model state change detected (LoRA). Reloading Base Pipeline...")
                self.base_pipeline = None 
                self.load_base_model(lora_path=lora_path)
            return

        print(f"Loading Base Model: {self.base_model_id}...")
        vae = self._load_vae()

        # Distinguish between local file and Hugging Face Repo
        if self.base_model_id.endswith(".safetensors") or self.base_model_id.endswith(".ckpt"):
            print("Detected local checkpoint file. Using 'from_single_file'...")
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
        
        self.base_pipeline.has_lora = False

        if lora_path and os.path.exists(lora_path):
            print(f"Loading LoRA from: {lora_path}")
            self.base_pipeline.load_lora_weights(lora_path)
            self.base_pipeline.has_lora = True
        elif lora_path:
             print(f"WARNING: LoRA file not found at {lora_path}")

        self.base_pipeline.enable_model_cpu_offload()
        print("Base Model loaded.")

    def load_refiner_model(self):
        """Loads the Refiner Pipeline if not already active."""
        if self.refiner_pipeline is not None:
            return

        print(f"Loading Refiner Model: {self.refiner_model_id}...")
        vae = self._load_vae()
        
        self.refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            self.refiner_model_id,
            vae=vae, 
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16"
        )
        self.refiner_pipeline.enable_model_cpu_offload()
        print("Refiner Model loaded.")

    def _sanitize_prompt(self, prompt, max_len=50):
        """Sanitizes the prompt to be used as a filename."""
        truncated_prompt = prompt.split(',')[0].split('.')[0].strip()
        if len(truncated_prompt) > max_len:
            truncated_prompt = truncated_prompt[:max_len]
        sanitized = re.sub(r'[^a-zA-Z0-9]+', '_', truncated_prompt)
        return sanitized.strip('_').lower()

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

    def generate(self, prompt, negative_prompt="", steps=30, guidance_scale=7.5, seed=None, use_refiner=False, lora_path=None, lora_scale=1.0):
        """
        Generates an image and saves it with embedded metadata.
        """
        output_path = self._create_output_path(prompt, use_refiner, lora_path)

        # Ensure models are loaded
        self.load_base_model(lora_path=lora_path) 
        if use_refiner:
            self.load_refiner_model()

        # Set Seed
        if seed is None:
            generator = None
            seed_value = "Random" # For metadata
        else:
            generator = torch.Generator(device="cpu").manual_seed(seed)
            seed_value = str(seed)

        print(f"Generating for: '{prompt}' (Refiner: {use_refiner}, LoRA: {lora_path}, Scale: {lora_scale})")
        
        cross_attn_kwargs = {}
        if self.base_pipeline.has_lora:
            cross_attn_kwargs["scale"] = lora_scale

        # --- Inference ---
        if not use_refiner:
            image = self.base_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                cross_attention_kwargs=cross_attn_kwargs if self.base_pipeline.has_lora else None
            ).images[0]
        else:
            # Ensemble of Experts (Base + Refiner)
            high_noise_frac = 0.8
            latents = self.base_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                denoising_end=high_noise_frac, 
                output_type="latent",
                cross_attention_kwargs=cross_attn_kwargs if self.base_pipeline.has_lora else None
            ).images
            
            image = self.refiner_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                denoising_start=high_noise_frac, 
                image=latents,
            ).images[0]

        # --- Save with Metadata (PNG Info) ---
        metadata = PngInfo()
        parameters_txt = (
            f"{prompt}\n"
            f"Negative prompt: {negative_prompt}\n"
            f"Steps: {steps}, CFG scale: {guidance_scale}, Seed: {seed_value}, "
            f"Model: {os.path.basename(self.base_model_id)}, "
            f"LoRA: {os.path.basename(lora_path) if lora_path else 'None'}, "
            f"LoRA Scale: {lora_scale}"
        )
        metadata.add_text("parameters", parameters_txt)
        metadata.add_text("Software", "Python Local T2I Engine")

        image.save(output_path, pnginfo=metadata)
        print(f"Image saved to: {output_path}")
        
        # Cleanup VRAM if needed (optional)
        gc.collect()
        torch.cuda.empty_cache()
        
        return output_path

    def cleanup(self):
        """Explicitly unloads pipelines to free VRAM."""
        print("Unloading pipelines and clearing VRAM...")
        
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
        print("VRAM cleanup complete.")
