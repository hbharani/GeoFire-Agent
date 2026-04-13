import requests
import time
import json

# Your backend is exposed on port 8001 (we mapped it earlier)
BACKEND_URL = "http://localhost:8001/api/agent/patrol"

# Define a few target coordinates representing a simulated orbital satellite trajectory
TARGETS = [
    {"name": "Sector Alpha (Urban Infrastructure)", "lat": 40.7128, "lon": -74.0060},
    {"name": "Sector Bravo (Jasper Dense Forest)", "lat": 52.873, "lon": -118.082},
    {"name": "Sector Charlie (Arid Barren Zone)", "lat": 36.1699, "lon": -115.1398}
]

def simulate_orbital_sweep():
    print("🚀 Initiating LEO (Low Earth Orbit) Satellite Patrol Sweep...\n")
    
    for target in TARGETS:
        print(f"🛰️ Analyzing: {target['name']} [Lat: {target['lat']}, Lon: {target['lon']}]")
        print("  => Requesting Agentic Triage...")
        
        try:
            # We hit the endpoint we just created in main.py
            response = requests.post(BACKEND_URL, params={"lat": target['lat'], "lon": target['lon']}, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                
                decision = result.get("agent_decision", "UNKNOWN")
                scout_data = result.get("scout_analysis", {})
                
                # Colorize outputs for hackathon visual wow-factor
                if "ESCALATE" in decision or "ESCALATED" in decision:
                    print(f"  🚨 DECISION: \033[91m{decision}\033[0m")
                else:
                    print(f"  ✅ DECISION: \033[92m{decision}\033[0m")
                    
                print(f"  => Scout Telemetry:")
                print(json.dumps(scout_data, indent=4))
            else:
                print(f"  ❌ Backend Error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network Error connecting to Backend: {e}")
            
        print("-" * 50)
        time.sleep(2) # Simulate orbital travel time between sectors

if __name__ == "__main__":
    simulate_orbital_sweep()
