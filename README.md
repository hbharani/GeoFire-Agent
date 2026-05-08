# GeoFire-Agent

> **Orbital Edge Compute Agent** — Autonomous Satellite Triage & Fire-Risk Platform

## Overview

GeoFire-Agent has evolved from a deterministic PostGIS web-app into a multi-layered **Agentic Orbital Edge Compute** architecture. 

It simulates a low-power Low Earth Orbit (LEO) satellite performing autonomous perimeter sweeps. Imagery is dynamically acquired via Mapbox (or simulated via SimSat) and analyzed locally on edge hardware (CPU-only) using a fine-tuned **LiquidAI/LFM2.5-VL-450M** vision language model. The "Orbital Edge" acts as a bandwidth-saver—only escalating critical infrastructure or dense vegetation fire threats to the heavy downstream **Ground Station (Dagster + PostGIS)** for advanced GIS buffering and risk analysis.

### Service Port Map (Local Environment)

| Service | Address Focus | Description |
|---------|------------|-------------|
| **React Dashboard** | `http://localhost:5173` | Visual interface mapped to the PostGIS results & runs |
| **Dagster System** | `http://localhost:3000` | Ground Station GIS Pipeline Graph Controller |
| **FastAPI Backend** | `http://localhost:8001` | Core Agent API routing & Orchestration (`/api/agent/patrol`) |
| **Vision Scout Edge** | `vision_edge:8080` | Internal CPU-only VLM Inference Microservice |

## Tech Stack & Architecture

| Layer | Technology |
|-------|------------|
| **Edge Vision Inference** | `transformers`, `peft` (LoRA), CPU PyTorch (`vision_edge` microservice) |
| **Fine-Tuning Stack** | Google Colab, HuggingFace `accelerate`, LFM2-VL format |
| **Agent / Orchestrator** | FastAPI `async` routers, `httpx`, LangGraph integration scaffolding |
| **Ground Station GIS** | Dagster, PostGIS 3.4, SQLAlchemy, GeoPandas, Shapely |
| **Ground UI Dashboard** | React 18, Vite, TailwindCSS, React-Leaflet |

```text
GeoFire-Agent/
├── docker-compose.yml           # Bootstraps Postgres, FastAPI, Vision Scout, Dagster, and Vite
├── test_orbital_patrol.py       # Simulates a multi-sector orbital pass hitting the Edge API
├── colab/
│   └── finetune_lfm.ipynb       # Standalone Colab notebook to generate LoRA weights
├── vision_edge/                 # [NEW] Edge CPU visual evaluation microservice
│   ├── app.py                   # Fast inferences on LFM2.5-VL-450M 
│   └── geofire_orbital_weights/ # Mount dir for resulting Colab LoRA adapters
├── backend/                     
│   ├── main.py                  # Hosts the Agentic Patrol logic & API Endpoints
│   └── agent/orchestrator.py    # Multi-node logic triggering Dagster Downlinks
├── dagster_pipeline/            # Heavy raster intersection + buffer jobs
└── frontend/                    # Ground Station GUI
```

## Quick Start

### 1. Model Fine-Tuning (Mandatory for Vision Edge)
The Local Vision Scout requires an expert adapter.
1. Open `colab/finetune_lfm.ipynb` in Google Colab (requires free T4 GPU).
2. It will dynamically fetch training images from the Mapbox API to simulate actual satellite tiles, assemble LFM-VL formatted JSONs, and execute a quick LoRA parameter fine-tune.
3. Download the resulting weights from your Google Drive into the local directory `./vision_edge/geofire_orbital_weights/`.

### 2. Bootstrapping the Local Cluster
Once your weights are secured, boot the main orchestration pipeline:
```bash
# Clone the repository and navigate inside
git clone https://github.com/hbharani/GeoFire-Agent.git
cd GeoFire-Agent

# Build and start all 5 isolated systems native to Docker Compose
docker-compose up -d --build
```

### 3. Initiate the Agentic Patrol
To watch the edge compute logic execute its sweep and conditionally trigger ground downlinks, run the packaged simulation script:
```bash
python test_orbital_patrol.py
```
*Note: Depending on your hardware, the `vision_edge` CPU container can take upwards of ~45s per tile to infer and output its deterministic JSON diagnosis.*

### 4. Review the Ground Station
If an anomaly is escalated by the Scout, track the resulting detailed geo-processing buffers locally at `http://localhost:3000` (Dagster UI), and visually observe the flagged vectors at `http://localhost:5173` (React Dashboard).

## Why CPU-Only Edge Compute?
Hackers naturally scale to the cloud. We restricted the Vision pipeline (`vision_edge`) explicitly to Python 3.13-slim with strict `--index-url cpu` PyTorch constraints. This realistically mimics the extreme power and cooling restrictions a small LEO satellite chassis experiences, demonstrating viability for "Space Hackathon" deploy-to-orbit architectures. Bandwidth to Ground hurts; compute on edge saves it.
