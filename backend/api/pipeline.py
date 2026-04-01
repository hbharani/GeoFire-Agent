import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from services.project_service import ProjectService
from services.run_service import RunService
from services.dagster_service import DagsterService
from schemas.run import AnalysisRunCreate

router = APIRouter(tags=["pipeline"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

async def _save_upload(upload: UploadFile, destination: Path) -> None:
    contents = await upload.read()
    destination.write_bytes(contents)

@router.get("/status/{run_id}")
async def get_status(run_id: str, db_run_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    try:
        status = await DagsterService.get_run_status(run_id)
        
        if db_run_id and status in ["SUCCESS", "FAILURE", "CANCELED"]:
            await RunService.update_run_status(db, db_run_id, status)

        return {"run_id": run_id, "status": status}
    except Exception as e:
        return {"run_id": run_id, "status": "ERROR", "detail": str(e)}

@router.post("/upload")
async def upload_files(
    project_id: str = Form(...),
    red_band: UploadFile = File(...),
    nir_band: UploadFile = File(...),
    utility_lines: UploadFile = File(...),
    canopy_height: Optional[UploadFile] = None,
    db: AsyncSession = Depends(get_db)
):
    # Security: Validate project_id as UUID
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format. Must be a UUID.")

    project = await ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Security: Sanitize filenames to prevent path traversal
    red_filename = Path(red_band.filename).name
    nir_filename = Path(nir_band.filename).name
    util_filename = Path(utility_lines.filename).name

    # Initialize a new isolated AnalysisRun layer
    # Note: Using commit=False to ensure transactional integrity
    current_run = await RunService.create_run(
        db, 
        AnalysisRunCreate(project_id=project.id, name=f"Execution: {red_filename[:15]}"),
        commit=False
    )

    proj_dir = DATA_DIR / project_id / str(current_run.id)
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    red_dest = proj_dir / red_filename
    nir_dest = proj_dir / nir_filename
    util_dest = proj_dir / util_filename

    await _save_upload(red_band, red_dest)
    await _save_upload(nir_band, nir_dest)
    await _save_upload(utility_lines, util_dest)

    canopy_dest_str = ""
    if canopy_height:
        canopy_filename = Path(canopy_height.filename).name
        canopy_dest = proj_dir / canopy_filename
        await _save_upload(canopy_height, canopy_dest)
        canopy_dest_str = str(canopy_dest)

    # Update statuses in a single commit block
    project.status = "RUNNING"
    await RunService.update_run_status(db, str(current_run.id), "RUNNING", commit=False)
    await db.commit()

    dagster_result: dict = {}
    try:
        dagster_result = await DagsterService.trigger_job(
            red_path=str(red_dest),
            nir_path=str(nir_dest),
            utility_path=str(util_dest),
            canopy_path=canopy_dest_str,
            project_id=project_id,
            run_id=str(current_run.id)
        )
    except Exception as exc:
        dagster_result = {"error": str(exc)}
        # Security/Consistency: Revert statuses on failure
        project.status = "FAILED"
        await RunService.update_run_status(db, str(current_run.id), "FAILED", commit=False)
        await db.commit()

    return {"message": "Files received", "dagster": dagster_result, "project_id": project_id, "run_id": str(current_run.id)}
