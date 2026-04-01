"""
FastAPI PostGIS Backend for the GeoFire-Agent MVP.
Refactored with Layered Architecture and Centralized Lifespan.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.lifespan import lifespan
from api import projects, runs, pipeline, health

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

    return app

app = create_app()
