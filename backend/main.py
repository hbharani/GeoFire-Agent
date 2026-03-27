"""
FastAPI backend for the GeoFire-Agent MVP.

Endpoints:
  POST /upload  — accept a GeoTIFF satellite image and a Shapefile/GeoJSON utility
                  line file, persist them to the /data directory, then trigger a
                  Dagster job via the Dagster GraphQL API using those file paths as
                  run config.
  GET  /health  — simple liveness check.
"""

import os
import json
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("geofire.backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="GeoFire-Agent API", version="0.1.0")

# Allow the React dev-server and the production build to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------- #
# Configuration (overridable via environment variables)                        #
# --------------------------------------------------------------------------- #
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DAGSTER_HOST = os.getenv("DAGSTER_HOST", "dagster")
DAGSTER_PORT = os.getenv("DAGSTER_PORT", "3000")
DAGSTER_URL = f"http://{DAGSTER_HOST}:{DAGSTER_PORT}/graphql"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

async def _save_upload(upload: UploadFile, destination: Path) -> None:
    """Stream an uploaded file to *destination*."""
    contents = await upload.read()
    destination.write_bytes(contents)
    logger.info("Saved upload to %s (%d bytes)", destination, len(contents))


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
    ... on LaunchRunSuccess {
      run {
        runId
      }
    }
    ... on PythonError {
      message
    }
    ... on InvalidSubsetError {
      message
    }
    ... on RunConfigValidationInvalid {
      errors {
        message
      }
    }
  }
}
"""


async def _trigger_dagster_job(satellite_path: str, utility_lines_path: str) -> dict:
    """
    Launch the ``fire_risk_pipeline`` Dagster job via the GraphQL API,
    passing the file paths as run config so the ops know where to read data from.
    """
    run_config = {
        "ops": {
            "ingest_satellite_image": {
                "config": {"file_path": satellite_path}
            },
            "ingest_utility_lines": {
                "config": {"file_path": utility_lines_path}
            },
        }
    }

    variables = {
        "config": run_config,
        "jobName": "fire_risk_pipeline",
        "repositoryLocationName": "dagster_pipeline.pipeline",
        "repositoryName": "__repository__",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            DAGSTER_URL,
            json={"query": LAUNCH_RUN_MUTATION, "variables": variables},
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #

@app.get("/health", tags=["ops"])
async def health():
    """Liveness check."""
    return {"status": "ok"}


@app.post("/upload", tags=["pipeline"])
async def upload_files(
    satellite_image: UploadFile = File(..., description="GeoTIFF satellite image"),
    utility_lines: UploadFile = File(..., description="Shapefile (.zip) or GeoJSON utility lines"),
):
    """
    Accept a GeoTIFF and a utility-line file, persist them to the shared data
    volume, then trigger the Dagster fire-risk pipeline.
    """
    # Validate basic content type hints (not strict — Docker env won't always
    # set MIME types correctly for GeoTIFF / Shapefile).
    allowed_extensions = {
        "satellite_image": {".tif", ".tiff", ".geotiff"},
        "utility_lines": {".geojson", ".json", ".zip", ".shp"},
    }

    sat_ext = Path(satellite_image.filename or "").suffix.lower()
    util_ext = Path(utility_lines.filename or "").suffix.lower()

    if sat_ext not in allowed_extensions["satellite_image"]:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported satellite image format '{sat_ext}'. "
                   f"Allowed: {allowed_extensions['satellite_image']}",
        )
    if util_ext not in allowed_extensions["utility_lines"]:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported utility lines format '{util_ext}'. "
                   f"Allowed: {allowed_extensions['utility_lines']}",
        )

    satellite_dest = DATA_DIR / satellite_image.filename
    utility_dest = DATA_DIR / utility_lines.filename

    await _save_upload(satellite_image, satellite_dest)
    await _save_upload(utility_lines, utility_dest)

    # Trigger the Dagster job — failures are logged but do not block the
    # response so the caller knows the files were received.
    dagster_result: dict = {}
    try:
        dagster_result = await _trigger_dagster_job(
            satellite_path=str(satellite_dest),
            utility_lines_path=str(utility_dest),
        )
        logger.info("Dagster response: %s", json.dumps(dagster_result))
    except (httpx.HTTPError, httpx.TimeoutException) as exc:  # noqa: BLE001
        logger.warning("Could not reach Dagster: %s", exc)
        dagster_result = {"error": str(exc)}

    return {
        "message": "Files received and pipeline triggered.",
        "satellite_image": str(satellite_dest),
        "utility_lines": str(utility_dest),
        "dagster": dagster_result,
    }
