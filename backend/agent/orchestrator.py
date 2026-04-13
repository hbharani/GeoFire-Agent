import httpx
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
import asyncio
from services.dagster_service import DagsterService
import uuid

class OrchestratorState(TypedDict):
    tile_image_bytes: Optional[bytes]
    vision_response: Optional[dict]
    routing_decision: Optional[str]
    project_id: Optional[str]

async def fetch_latest_image(state: OrchestratorState):
    print("Node 1: Polling SimSat API for current sentinel image...")
    # Simulated API fetch
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.simsat.space/data/current/image/sentinel", timeout=2.0)
            tile_bytes = response.content
    except Exception:
        # Fallback to dummy bytes for hackathon since SimSat API is mocked
        tile_bytes = b"dummy_image_data_for_now"
    
    return {"tile_image_bytes": tile_bytes}

async def edge_vision_triage(state: OrchestratorState):
    """Send image to the local CPU vision_edge microservice."""
    print("Node 2: Edge Vision Triage")
    tile_bytes = state.get("tile_image_bytes")
    
    if not tile_bytes:
         return {"vision_response": {"anomaly_detected": False, "confidence": 0.0, "description": "No image data"}}

    # In docker, the hostname is 'vision_edge'
    files = {'image': ('tile.jpg', tile_bytes, 'image/jpeg')}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post("http://vision_edge:8080/analyze-tile", files=files)
            if response.status_code == 200:
                vision_json = response.json()
            else:
                vision_json = {"anomaly_detected": False, "confidence": 0.0, "description": f"Failed with {response.status_code}"}
    except Exception as e:
        print(f"Error calling vision_edge: {e}")
        # Default mock fallback for testing
        vision_json = {"anomaly_detected": True, "confidence": 0.85, "description": "Fallback mock: anomaly detected in bounds."}
        
    return {"vision_response": vision_json}

def decide_routing(state: OrchestratorState):
    """Conditional edge based on anomaly detection."""
    vision_response = state.get("vision_response", {})
    if vision_response.get("anomaly_detected") is True:
        print("Routing Decision: Anomaly Detected -> Triggering Downlink")
        return "trigger_dagster"
    else:
        print("Routing Decision: No Anomaly -> Dropping Image")
        return "drop"

async def trigger_postgis_ground_station(state: OrchestratorState):
    """Node 3: Downlink and deep analysis via PostGIS processing in Dagster."""
    print("Node 3: Triggering PostGIS Ground Station Dagster pipeline...")
    project_id = state.get("project_id") or str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    print(f"Flagged area. Project: {project_id}, Run: {run_id}")
    
    # Substitute paths with streaming defaults for the edge scenario
    red_path = "/data/stream_red.tif"
    nir_path = "/data/stream_nir.tif"
    utility_path = "/data/stream_utils.geojson"
    try:
        dagster_res = await DagsterService.trigger_job(
            red_path=red_path,
            nir_path=nir_path,
            utility_path=utility_path,
            canopy_path="",
            swir_path="",
            project_id=project_id,
            run_id=run_id
        )
        return {"routing_decision": "DAGSTER_TRIGGERED"}
    except Exception as e:
        print(f"Dagster trigger failed: {e}")
        return {"routing_decision": f"DAGSTER_FAILED"}

# Build LangGraph 
workflow = StateGraph(OrchestratorState)

workflow.add_node("stream_poller", fetch_latest_image)
workflow.add_node("edge_vision", edge_vision_triage)
workflow.add_node("ground_station", trigger_postgis_ground_station)

workflow.set_entry_point("stream_poller")
workflow.add_edge("stream_poller", "edge_vision")

# Conditional Edge
workflow.add_conditional_edges(
    "edge_vision",
    decide_routing,
    {
        "trigger_dagster": "ground_station",
        "drop": END
    }
)

workflow.add_edge("ground_station", END)

# Compile graph
orchestrator_app = workflow.compile()
