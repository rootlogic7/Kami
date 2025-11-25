import argparse
import sys
import os

# Füge das aktuelle Verzeichnis zum Pfad hinzu, damit wir 'app' importieren können
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.engine import T2IEngine

def main():
    parser = argparse.ArgumentParser(description="Lokaler T2I Generator CLI (SDXL + Refiner)")
    
    # Erforderliches Argument
    parser.add_argument("prompt", type=str, help="Der Text-Prompt für das Bild")
    
    # Optionale Argumente
    parser.add_argument("--neg", type=str, default="ugly, blurry, low quality", help="Negative Prompt (was NICHT im Bild sein soll)")
    parser.add_argument("--steps", type=int, default=30, help="Anzahl der Denoising-Schritte (Qualität)")
    parser.add_argument("--guidance", type=float, default=7.0, help="Wie stark sich das Bild an den Prompt hält (CFG Scale)")
    parser.add_argument("--seed", type=int, default=None, help="Seed für reproduzierbare Ergebnisse")
    parser.add_argument("--output", type=str, default="output.png", help="Dateiname für das Ergebnis")
    
    # NEU: Refiner Switch
    parser.add_argument("--refiner", action="store_true", help="Aktiviert den SDXL Refiner für mehr Details")
    
    args = parser.parse_args()

    # Engine initialisieren
    try:
        engine = T2IEngine()
        engine.generate(
            prompt=args.prompt,
            negative_prompt=args.neg,
            steps=args.steps,
            guidance_scale=args.guidance,
            seed=args.seed,
            output_path=args.output,
            use_refiner=args.refiner # Hier übergeben wir den Switch an die Engine
        )
    except KeyboardInterrupt:
        print("\nAbbruch durch Benutzer.")
    except Exception as e:
        print(f"\nEin Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    main()
