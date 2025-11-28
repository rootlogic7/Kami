import streamlit as st
import os
from PIL import Image
from engine import T2IEngine

# --- Page Config ---
st.set_page_config(page_title="Local SDXL T2I", layout="wide")

# --- Session State Initialization ---
# Wir nutzen den Session State, um Daten über App-Reruns hinweg zu speichern.
if 'engine' not in st.session_state:
    # Engine wird nur einmal initialisiert
    st.session_state.engine = T2IEngine()

if 'history' not in st.session_state:
    # Liste für die Pfade der generierten Bilder
    st.session_state.history = []

# st.session_state.selected_input_image_path entfernt

# Shortcut für die Engine Instanz
engine = st.session_state.engine

# --- Helper Functions ---
def load_image_from_path(path):
    """Hilfsfunktion, um ein Bild sicher zu laden."""
    try:
        return Image.open(path).convert("RGB")
    except Exception as e:
        st.error(f"Error loading image from path {path}: {e}")
        return None

# set_input_image entfernt

# --- Sidebar UI ---
with st.sidebar:
    st.title("Configuration")
    
    # Modus-Auswahl entfernt
    
    # I2I spezifische Optionen entfernt
    # input_image, strength entfernt

    # Gemeinsame Parameter
    st.header("Prompt Parameters")
    prompt = st.text_area("Positive Prompt", "a cinematic shot of a majestic lion, golden hour lighting, detailed fur, 8k resolution", height=100)
    negative_prompt = st.text_area("Negative Prompt", "blurry, low quality, distorted, ugly, watermark, text", height=100)
    
    steps = st.slider("Steps", 10, 100, 30)
    guidance_scale = st.slider("Guidance Scale (CFG)", 1.0, 20.0, 7.5)
    
    use_seed = st.checkbox("Use specific seed")
    seed = None
    if use_seed:
        seed = st.number_input("Seed value", value=42, step=1, format="%d")

    # --- Advanced Settings ---
    with st.expander("Advanced Settings"):
        st.subheader("Refiner")
        use_refiner = st.checkbox("Enable Refiner (for final polish)")
        
        st.subheader("LoRA")
        lora_path = st.text_input("LoRA File Path (.safetensors)", "")
        lora_scale = st.slider("LoRA Scale", 0.0, 2.0, 1.0)

        st.subheader("FreeU (Experimental)")
        use_freeu = st.checkbox("Enable FreeU")
        freeu_args = None
        if use_freeu:
            c1, c2 = st.columns(2)
            b1 = c1.slider("b1 (Backbone 1)", 1.0, 1.5, 1.3, step=0.05)
            b2 = c2.slider("b2 (Backbone 2)", 1.0, 1.5, 1.4, step=0.05)
            s1 = c1.slider("s1 (Skip 1)", 0.0, 1.0, 0.9, step=0.05)
            s2 = c2.slider("s2 (Skip 2)", 0.0, 1.0, 0.2, step=0.05)
            freeu_args = {"b1": b1, "b2": b2, "s1": s1, "s2": s2}
            
    if st.button("Unload Models (Free VRAM)"):
        engine.cleanup()
        st.success("Models unloaded!")

# --- Main Content Area ---
st.title("SDXL Local Generation Station (Text-to-Image)")

generate_button = st.button("Generate Image", type="primary")

if generate_button:
    # Validierung
    if not prompt:
        st.error("Please enter a positive prompt.")
    # I2I-Validierung entfernt
    else:
        with st.spinner("Generating... Please wait. Check terminal for progress."):
            try:
                # Nur T2I-Aufruf
                output_path = engine.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    steps=steps,
                    guidance_scale=guidance_scale,
                    seed=seed,
                    use_refiner=use_refiner,
                    lora_path=lora_path if lora_path else None,
                    lora_scale=lora_scale,
                    freeu_args=freeu_args
                )
                
                # Erfolgreiche Generierung anzeigen
                st.success(f"Image generated! Saved to: {output_path}")
                st.image(output_path, caption="Generated Image", use_column_width=True)
                
                # Zum Verlauf hinzufügen (neuestes zuerst)
                st.session_state.history.insert(0, output_path)
                
            except Exception as e:
                st.error(f"An error occurred during generation: {e}")
                st.error("Check the terminal logs for more details.")

# --- History Grid View ---
if st.session_state.history:
    st.markdown("---")
    st.subheader("History & Gallery")
    # I2I-Hinweis entfernt
    
    # Grid-Layout erstellen
    cols_per_row = 4
    history_images = st.session_state.history
    
    # Schleife durch die Historie in Blöcken von 4 Bildern
    for i in range(0, len(history_images), cols_per_row):
        cols = st.columns(cols_per_row)
        row_images = history_images[i:i+cols_per_row]
        
        for j, img_path in enumerate(row_images):
            with cols[j]:
                img = load_image_from_path(img_path)
                if img:
                    st.image(img, use_column_width=True)
                    # Button "Use as Input" entfernt
