"""
Dagster pipeline for the GeoFire-Agent with PostGIS Backend.
"""

import os
import uuid
import logging
import httpx
import math
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
# Helpers
# --------------------------------------------------------------------------- #

def get_live_fire_weather(lats: list, lons: list):
    """
    Open-Meteo endpoint for batch fetching multiple locations (current temp, humidity, wind speed).
    """
    lat_str = ",".join([f"{l:.4f}" for l in lats])
    lon_str = ",".join([f"{l:.4f}" for l in lons])
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat_str}&longitude={lon_str}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
    try:
        response = httpx.get(url, timeout=15.0).json()
        
        # Handle single vs multiple location response format
        if not isinstance(response, list):
            observations = [response]
        else:
            observations = response
            
        results = []
        for obs in observations:
            current = obs.get('current', {})
            wind_kmh = current.get('wind_speed_10m', 0)
            wind_deg = current.get('wind_direction_10m', 0)
            humidity_pct = current.get('relative_humidity_2m', 100)
            temp_c = current.get('temperature_2m', 0)
            lat_out = obs.get('latitude')
            lon_out = obs.get('longitude')
            
            # Red Flag Warning: Wind > 30km/h and Humidity < 30%
            red_flag_warning = wind_kmh > 30 and humidity_pct < 30
            
            results.append({
                "latitude": lat_out,
                "longitude": lon_out,
                "wind_speed": wind_kmh,
                "wind_direction": wind_deg,
                "humidity": humidity_pct,
                "temperature": temp_c,
                "red_flag": red_flag_warning
            })
        return results
    except Exception as e:
        logger.error(f"Failed to fetch batch weather data: {e}")
        return None

# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #

@op(config_schema={"file_path": Field(String)})
def ingest_red_band(context: OpExecutionContext) -> str: return context.op_config["file_path"]

@op(config_schema={"file_path": Field(String)})
def ingest_nir_band(context: OpExecutionContext) -> str: return context.op_config["file_path"]

@op(config_schema={"file_path": Field(String, default_value="", is_required=False)})
def ingest_canopy_height(context: OpExecutionContext) -> str: return context.op_config.get("file_path", "")

@op(config_schema={"file_path": Field(String, default_value="", is_required=False)})
def ingest_swir_band(context: OpExecutionContext) -> str: return context.op_config.get("file_path", "")

@op(config_schema={"file_path": Field(String)})
def ingest_utility_lines(context: OpExecutionContext) -> str: return context.op_config["file_path"]

@op(
    config_schema={
        "project_id": Field(String, is_required=True, description="UUID of the active project"),
        "run_id": Field(String, is_required=True, description="UUID of the specific run attempt"),
        "ndmi_high_stress_threshold": Field(float, default_value=0.0, description="NDMI values below this increase fire risk"),
        "ndmi_low_stress_threshold": Field(float, default_value=0.2, description="NDMI values above this decrease fire risk")
    },
    ins={
        "utility_lines_path": In(), "red_path": In(), "nir_path": In(), "canopy_path": In(), "swir_path": In(),
    },
    out=Out()
)
def mask_and_calculate_risk(
    context: OpExecutionContext,
    utility_lines_path: str,
    red_path: str,
    nir_path: str,
    canopy_path: str,
    swir_path: str,
) -> str:
    project_id = context.op_config["project_id"]
    run_id = context.op_config["run_id"]
    ndmi_high_stress_threshold = context.op_config["ndmi_high_stress_threshold"]
    ndmi_low_stress_threshold = context.op_config["ndmi_low_stress_threshold"]
    context.log.info(f"Triggered pipeline for Project ID: {project_id} | Run ID: {run_id}")

    # Validation: Ensure thresholds don't overlap
    if ndmi_high_stress_threshold >= ndmi_low_stress_threshold:
        context.log.warning(
            f"Overlapping NDMI thresholds: high_stress({ndmi_high_stress_threshold}) >= low_stress({ndmi_low_stress_threshold}). "
            "Skipping NDMI risk adjustment."
        )
        use_swir_internal = False
    else:
        use_swir_internal = True

    # 1. Align Coordinate Systems & Calculate Dynamic Weather Grid
    with rasterio.open(red_path) as src_red:
        raster_crs = src_red.crs
        raster_bounds = src_red.bounds
        
        # Calculate dynamic grid dimensions (Target: ~20km resolution)
        width_m = raster_bounds.right - raster_bounds.left
        height_m = raster_bounds.top - raster_bounds.bottom
        resolution_m = 20000.0 # 20km
        
        num_cols = max(1, math.ceil(width_m / resolution_m))
        num_rows = max(1, math.ceil(height_m / resolution_m))
        
        context.log.info(f"Generating dynamic weather grid: {num_cols}x{num_rows} sampling points ({width_m/1000:.1f}km x {height_m/1000:.1f}km area)")
        
        # Generate grid centroids
        lats, lons = [], []
        from pyproj import Transformer
        transformer = Transformer.from_crs(raster_crs, "EPSG:4326", always_xy=True)
        
        col_step = width_m / num_cols
        row_step = height_m / num_rows
        
        for r in range(num_rows):
            for c in range(num_cols):
                # Calculate center of each cell in meters
                mx = raster_bounds.left + (c + 0.5) * col_step
                my = raster_bounds.bottom + (r + 0.5) * row_step
                lon, lat = transformer.transform(mx, my)
                lats.append(lat)
                lons.append(lon)
        
    context.log.info(f"Fetching batch weather for {len(lats)} dynamic stations...")
    weather_results = get_live_fire_weather(lats, lons)
    
    if weather_results:
        num_red_flags = sum(1 for w in weather_results if w['red_flag'])
        context.log.info(f"Atmospheric Data Received: {len(weather_results)} points. RED FLAGS: {num_red_flags}")
    else:
        context.log.warning("Spatial weather fetch returned no results. Proceeding with baseline risk factors only...")

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
            properties = row['properties'] if 'properties' in row else None
            records.append({
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "run_id": run_id,
                "asset_type": asset_type,
                "risk_level": risk_val,
                "properties": properties,
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

    use_swir = bool(swir_path and Path(swir_path).exists())
    swir_data = None
    if use_swir:
        from rasterio.vrt import WarpedVRT
        with rasterio.open(swir_path) as src_swir:
            with WarpedVRT(src_swir, crs=raster_crs, transform=red_transform, height=red_height, width=red_width) as vrt_swir:
                swir_masked, _ = mask(vrt_swir, shapes, crop=True)
                swir_data = swir_masked[0].astype(float)

    use_swir = use_swir and use_swir_internal

    # Calculate NDVI
    denominator = (nir_data + red_data)
    ndvi = np.zeros_like(red_data)
    valid_mask = denominator != 0
    ndvi[valid_mask] = (nir_data[valid_mask] - red_data[valid_mask]) / denominator[valid_mask]

    risk_array = np.zeros_like(ndvi, dtype='uint8')
    risk_array[(ndvi > 0.3) & (ndvi <= 0.5)] = 1
    risk_array[(ndvi > 0.5) & (ndvi <= 0.7)] = 2
    risk_array[ndvi > 0.7] = 3

    if use_swir and swir_data is not None:
        ndmi_denominator = (nir_data + swir_data)
        ndmi = np.zeros_like(nir_data)
        ndmi_valid = ndmi_denominator != 0
        ndmi[ndmi_valid] = (nir_data[ndmi_valid] - swir_data[ndmi_valid]) / ndmi_denominator[ndmi_valid]
        
        high_stress = ndmi_valid & (ndmi < ndmi_high_stress_threshold) & (risk_array > 0)
        risk_array[high_stress] = np.minimum(risk_array[high_stress] + 1, 3)
        
        # Mutually exclusive: only apply low stress if NOT already adjusted by high stress
        low_stress = ndmi_valid & (ndmi > ndmi_low_stress_threshold) & (risk_array > 0) & ~high_stress
        risk_array[low_stress] = np.maximum(risk_array[low_stress] - 1, 1)

    if use_canopy and canopy_data is not None:
        risk_array[canopy_data < 3.0] = 0

    # Apply Localized Dynamic Weather Escalation
    if weather_results:
        context.log.info("Applying Localized Proximity-Aware Risk Escalation...")
        
        # Create a low-res red flag map based on the grid
        # Note: Open-Meteo returns results in the same order as requested (row by row)
        red_flag_grid = np.array([w['red_flag'] for w in weather_results]).reshape(num_rows, num_cols)
        
        if np.any(red_flag_grid):
            # Efficiently upscale the low-res flag grid to the full raster dimension using nearest-neighbor mapping
            # This identifies which high-res pixel belongs to which 20km station quadrant
            # We reverse the row order because PostGIS / Raster arrays are top-to-bottom (Y=0 at TOP)
            # but our meter calculation started from raster_bounds.bottom (Y=0 at BOTTOM for Cartesian Y)
            red_flag_grid_flipped = np.flipud(red_flag_grid)
            
            # Map raster indices to grid cell indices
            h, w = risk_array.shape
            y_map = (np.arange(h) * num_rows / h).astype(int)
            x_map = (np.arange(w) * num_cols / w).astype(int)
            
            spatial_flag_mask = red_flag_grid_flipped[y_map[:, None], x_map]
            
            # Apply escalation (+1) localized to red-flag cells (cap at 3)
            risk_array[(risk_array > 0) & (risk_array < 3) & spatial_flag_mask] += 1
            context.log.info("Spatial escalation applied successfully to affected quadrants.")

    context.log.info("Vectorizing risk areas into definitive polygons & calculating Risk DNA...")
    polygons, risk_levels, dna_props = [], [], []
    
    # Pre-calculate spatial flag mask indices for fast weather lookup
    h, w = risk_array.shape
    y_map = (np.arange(h) * num_rows / h).astype(int)
    x_map = (np.arange(w) * num_cols / w).astype(int)
    
    for geom, val in rasterio.features.shapes(risk_array, transform=out_transform):
        if val > 0:
            poly = shape(geom)
            polygons.append(poly)
            risk_levels.append(int(val))
            
            # Risk DNA: Sample the underlying raster data for this polygon using its centroid
            # Optimization: Instead of expensive geometry masking, we use the centroid for high-speed sampling
            centroid = poly.centroid
            cx, cy = int((centroid.x - raster_bounds.left) * w / width_m), int((raster_bounds.top - centroid.y) * h / height_m)
            # Clip indices to avoid out-of-bounds
            cx, cy = max(0, min(w-1, cx)), max(0, min(h-1, cy))
            
            p_ndvi = float(ndvi[cy, cx])
            p_ndmi = float(ndmi[cy, cx]) if use_swir else 0.0
            p_canopy = float(canopy_data[cy, cx]) if use_canopy else 0.0
            
            # Map nearest weather station using same indices
            grid_y, grid_x = y_map[cy], x_map[cx]
            weather_idx = grid_y * num_cols + grid_x
            p_weather = weather_results[weather_idx] if weather_results and weather_idx < len(weather_results) else {}
            
            dna_props.append({
                "ndvi": round(p_ndvi, 3),
                "ndmi": round(p_ndmi, 3),
                "canopy_height": round(p_canopy, 2),
                "wind_speed": p_weather.get("wind_speed"),
                "wind_direction": p_weather.get("wind_direction"),
                "humidity": p_weather.get("humidity"),
                "temp": p_weather.get("temperature"),
                "red_flag_alert": p_weather.get("red_flag", False)
            })
            
    veg_gdf = gpd.GeoDataFrame({
        'geometry': polygons, 
        'risk_score': risk_levels,
        'properties': dna_props
    }, crs=raster_crs)
    
    if not veg_gdf.empty:
        risk_map = {1: 'Low', 2: 'Medium', 3: 'High'}
        veg_gdf['risk_level'] = veg_gdf['risk_score'].map(risk_map)
        context.log.info("Transforming CRS to standard lat/lon...")
        veg_gdf_out = veg_gdf.to_crs(4326)
        
        context.log.info("Inserting Risk Polygons natively into PostGIS with full DNA properties!")
        push_geometries_to_db(veg_gdf_out, 'RISK_POLYGON', risk_col='risk_level')
        context.log.info(f"Process complete! Registered {len(veg_gdf_out)} threat polygons with traceable metadata.")
    
    # Store dynamic weather grid back to the analysis_run table
    if weather_results:
        try:
            from sqlalchemy import text
            with engine.begin() as conn:
                import json
                conn.execute(
                    text("UPDATE analysis_runs SET weather_data = :wdata WHERE id = CAST(:rid AS UUID)"),
                    {"wdata": json.dumps(weather_results), "rid": run_id}
                )
            context.log.info(f"Persisted atmospheric metadata for {len(weather_results)} stations to Database.")
        except Exception as e:
            context.log.error(f"Failed to persist weather data for run {run_id}: {e}")

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
    swir = ingest_swir_band()
    mask_and_calculate_risk(
        utility_lines_path=utility,
        red_path=red,
        nir_path=nir,
        canopy_path=canopy,
        swir_path=swir
    )

defs = Definitions(jobs=[fire_risk_pipeline])
