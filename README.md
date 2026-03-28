# GeoFire-Agent

> **Enterprise-Ready** — Vegetation & Utility-Line Fire-Risk Platform

## Overview

A full-stack geospatial platform that lets you define tracking Workspaces, upload satellite GeoTIFFs (Red, NIR, and optional Canopy Height Models) and Utility-Line infrastructure, and then automatically triggers a high-performance NDVI-based fire-risk analysis pipeline orchestrated by Dagster.

Crucially, the entire agent runs off a C-optimized **PostgreSQL / PostGIS** database backend to natively compute vector intersections and strictly organize analysis data under isolated `Project` and `AnalysisRun` contexts.

| Service | URL (local) |
|---------|------------|
| React Frontend | http://localhost:5173 |
| FastAPI Backend | http://localhost:8000 |
| FastAPI Docs | http://localhost:8000/docs |
| Dagster Webserver | http://localhost:3000 |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS, React-Leaflet |
| Backend | FastAPI, SQLAlchemy, GeoAlchemy2, Uvicorn |
| Database | PostgreSQL 15, PostGIS 3.4 |
| Orchestration | Dagster |
| Geospatial Compute | GeoPandas, Rasterio, Shapely |
| Infrastructure | Docker Compose |

## Architecture Structure

```text
GeoFire-Agent/
├── docker-compose.yml           # Bootstraps Postgres, FastAPI, Dagster, and Vite
├── backend/
│   ├── database.py              # SQLAlchemy engine bound to async lifespans
│   ├── models.py                # Project, AnalysisRun, and GeospatialAsset schemas
│   └── main.py                  # Routing endpoints + Dagster telemetry interceptors
├── dagster_pipeline/
│   └── pipeline.py              # Compute graph handling chunked EWKT PostGIS batching
└── frontend/
    └── src/
        ├── components/
        │   ├── Dashboard.jsx    # Active grid module for handling Project CRUD
        │   └── MapWorkspace.jsx # Leaflet map with overlaid UI Analysis History tabs
        └── App.jsx              # Lightweight UI Context router
```

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/hbharani/GeoFire-Agent.git
cd GeoFire-Agent

# 2. Build and start all services natively
# (The Postgres DB requires time to boot its TCP layer)
docker compose up -d --build

# 3. Open http://localhost:5173 in your browser!

# 4. Download Sample Data
# Head over to the Releases tab on GitHub to download `geofire_sample_data.zip`. 
# Extract it to securely retrieve the original Red, NIR, and Utility Line files without bloating Git!
```

## System Workflow Pipeline

Instead of dragging huge flat `.geojson` outputs out to the UI, the GeoFire backend natively translates calculations straight into binary database mappings:

1. **Ingestion** — API caches Multi-spectral TIFF layers (Red, NIR, Canopy Height) on disk and maps their path string boundaries.
2. **Buffer Operations** — Identifies shape intersections, and isolates utility bounds exactly matching active target grids.
3. **Vegetation & Canopy Classification** — Evaluates spectral boundaries `((NIR - Red) / (NIR + Red))` and integrates CHM verticality to map Low, Medium, and High foliage threat sectors.
4. **PostGIS Chunk Sync** — Overrides strict Python geometry processing and relies on raw `SQLAlchemy Core` to batch inject vectors dynamically formatted as `"SRID=4326;{geometry}"` cleanly isolated by `run_id`.
5. **Dynamic UI Rendering** — The interface isolates execution histories dynamically utilizing `ST_AsGeoJSON()`.

## Future Work

This V1 MVP demonstrates high-performance spatial orchestration, but the analytical models will be expanded in future versions based on interest and specific utility needs:

- **True Fuel Moisture (NDMI)**: Integrating SWIR (Shortwave Infrared) bands alongside NDVI to dynamically calculate the physical water-content of vegetation (dry dead timber vs healthy wet forests).
- **Topographical Scalars (DEM)**: Utilizing Digital Elevation Models to scale fire-spread risk exponentially across steeply inclined transmission line right-of-ways.
- **Meteorological API Integration**: Layering live relative humidity, ambient temperature, and wind-vector data onto the localized threat score.
- **Advanced Canopy Strike Models**: Further utilizing the Canopy Height Model (CHM) ingest layer to calculate physical fall/strike risks from timber dynamically encroaching into utility easement cylinders.
- **Multi-Agent Orchestration (LangGraph & LLMs)**: Evolving the platform from a deterministic GIS pipeline into a true Agentic workflow. Future iterations will integrate LangGraph to autonomously query the highest-risk PostGIS threat polygons, cross-reference them with maintenance budgets or regulatory compliance documents via RAG, and generate prioritized, human-readable vegetation management reports for utility dispatch crews.
