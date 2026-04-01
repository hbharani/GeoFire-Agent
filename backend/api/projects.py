from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_db
from services.project_service import ProjectService
from schemas.project import ProjectCreate, Project
from typing import List
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=Project)
async def create_project(project_data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    return await ProjectService.create_project(db, project_data)

@router.get("", response_model=List[Project])
async def get_projects(db: AsyncSession = Depends(get_db)):
    return await ProjectService.get_all_projects(db)

@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await ProjectService.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: UUID, project_data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = await ProjectService.update_project(db, project_id, project_data)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    success = await ProjectService.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success"}
