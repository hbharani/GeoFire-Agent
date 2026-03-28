"""
FastAPI PostGIS Backend for the GeoFire-Agent MVP.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from database import engine, Base, get_db
from models import Project, GeospatialAsset, AnalysisRun

logger = logging.getLogger("geofire.backend")
logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Natively defer Database metadata execution until active server boot
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="GeoFire-Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DAGSTER_HOST = os.getenv("DAGSTER_HOST", "dagster")
DAGSTER_PORT = os.getenv("DAGSTER_PORT", "3000")
DAGSTER_URL = f"http://{DAGSTER_HOST}:{DAGSTER_PORT}/graphql"

DATA_DIR.mkdir(parents=True, exist_ok=True)

class ProjectCreate(BaseModel):
    name: str

async def _save_upload(upload: UploadFile, destination: Path) -> None:
    contents = await upload.read()
    destination.write_bytes(contents)

LAUNCH_RUN_MUTATION = """
mutation LaunchRun($config: RunConfigData!, $jobName: String!, $repositoryLocationName: String!, $repositoryName: String!) {
  launchRun(
    executionParams: {
      selector: {
        jobName: $jobName
        repositoryLocationName: $repositoryLocationName
        repositoryName: $repositoryName
      }
      runConfigData: $config
    }
  ) {
    __typename
    ... on LaunchRunSuccess { run { runId } }
    ... on PythonError { message }
  }
}
"""

RUN_STATUS_QUERY = """
query GetRunStatus($runId: ID!) {
  pipelineRunOrError(runId: $runId) {
    ... on Run { status }
  }
}
"""

async def _trigger_dagster_job(red_path: str, nir_path: str, utility_path: str, canopy_path: str, project_id: str, run_id: str) -> dict:
    run_config = {
        "ops": {
            "ingest_red_band": {"config": {"file_path": red_path}},
            "ingest_nir_band": {"config": {"file_path": nir_path}},
            "ingest_utility_lines": {"config": {"file_path": utility_path}},
            "ingest_canopy_height": {"config": {"file_path": canopy_path}},
            "mask_and_calculate_risk": {"config": {"project_id": project_id, "run_id": run_id}},
        }
    }
    variables = {
        "config": run_config,
        "jobName": "fire_risk_pipeline",
        "repositoryLocationName": "pipeline.py",
        "repositoryName": "__repository__",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            DAGSTER_URL, json={"query": LAUNCH_RUN_MUTATION, "variables": variables},
        )
        response.raise_for_status()
        return response.json()


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}

@app.post("/projects", tags=["projects"])
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = Project(name=project.name)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/projects", tags=["projects"])
async def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects

@app.delete("/projects/{project_id}", tags=["projects"])
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"status": "success"}

@app.put("/projects/{project_id}", tags=["projects"])
async def update_project(project_id: str, proj_update: ProjectCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = proj_update.name
    db.commit()
    db.refresh(project)
    return project

@app.get("/projects/{project_id}/runs", tags=["runs"])
async def get_project_runs(project_id: str, db: Session = Depends(get_db)):
    runs = db.query(AnalysisRun).filter(AnalysisRun.project_id == project_id).order_by(AnalysisRun.created_at.desc()).all()
    return runs

@app.get("/status/{run_id}", tags=["pipeline"])
async def get_status(run_id: str, db_run_id: Optional[str] = None, db: Session = Depends(get_db)):
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(DAGSTER_URL, json={"query": RUN_STATUS_QUERY, "variables": {"runId": run_id}})
            data = response.json()
            status = data.get("data", {}).get("pipelineRunOrError", {}).get("status", "UNKNOWN")
            
            if db_run_id and status in ["SUCCESS", "FAILURE", "CANCELED"]:
                run = db.query(AnalysisRun).filter(AnalysisRun.id == db_run_id).first()
                if run and run.status != status:
                    run.status = status
                    db.commit()

            return {"run_id": run_id, "status": status}
        except Exception as e:
            return {"run_id": run_id, "status": "ERROR", "detail": str(e)}

@app.get("/runs/{run_id}/results", tags=["pipeline"])
async def get_run_results(run_id: str, db: Session = Depends(get_db)):
    query = """
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(json_agg(
            json_build_object(
                'type',       'Feature',
                'geometry',   ST_AsGeoJSON(geometry)::json,
                'properties', json_build_object('risk_level', risk_level)
            )
        ), '[]'::json)
    )
    FROM geospatial_assets
    WHERE run_id = :rid AND asset_type = 'RISK_POLYGON';
    """
    result = db.execute(text(query), {"rid": run_id}).scalar()
    return JSONResponse(content=result)

@app.get("/runs/{run_id}/utility-lines", tags=["pipeline"])
async def get_run_utility_lines(run_id: str, db: Session = Depends(get_db)):
    query = """
    SELECT json_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(json_agg(
            json_build_object(
                'type',       'Feature',
                'geometry',   ST_AsGeoJSON(geometry)::json,
                'properties', json_build_object('Name', 'Utility Line')
            )
        ), '[]'::json)
    )
    FROM geospatial_assets
    WHERE run_id = :rid AND asset_type = 'UTILITY_LINE';
    """
    result = db.execute(text(query), {"rid": run_id}).scalar()
    return JSONResponse(content=result)


@app.post("/upload", tags=["pipeline"])
async def upload_files(
    project_id: str = Form(...),
    red_band: UploadFile = File(...),
    nir_band: UploadFile = File(...),
    utility_lines: UploadFile = File(...),
    canopy_height: Optional[UploadFile] = None,
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Initialize a new isolated AnalysisRun layer
    current_run = AnalysisRun(project_id=project.id, name=f"Execution: {red_band.filename[:15]}")
    db.add(current_run)
    db.commit()
    db.refresh(current_run)

    proj_dir = DATA_DIR / project_id / str(current_run.id)
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    red_dest = proj_dir / red_band.filename
    nir_dest = proj_dir / nir_band.filename
    util_dest = proj_dir / utility_lines.filename

    await _save_upload(red_band, red_dest)
    await _save_upload(nir_band, nir_dest)
    await _save_upload(utility_lines, util_dest)

    canopy_dest_str = ""
    if canopy_height:
        canopy_dest = proj_dir / canopy_height.filename
        await _save_upload(canopy_height, canopy_dest)
        canopy_dest_str = str(canopy_dest)

    project.status = "RUNNING"
    current_run.status = "RUNNING"
    db.commit()

    dagster_result: dict = {}
    try:
        dagster_result = await _trigger_dagster_job(
            red_path=str(red_dest),
            nir_path=str(nir_dest),
            utility_path=str(util_dest),
            canopy_path=canopy_dest_str,
            project_id=project_id,
            run_id=str(current_run.id)
        )
    except Exception as exc:
        dagster_result = {"error": str(exc)}
        current_run.status = "FAILED"
        db.commit()

    return {"message": "Files received", "dagster": dagster_result, "project_id": project_id, "run_id": str(current_run.id)}
