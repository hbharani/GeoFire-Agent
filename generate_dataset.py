import requests
import json
import os

SIMSAT_URL = "http://localhost:9005/data/image/mapbox"
IMAGE_DIR = "./simsat_training_images"
OUTPUT_JSON = "./lfm_finetune_dataset.json"

os.makedirs(IMAGE_DIR, exist_ok=True)

TARGETS = [
    {"name": "urban_infrastructure", "lat": 40.7128, "lon": -74.0060, "type": "urban"},
    {"name": "dense_boreal_fuel", "lat": 52.873, "lon": -118.082, "type": "forest"},
    {"name": "arid_low_risk", "lat": 36.1699, "lon": -115.1398, "type": "arid"}
]

training_data = []

def fetch_mapbox_image(lat, lon, filename):
    print(f"  Requesting {filename}...")
    params = {
        "lat_target": lat, "lon_target": lon,
        "lat_satellite": lat, "lon_satellite": lon, 
        "alt_satellite": 500.0
    }
    
    try:
        response = requests.get(SIMSAT_URL, params=params)
        
        if response.status_code == 200 and response.content.startswith(b'\x89PNG'):
            filepath = os.path.join(IMAGE_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print("    ✅ Downloaded successfully.")
            return filepath
        else:
            print(f"    ❌ Failed. The simulator rejected the Mapbox token or couldn't reach the internet.")
            return None
    except Exception as e:
        print(f"    ❌ API Error: Is the SimSat Docker container running? Details: {e}")
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

print("Initiating Mapbox Extraction...")

for target in TARGETS:
    filename = f"{target['name']}.png"
    filepath = fetch_mapbox_image(target['lat'], target['lon'], filename)
    if filepath:
        training_data.append(build_conversation(filename, target['type']))

with open(OUTPUT_JSON, 'w') as f:
    json.dump(training_data, f, indent=2)

print("\nProcess Complete.")