"""
Dagster pipeline for the GeoFire-Agent MVP.

Job: fire_risk_pipeline
Ops (stubbed — real processing logic to be wired in later):
  1. ingest_satellite_image      — load / validate GeoTIFF
  2. ingest_utility_lines        — load / validate Shapefile or GeoJSON
  3. calculate_vegetation_index  — compute NDVI from bands (mocked)
  4. mask_and_calculate_risk     — buffer lines, intersect with vegetation (mocked)
"""

import os
import logging
from pathlib import Path

from dagster import (
    Definitions,
    job,
    op,
    In,
    Out,
    Field,
    String,
    OpExecutionContext,
)

logger = logging.getLogger("geofire.pipeline")

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))


# --------------------------------------------------------------------------- #
# Op 1 — Ingest satellite image                                               #
# --------------------------------------------------------------------------- #

@op(
    config_schema={"file_path": Field(String, description="Absolute path to the GeoTIFF file.")},
    out=Out(description="Path to the validated GeoTIFF file."),
)
def ingest_satellite_image(context: OpExecutionContext) -> str:
    file_path = context.op_config["file_path"]
    context.log.info("Ingesting satellite image from: %s", file_path)

    if not Path(file_path).exists():
        raise FileNotFoundError(f"Satellite image not found: {file_path}")

    # TODO: Use rasterio to open and validate the GeoTIFF CRS / band count.
    context.log.info("[MOCK] Satellite image validated successfully.")
    return file_path


# --------------------------------------------------------------------------- #
# Op 2 — Ingest utility lines                                                 #
# --------------------------------------------------------------------------- #

@op(
    config_schema={"file_path": Field(String, description="Absolute path to the Shapefile (.zip) or GeoJSON.")},
    out=Out(description="Path to the validated utility-lines file."),
)
def ingest_utility_lines(context: OpExecutionContext) -> str:
    file_path = context.op_config["file_path"]
    context.log.info("Ingesting utility lines from: %s", file_path)

    if not Path(file_path).exists():
        raise FileNotFoundError(f"Utility lines file not found: {file_path}")

    # TODO: Use geopandas to read and validate geometry types.
    context.log.info("[MOCK] Utility lines validated successfully.")
    return file_path


# --------------------------------------------------------------------------- #
# Op 3 — Calculate vegetation index (NDVI)                                    #
# --------------------------------------------------------------------------- #

@op(
    ins={"satellite_path": In(description="Path to the validated GeoTIFF.")},
    out=Out(description="Path to the NDVI output raster."),
)
def calculate_vegetation_index(context: OpExecutionContext, satellite_path: str) -> str:
    context.log.info("Calculating NDVI for: %s", satellite_path)

    # TODO: Real implementation:
    #   with rasterio.open(satellite_path) as src:
    #       red  = src.read(3).astype(float)   # band indices depend on sensor
    #       nir  = src.read(4).astype(float)
    #       ndvi = (nir - red) / (nir + red + 1e-10)
    #   Write ndvi array back to /data/ndvi_output.tif using rasterio.

    ndvi_output_path = str(DATA_DIR / "ndvi_output.tif")
    context.log.info("[MOCK] NDVI raster written to: %s", ndvi_output_path)
    return ndvi_output_path


# --------------------------------------------------------------------------- #
# Op 4 — Mask and calculate fire risk                                         #
# --------------------------------------------------------------------------- #

@op(
    ins={
        "utility_lines_path": In(description="Path to the validated utility-lines file."),
        "ndvi_path": In(description="Path to the NDVI raster."),
    },
    out=Out(description="Path to the fire-risk GeoJSON output."),
)
def mask_and_calculate_risk(
    context: OpExecutionContext,
    utility_lines_path: str,
    ndvi_path: str,
) -> str:
    context.log.info(
        "Calculating fire risk | utility_lines=%s | ndvi=%s",
        utility_lines_path,
        ndvi_path,
    )

    # TODO: Real implementation:
    #   lines_gdf = geopandas.read_file(utility_lines_path)
    #   buffered   = lines_gdf.buffer(distance=30)   # 30-metre corridor
    #   with rasterio.open(ndvi_path) as src:
    #       masked, _ = rasterio.mask.mask(src, buffered.geometry, crop=True)
    #   Classify risk bands and write output GeoJSON.

    risk_output_path = str(DATA_DIR / "fire_risk_output.geojson")
    context.log.info("[MOCK] Fire-risk output written to: %s", risk_output_path)
    return risk_output_path


# --------------------------------------------------------------------------- #
# Job definition                                                               #
# --------------------------------------------------------------------------- #

@job(description="End-to-end fire-risk pipeline: ingest → NDVI → risk mask.")
def fire_risk_pipeline():
    satellite_path = ingest_satellite_image()
    utility_path = ingest_utility_lines()
    ndvi_path = calculate_vegetation_index(satellite_path=satellite_path)
    mask_and_calculate_risk(
        utility_lines_path=utility_path,
        ndvi_path=ndvi_path,
    )


# --------------------------------------------------------------------------- #
# Dagster Definitions (entry point for the webserver / CLI)                   #
# --------------------------------------------------------------------------- #

defs = Definitions(jobs=[fire_risk_pipeline])
