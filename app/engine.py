import torch
from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline, AutoencoderKL
import os
import gc

class T2IEngine:
    """
    Die Kern-Klasse für die Bildgenerierung (SDXL Base + Refiner).
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
        """Lädt den VAE separat, damit Base und Refiner ihn teilen können."""
        if self.vae is not None:
            return self.vae
            
        print("Lade VAE (fp16 fix)...")
        self.vae = AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix", 
            torch_dtype=torch.float16
        )
        return self.vae

    def load_base_model(self):
        if self.base_pipeline is not None:
            return

        print(f"Lade Base Modell: {self.base_model_id}...")
        vae = self._load_vae()

        self.base_pipeline = StableDiffusionXLPipeline.from_pretrained(
            self.base_model_id,
            vae=vae,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16"
        )
        self.base_pipeline.enable_model_cpu_offload()
        print("Base Modell geladen.")

    def load_refiner_model(self):
        if self.refiner_pipeline is not None:
            return

        print(f"Lade Refiner Modell: {self.refiner_model_id}...")
        vae = self._load_vae()
        
        self.refiner_pipeline = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            self.refiner_model_id,
            vae=vae, # Wir nutzen den gleichen VAE -> spart VRAM
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16"
        )
        self.refiner_pipeline.enable_model_cpu_offload()
        print("Refiner Modell geladen.")

    def generate(self, prompt, negative_prompt="", steps=30, guidance_scale=7.5, seed=None, output_path="output.png", use_refiner=False):
        """
        Generiert ein Bild. Wenn use_refiner=True, wird der Prozess aufgeteilt (80% Base, 20% Refiner).
        """
        # 1. Base Modell laden
        self.load_base_model()
        
        # 2. Refiner laden (nur wenn nötig)
        if use_refiner:
            self.load_refiner_model()

        # Seed setzen
        if seed is None:
            generator = None
        else:
            generator = torch.Generator(device="cpu").manual_seed(seed)

        print(f"Generiere Bild für: '{prompt}' (Refiner: {use_refiner})")
        
        # Logik-Weiche: Mit oder ohne Refiner?
        if not use_refiner:
            # Standard Modus: Base macht alles
            image = self.base_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator
            ).images[0]
        else:
            # Refiner Modus: "Ensemble of Experts"
            # High Noise Fraction: Wann übergibt Base an Refiner? 
            # 0.8 bedeutet: Base macht die ersten 80% (viel Rauschen entfernen), Refiner die letzten 20%.
            high_noise_frac = 0.8
            
            # Schritt A: Base Model (gibt Latents aus, kein fertiges Bild)
            latents = self.base_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                denoising_end=high_noise_frac, # Stoppt bei 80%
                output_type="latent"           # WICHTIG: Gib rohe Daten zurück
            ).images
            
            # Schritt B: Refiner Model (nimmt Latents)
            image = self.refiner_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                denoising_start=high_noise_frac, # Startet bei 80%
                image=latents
            ).images[0]

        image.save(output_path)
        print(f"Bild gespeichert unter: {output_path}")
        
        # Cleanup
        gc.collect()
        torch.cuda.empty_cache()
        
        return output_path
