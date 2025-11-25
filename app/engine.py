import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
import os
import gc

class T2IEngine:
    """
    Die Kern-Klasse für die Bildgenerierung.
    Kapselt die Komplexität von Diffusers und Speichermanagement.
    """
    
    def __init__(self, model_id="stabilityai/stable-diffusion-xl-base-1.0", device="cuda"):
        self.model_id = model_id
        self.device = device
        self.pipeline = None
        
    def load_model(self):
        """
        Lädt das Modell in den Speicher. 
        Nutzt Optimierungen für 8GB VRAM Karten (float16 + offload).
        """
        if self.pipeline is not None:
            return

        print(f"Lade Modell: {self.model_id}...")
        
        # VAE Fix für bessere Farben/weniger Artefakte bei fp16
        vae = AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix", 
            torch_dtype=torch.float16
        )

        # Pipeline laden
        self.pipeline = StableDiffusionXLPipeline.from_pretrained(
            self.model_id,
            vae=vae,
            torch_dtype=torch.float16,
            use_safetensors=True,
            variant="fp16"
        )

        # WICHTIG für 8GB VRAM:
        # 'enable_model_cpu_offload' schiebt Teile des Modells in den RAM, 
        # wenn sie gerade nicht auf der GPU gebraucht werden.
        # Das ist viel effizienter als 'sequential_cpu_offload'.
        self.pipeline.enable_model_cpu_offload()
        
        # Optional: Slicing hilft, wenn der VRAM sehr knapp wird, macht es aber minimal langsamer
        # self.pipeline.enable_vae_slicing()
        
        print("Modell erfolgreich geladen und optimiert.")

    def generate(self, prompt, negative_prompt="", steps=30, guidance_scale=7.5, seed=None, output_path="output.png"):
        """
        Führt die eigentliche Generierung aus.
        """
        if self.pipeline is None:
            self.load_model()

        # Determinismus für reproduzierbare Ergebnisse
        if seed is None:
            generator = None
        else:
            generator = torch.Generator(device="cpu").manual_seed(seed)

        print(f"Generiere Bild für: '{prompt}'")
        
        image = self.pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator
        ).images[0]

        image.save(output_path)
        print(f"Bild gespeichert unter: {output_path}")
        
        # Speicherbereinigung (Optional, gut für Batch-Processing)
        gc.collect()
        torch.cuda.empty_cache()
        
        return output_path
