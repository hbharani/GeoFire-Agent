from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from services.run_service import RunService
from schemas.run import AnalysisRun
from typing import List

router = APIRouter(tags=["runs"])

@router.get("/projects/{project_id}/runs", response_model=List[AnalysisRun])
async def get_project_runs(project_id: str, db: AsyncSession = Depends(get_db)):
    return await RunService.get_project_runs(db, project_id)

@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await RunService.get_run_results_geojson(db, run_id, 'RISK_POLYGON')
    return JSONResponse(content=result)

@router.get("/runs/{run_id}/utility-lines")
async def get_run_utility_lines(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await RunService.get_run_results_geojson(db, run_id, 'UTILITY_LINE')
    return JSONResponse(content=result)
