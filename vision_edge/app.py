from fastapi import FastAPI, File, UploadFile
from transformers import AutoProcessor, AutoModelForImageTextToText
from peft import PeftModel
from PIL import Image
import torch
import io
import json

app = FastAPI(title="GeoFire Vision Scout (Edge)")

# Configuration
MODEL_ID = "LiquidAI/LFM2.5-VL-450M"
ADAPTER_PATH = "./geofire_orbital_weights"

print("🚀 Loading Orbital Scout into CPU memory...")
# Load the base model explicitly on CPU
base_model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID, 
    trust_remote_code=True,
    device_map={"": "cpu"} 
)

# Attach your custom fine-tuned weights
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
model.eval()
print("✅ Scout is ready for triage.")

@app.post("/analyze-tile")
async def analyze_tile(file: UploadFile = File(...)):
    # 1. Read and process image
    content = await file.read()
    image = Image.open(io.BytesIO(content)).convert("RGB")
    
    # 2. Prepare the prompt (matching your training format)
    prompt = "<image>\nUSER: Analyze this satellite tile. Classify the terrain, identify infrastructure presence, and assess the wildland fuel load risk. Respond in strict JSON.\nASSISTANT: "
    
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    
    # 3. Inference (CPU)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs, 
            max_new_tokens=128,
            do_sample=False # Keep it deterministic for JSON output
        )
    
    # 4. Decode response
    response_text = processor.batch_decode(output_ids, skip_special_tokens=True)[0]
    
    # Extract the JSON part from the response
    try:
        # Clean up the string to find the JSON block
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        result = json.loads(response_text[json_start:json_end])
    except:
        result = {"raw_output": response_text, "error": "Could not parse JSON"}

    return result

@app.get("/health")
def health():
    return {"status": "active", "device": "cpu"}
