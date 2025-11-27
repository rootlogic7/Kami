import argparse
import sys
import os
import logging
import traceback

# Add current directory to path to ensure app modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.engine import T2IEngine

# Configure logging to console for CLI usage (or file if preferred)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CLI")

def main():
    parser = argparse.ArgumentParser(description="Local T2I Generator CLI")
    
    # Required arguments
    parser.add_argument("prompt", type=str, help="The text prompt for image generation")
    
    # Optional arguments
    parser.add_argument("--neg", type=str, default="ugly, blurry, low quality", help="Negative prompt")
    parser.add_argument("--steps", type=int, default=30, help="Denoising steps")
    parser.add_argument("--guidance", type=float, default=7.0, help="Guidance scale (CFG)")
    parser.add_argument("--seed", type=int, default=None, help="Seed for reproducibility")
    parser.add_argument("--refiner", action="store_true", help="Enable SDXL Refiner")
    parser.add_argument("--lora", type=str, default=None, help="Path to LoRA file")
    parser.add_argument("--lora-scale", type=float, default=1.0, help="LoRA strength (0.0 to 1.0)")
    parser.add_argument("--model", type=str, default="stabilityai/stable-diffusion-xl-base-1.0", help="Base model path or HF ID")
    
    args = parser.parse_args()

    try:
        logger.info(f"Initializing engine with model: {args.model}")
        engine = T2IEngine(base_model_id=args.model)

        if not (0.0 <= args.lora_scale <= 1.0):
            logger.error("LoRA scale must be between 0.0 and 1.0")
            return

        logger.info(f"Starting generation for prompt: '{args.prompt}'")
        output_path = engine.generate(
            prompt=args.prompt,
            negative_prompt=args.neg,
            steps=args.steps,
            guidance_scale=args.guidance,
            seed=args.seed,
            use_refiner=args.refiner,
            lora_path=args.lora,
            lora_scale=args.lora_scale
        )
        
        print(f"\nSUCCESS: Image saved to: {output_path}")

    except KeyboardInterrupt:
        logger.warning("Process aborted by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    main()
