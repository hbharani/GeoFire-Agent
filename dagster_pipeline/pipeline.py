"""
Dagster pipeline for the GeoFire-Agent with PostGIS Backend.
"""

import os
import uuid
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

import geopandas as gpd
import pandas as pd
import rasterio
import rasterio.features
from rasterio.mask import mask
from shapely.geometry import shape
import numpy as np

# PostGIS dependencies
from sqlalchemy import create_engine
import geoalchemy2

logger = logging.getLogger("geofire.pipeline")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://geofire:geofire_secret@db:5432/geofire")

engine = create_engine(DATABASE_URL)

# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #

@op(config_schema={"file_path": Field(String)})
def ingest_red_band(context: OpExecutionContext) -> str: return context.op_config["file_path"]

@op(config_schema={"file_path": Field(String)})
def ingest_nir_band(context: OpExecutionContext) -> str: return context.op_config["file_path"]

@op(config_schema={"file_path": Field(String, default_value="", is_required=False)})
def ingest_canopy_height(context: OpExecutionContext) -> str: return context.op_config.get("file_path", "")

@op(config_schema={"file_path": Field(String)})
def ingest_utility_lines(context: OpExecutionContext) -> str: return context.op_config["file_path"]

@op(
    config_schema={
        "project_id": Field(String, is_required=True, description="UUID of the active project"),
        "run_id": Field(String, is_required=True, description="UUID of the specific run attempt")
    },
    ins={
        "utility_lines_path": In(), "red_path": In(), "nir_path": In(), "canopy_path": In(),
    },
    out=Out()
)
def mask_and_calculate_risk(
    context: OpExecutionContext,
    utility_lines_path: str,
    red_path: str,
    nir_path: str,
    canopy_path: str,
) -> str:
    project_id = context.op_config["project_id"]
    run_id = context.op_config["run_id"]
    context.log.info(f"Triggered pipeline for Project ID: {project_id} | Run ID: {run_id}")

    # 1. Align Coordinate Systems
    with rasterio.open(red_path) as src_red:
        raster_crs = src_red.crs
        raster_bounds = src_red.bounds

    # 2. Push Utility Lines to DB & Buffer instantly
    context.log.info("Loading Utility lines directly into PostGIS...")
    lines_gdf = gpd.read_file(utility_lines_path)
    lines_projected = lines_gdf.to_crs(raster_crs)
    
    from shapely.geometry import box as shp_box
    raster_box = shp_box(*raster_bounds)
    lines_projected = lines_projected[lines_projected.intersects(raster_box)]
    
    if lines_projected.empty:
        context.log.warning("No utility lines overlap the raster! Exiting early.")
        return project_id

    # Raw SQLAlchemy Core Insert logic to completely bypass Pandas Geometry mapping bugs
    from sqlalchemy import MetaData, Table, insert
    metadata = MetaData()
    metadata.reflect(bind=engine)
    asset_table = metadata.tables['geospatial_assets']
    
    def push_geometries_to_db(gdf, asset_type, risk_col=None):
        if gdf.empty: return
        records = []
        for _, row in gdf.iterrows():
            risk_val = row[risk_col] if risk_col and risk_col in row else None
            records.append({
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "run_id": run_id,
                "asset_type": asset_type,
                "risk_level": risk_val,
                "geometry": f"SRID=4326;{row['geometry'].wkt}" # Format as EWKT string dynamically accepted by Postgres
            })
        
        with engine.begin() as conn:
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                conn.execute(insert(asset_table), records[i:i+chunk_size])

    context.log.info("Transforming lines to EPSG:4326 for unified web storage...")
    lines_db = lines_projected.to_crs(4326)
    
    context.log.info("Writing utility vectors robustly to PostGIS...")
    push_geometries_to_db(lines_db, 'UTILITY_LINE')

    context.log.info("Triggering Native Buffer...")
    buffer_distance = 30.0
    buffered_lines = lines_projected.copy()
    buffered_lines['geometry'] = buffered_lines.buffer(buffer_distance)
    
    shapes = [geom for geom in buffered_lines.geometry]

    with rasterio.open(red_path) as src_red:
        red_masked, out_transform = mask(src_red, shapes, crop=True)
        red_height, red_width, red_transform = src_red.height, src_red.width, src_red.transform
    with rasterio.open(nir_path) as src_nir:
        nir_masked, _ = mask(src_nir, shapes, crop=True)
        
    red_data, nir_data = red_masked[0].astype(float), nir_masked[0].astype(float)

    use_canopy = bool(canopy_path and Path(canopy_path).exists())
    canopy_data = None
    if use_canopy:
        from rasterio.vrt import WarpedVRT
        with rasterio.open(canopy_path) as src_canopy:
            with WarpedVRT(src_canopy, crs=raster_crs, transform=red_transform, height=red_height, width=red_width) as vrt:
                canopy_masked, _ = mask(vrt, shapes, crop=True)
                canopy_data = canopy_masked[0].astype(float)

    # Calculate NDVI
    denominator = (nir_data + red_data)
    ndvi = np.zeros_like(red_data)
    valid_mask = denominator != 0
    ndvi[valid_mask] = (nir_data[valid_mask] - red_data[valid_mask]) / denominator[valid_mask]

    risk_array = np.zeros_like(ndvi, dtype='uint8')
    risk_array[(ndvi > 0.3) & (ndvi <= 0.5)] = 1
    risk_array[(ndvi > 0.5) & (ndvi <= 0.7)] = 2
    risk_array[ndvi > 0.7] = 3

    if use_canopy and canopy_data is not None:
        risk_array[canopy_data < 3.0] = 0

    context.log.info("Vectorizing risk areas into definitive polygons...")
    polygons, risk_levels = [], []
    for geom, val in rasterio.features.shapes(risk_array, transform=out_transform):
        if val > 0:
            polygons.append(shape(geom))
            risk_levels.append(int(val))
            
    veg_gdf = gpd.GeoDataFrame({'geometry': polygons, 'risk_score': risk_levels}, crs=raster_crs)
    if not veg_gdf.empty:
        risk_map = {1: 'Low', 2: 'Medium', 3: 'High'}
        veg_gdf['risk_level'] = veg_gdf['risk_score'].map(risk_map)
        context.log.info("Transforming CRS to standard lat/lon...")
        veg_gdf_out = veg_gdf.to_crs(4326)
        
        context.log.info("Inserting Risk Polygons natively into PostGIS!")
        push_geometries_to_db(veg_gdf_out, 'RISK_POLYGON', risk_col='risk_level')
        context.log.info(f"Process complete! Registered {len(veg_gdf_out)} threat polygons into PostGIS.")
    
    return project_id

# --------------------------------------------------------------------------- #
# Job definition
# --------------------------------------------------------------------------- #

@job(description="End-to-end discrete multi-spectral PostGIS pipeline.")
def fire_risk_pipeline():
    red = ingest_red_band()
    nir = ingest_nir_band()
    utility = ingest_utility_lines()
    canopy = ingest_canopy_height()
    mask_and_calculate_risk(
        utility_lines_path=utility,
        red_path=red,
        nir_path=nir,
        canopy_path=canopy
    )

defs = Definitions(jobs=[fire_risk_pipeline])
