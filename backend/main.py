"""
FastAPI PostGIS Backend for the GeoFire-Agent MVP.
Refactored with Layered Architecture and Centralized Lifespan.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.lifespan import lifespan
from api import projects, runs, pipeline, health, orchestrator_api

# Setup Logging
logger = logging.getLogger("geofire.backend")
logging.basicConfig(level=logging.INFO)

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routers
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(runs.router)
    app.include_router(pipeline.router)
    app.include_router(orchestrator_api.router)

    return app

app = create_app()

import requests
import os

# Internal Docker network aliases
SIMSAT_URL = "http://host.docker.internal:9005/data/image/mapbox" # Or the IP of your host
VISION_SCOUT_URL = "http://vision_edge:8080/analyze-tile"
DAGSTER_URL = "http://dagster:3000/graphql"

async def run_orbital_patrol(lat: float, lon: float):
    """The core loop: Sense -> Think -> Act"""
    
    # 1. SENSE: Pull image from Satellite
    print(f"🛰️ Pulling imagery for {lat}, {lon}...", flush=True)
    
    # Bypassing the local SimSat Docker resolving bug and hitting it directly
    MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "REPLACE_WITH_YOUR_MAPBOX_TOKEN")
    url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},14,0,0/500x500?access_token={MAPBOX_TOKEN}"
    
    try:
        sim_resp = requests.get(url, timeout=10)
        if sim_resp.status_code != 200:
            return {"error": f"Satellite signal lost (Status {sim_resp.status_code})"}
    except Exception as e:
        return {"error": f"API Error: {e}"}

    # 2. THINK: Triage with your fine-tuned Liquid Scout
    print("🧠 Consulting Orbital Scout (Liquid AI)...", flush=True)
    try:
        vision_resp = requests.post(VISION_SCOUT_URL, files={"file": sim_resp.content}, timeout=90)
        analysis = vision_resp.json()
    except Exception as e:
        print(f"Vision edge failed or timed out: {e}")
        analysis = {"error": "Scout Inference Timeout"}
    
    # 3. ACT: Route to Ground Station (Dagster) ONLY if risk is high
    high_fuel = analysis.get("high_fuel_load", False)
    infra_present = analysis.get("infrastructure_present", False)
    
    if high_fuel or infra_present:
        print("🔥 RISK DETECTED. Escalating to Ground Station (Dagster)...")
        # trigger_dagster_pipeline(lat, lon) # Call your existing trigger logic
        status = "ESCALATED TO GIS PIPELINE"
    else:
        print("✅ Area clear. Bandwidth saved.")
        status = "NOMINAL (NO ESCALATION)"

    return {
        "scout_analysis": analysis,
        "agent_decision": status,
        "coordinates": {"lat": lat, "lon": lon}
    }

@app.post("/api/agent/patrol")
async def trigger_patrol(lat: float, lon: float):
    return await run_orbital_patrol(lat, lon)
