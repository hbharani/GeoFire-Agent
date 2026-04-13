from fastapi import APIRouter
from agent.orchestrator import orchestrator_app

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

@router.post("/trigger-cycle")
async def trigger_cycle():
    """Trigger a manual edge compute polling cycle."""
    initial_state = {"project_id": "hackathon_edge_sim"}
    result = await orchestrator_app.ainvoke(initial_state)
    
    # We strip out the raw bytes before returning for a cleaner JSON response
    if "tile_image_bytes" in result:
        result["tile_image_bytes_length"] = len(result["tile_image_bytes"]) if result["tile_image_bytes"] else 0
        del result["tile_image_bytes"]
        
    return {"status": "Complete", "cycle_details": result}
