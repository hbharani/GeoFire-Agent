import requests
import json
import os

# Read Mapbox token from environment (Removed plaintext token to pass GitHub rules)
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "REPLACE_WITH_YOUR_MAPBOX_TOKEN")
IMAGE_DIR = "./simsat_training_images"
OUTPUT_JSON = "./lfm_finetune_dataset.json"

os.makedirs(IMAGE_DIR, exist_ok=True)

TARGETS = [
    {"name": "urban_infrastructure", "lat": 40.7128, "lon": -74.0060, "type": "urban", "zoom": 15},
    {"name": "dense_boreal_fuel", "lat": 52.873, "lon": -118.082, "type": "forest", "zoom": 14},
    {"name": "arid_low_risk", "lat": 36.1699, "lon": -115.1398, "type": "arid", "zoom": 14}
]

training_data = []

def fetch_direct_mapbox(lat, lon, zoom, filename):
    print(f"  Requesting {filename} directly from Mapbox...")
    
    # Direct call to the Mapbox Static Images API
    url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{zoom},0,0/500x500?access_token={MAPBOX_TOKEN}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            filepath = os.path.join(IMAGE_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print("    ✅ Downloaded successfully.")
            return filepath
        else:
            print(f"    ❌ Failed. Status Code: {response.status_code}")
            print(f"    ❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"    ❌ Network Error: {e}")
        return None

def build_conversation(image_filename, terrain_type):
    relative_path = f"simsat_training_images/{image_filename}"
    
    if terrain_type == "urban":
        answer = '{"terrain_classification": "urban", "high_fuel_load": false, "infrastructure_present": true, "risk_assessment": "High infrastructure value, low native fuel load."}'
    elif terrain_type == "forest":
        answer = '{"terrain_classification": "dense_forest", "high_fuel_load": true, "infrastructure_present": false, "risk_assessment": "High continuous fuel load detected. Escalate for PostGIS buffer analysis."}'
    else:
        answer = '{"terrain_classification": "arid_barren", "high_fuel_load": false, "infrastructure_present": false, "risk_assessment": "Low fuel load. Minimal immediate threat."}'

    return {
        "image": relative_path,
        "conversations": [
            {"from": "user", "value": "Analyze this high-resolution satellite tile. Classify the terrain, identify infrastructure presence, and assess the wildland fuel load risk. Respond in strict JSON."},
            {"from": "assistant", "value": answer}
        ]
    }

print("Initiating Direct Mapbox Extraction (Bypassing Docker)...")

for target in TARGETS:
    filename = f"{target['name']}.png"
    filepath = fetch_direct_mapbox(target['lat'], target['lon'], target['zoom'], filename)
    if filepath:
        training_data.append(build_conversation(filename, target['type']))

if len(training_data) > 0:
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(training_data, f, indent=2)
    print("\n✅ Process Complete. Dataset is ready for Colab.")
else:
    print("\n❌ Process failed. No images downloaded.")