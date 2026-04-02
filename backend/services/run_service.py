from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from db.models import AnalysisRun
from schemas.run import AnalysisRunCreate
from uuid import UUID

class RunService:
    @staticmethod
    async def get_project_runs(db: AsyncSession, project_id: UUID):
        result = await db.execute(
            select(AnalysisRun)
            .filter(AnalysisRun.project_id == project_id)
            .order_by(AnalysisRun.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_run_by_id(db: AsyncSession, run_id: UUID):
        result = await db.execute(select(AnalysisRun).filter(AnalysisRun.id == run_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_run(db: AsyncSession, run_data: AnalysisRunCreate, commit: bool = True):
        db_run = AnalysisRun(project_id=run_data.project_id, name=run_data.name)
        db.add(db_run)
        if commit:
            await db.commit()
            await db.refresh(db_run)
        else:
            # Ensure the run has an ID without forcing a commit
            await db.flush()
        return db_run

    @staticmethod
    async def update_run_status(db: AsyncSession, run_id: UUID, status: str, commit: bool = True):
        db_run = await RunService.get_run_by_id(db, run_id)
        if db_run:
            db_run.status = status
            if commit:
                await db.commit()
        return db_run

    @staticmethod
    async def get_run_results_geojson(db: AsyncSession, run_id: UUID, asset_type: str):
        if asset_type == 'RISK_POLYGON':
            query = """
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type',       'Feature',
                        'geometry',   ST_AsGeoJSON(ga.geometry)::json,
                        'properties', json_build_object('risk_level', ga.risk_level)::jsonb || COALESCE(ga.properties, '{}'::jsonb)
                    )
                ), '[]'::json),
                'properties', (SELECT weather_data FROM analysis_runs WHERE id = CAST(:rid AS UUID))
            )
            FROM geospatial_assets ga
            WHERE ga.run_id = CAST(:rid AS UUID) AND ga.asset_type = 'RISK_POLYGON';
            """
        elif asset_type == 'UTILITY_LINE':
            query = """
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type',       'Feature',
                        'geometry',   ST_AsGeoJSON(ga.geometry)::json,
                        'properties', json_build_object('Name', 'Utility Line')
                    )
                ), '[]'::json),
                'properties', (SELECT weather_data FROM analysis_runs WHERE id = CAST(:rid AS UUID))
            )
            FROM geospatial_assets ga
            WHERE ga.run_id = CAST(:rid AS UUID) AND ga.asset_type = 'UTILITY_LINE';
            """
        else:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        result = await db.execute(text(query), {"rid": run_id})
        return result.scalar()
