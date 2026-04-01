from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from db.models import AnalysisRun, GeospatialAsset
from schemas.run import AnalysisRunCreate

class RunService:
    @staticmethod
    async def get_project_runs(db: AsyncSession, project_id: str):
        result = await db.execute(
            select(AnalysisRun)
            .filter(AnalysisRun.project_id == project_id)
            .order_by(AnalysisRun.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_run_by_id(db: AsyncSession, run_id: str):
        result = await db.execute(select(AnalysisRun).filter(AnalysisRun.id == run_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_run(db: AsyncSession, run_data: AnalysisRunCreate):
        db_run = AnalysisRun(project_id=run_data.project_id, name=run_data.name)
        db.add(db_run)
        await db.commit()
        await db.refresh(db_run)
        return db_run

    @staticmethod
    async def update_run_status(db: AsyncSession, run_id: str, status: str):
        db_run = await RunService.get_run_by_id(db, run_id)
        if db_run:
            db_run.status = status
            await db.commit()
        return db_run

    @staticmethod
    async def get_run_results_geojson(db: AsyncSession, run_id: str, asset_type: str):
        query = """
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type',       'Feature',
                    'geometry',   ST_AsGeoJSON(geometry)::json,
                    'properties', json_build_object('risk_level', risk_level, 'Name', 'Utility Line')
                )
            ), '[]'::json)
        )
        FROM geospatial_assets
        WHERE run_id = :rid AND asset_type = :atype;
        """
        # Note: Added 'Name' to properties to handle both types with one query if needed, 
        # but the original code had slightly different properties per type.
        # I'll keep it flexible.
        
        if asset_type == 'RISK_POLYGON':
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
        elif asset_type == 'UTILITY_LINE':
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

        result = await db.execute(text(query), {"rid": run_id})
        return result.scalar()
