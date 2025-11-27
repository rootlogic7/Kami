import streamlit as st
import os
from PIL import Image
from engine import T2IEngine

# --- Page Config ---
st.set_page_config(page_title="Local SDXL T2I/I2I", layout="wide")

# --- Session State Initialization ---
# Wir nutzen den Session State, um Daten über App-Reruns hinweg zu speichern.
if 'engine' not in st.session_state:
    # Engine wird nur einmal initialisiert
    st.session_state.engine = T2IEngine()

if 'history' not in st.session_state:
    # Liste für die Pfade der generierten Bilder
    st.session_state.history = []

if 'selected_input_image_path' not in st.session_state:
    # Pfad für ein Bild, das aus der Galerie als Input gewählt wurde
    st.session_state.selected_input_image_path = None

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

def set_input_image(path):
    """Callback-Funktion für die Galerie-Buttons."""
    st.session_state.selected_input_image_path = path
    st.success(f"Set image as input for next generation!")

# --- Sidebar UI ---
with st.sidebar:
    st.title("Configuration")
    
    # Modus-Auswahl
    mode = st.radio("Generation Mode", ["Text-to-Image (T2I)", "Image-to-Image (I2I)"])
    is_i2i_mode = mode == "Image-to-Image (I2I)"

    input_image = None
    strength = 0.75

    # I2I spezifische Optionen
    if is_i2i_mode:
        st.header("I2I Settings")
        # Priorität: Zuerst prüfen, ob ein Bild aus der Galerie gewählt wurde
        if st.session_state.selected_input_image_path:
            st.info("Using selected image from history as input.")
            # Kleines Thumbnail anzeigen
            thumb = load_image_from_path(st.session_state.selected_input_image_path)
            if thumb:
                st.image(thumb, caption="Selected Input", width=150)
            input_image = thumb
            if st.button("Clear Selection"):
                st.session_state.selected_input_image_path = None
                st.experimental_rerun()
        else:
            # Fallback: Datei-Upload
            uploaded_file = st.file_uploader("Upload Input Image", type=["png", "jpg", "jpeg"])
            if uploaded_file is not None:
                input_image = Image.open(uploaded_file).convert("RGB")
                st.image(input_image, caption="Uploaded Input", width=150)

        # Stärke-Regler (nur für I2I relevant)
        strength = st.slider("Strength (Denoising)", min_value=0.0, max_value=1.0, value=0.75, step=0.01, 
                             help="How much to transform the input image. 0.0 = no change, 1.0 = complete change.")

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
st.title("SDXL Local Generation Station")

generate_button = st.button("Generate Image", type="primary")

if generate_button:
    # Validierung
    if not prompt:
        st.error("Please enter a positive prompt.")
    elif is_i2i_mode and input_image is None:
        st.error("Please upload an input image or select one from history for Img2Img mode.")
    else:
        with st.spinner("Generating... Please wait. Check terminal for progress."):
            try:
                # Entscheidung welche Generierungsmethode aufgerufen wird
                if is_i2i_mode:
                    output_path = engine.generate_i2i(
                        prompt=prompt,
                        input_image=input_image,
                        strength=strength,
                        negative_prompt=negative_prompt,
                        steps=steps,
                        guidance_scale=guidance_scale,
                        seed=seed,
                        use_refiner=use_refiner,
                        lora_path=lora_path if lora_path else None,
                        lora_scale=lora_scale,
                        freeu_args=freeu_args
                    )
                else:
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
    st.caption("Click 'Use as Input' to use a generated image for the next Img2Img generation.")
    
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
                    # Button mit Callback-Funktion
                    # WICHTIG: Der key muss eindeutig sein!
                    st.button("Use as Input", 
                              key=f"btn_use_{i}_{j}", 
                              on_click=set_input_image, 
                              args=(img_path,),
                              help="Set this image as input for Img2Img mode.")
