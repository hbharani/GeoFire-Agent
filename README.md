# GeoFire-Agent

> **MVP** — Vegetation & Utility-Line Fire-Risk Platform

## Overview

A full-stack geospatial MVP that lets you upload a satellite GeoTIFF and a utility-line Shapefile/GeoJSON, then automatically triggers an NDVI-based fire-risk analysis pipeline orchestrated by Dagster.

| Service | URL (local) |
|---------|------------|
| React frontend | http://localhost:5173 |
| FastAPI backend | http://localhost:8000 |
| FastAPI docs (Swagger) | http://localhost:8000/docs |
| Dagster webserver | http://localhost:3000 |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, TailwindCSS, react-leaflet (OpenStreetMap) |
| Backend | FastAPI, Uvicorn |
| Orchestration | Dagster |
| Geospatial | GeoPandas, Rasterio, Shapely |
| Infrastructure | Docker Compose |

## Project Structure

```
GeoFire-Agent/
├── docker-compose.yml
├── data/                        # shared data volume (git-ignored)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                  # FastAPI app — upload + Dagster trigger
├── dagster_pipeline/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── workspace.yaml
│   └── pipeline.py              # Dagster job with stubbed ops
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── index.css
        └── App.jsx              # Full-screen map + floating upload panel
```

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/hbharani/GeoFire-Agent.git
cd GeoFire-Agent

# 2. Create the shared data directory
mkdir -p data

# 3. Build and start all services
docker compose up --build

# 4. Open http://localhost:5173 in your browser
```

## Pipeline Steps (stubbed)

1. **ingest_satellite_image** — validate and load a GeoTIFF
2. **ingest_utility_lines** — validate and load a Shapefile or GeoJSON
3. **calculate_vegetation_index** — compute NDVI from NIR/Red bands *(mock)*
4. **mask_and_calculate_risk** — buffer utility lines 30 m and intersect with NDVI *(mock)*

Swap the `[MOCK]` stubs in `dagster_pipeline/pipeline.py` for real `rasterio` / `geopandas` logic when ready.
