from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Project
from schemas.project import ProjectCreate
from uuid import UUID

class ProjectService:
    @staticmethod
    async def get_all_projects(db: AsyncSession):
        result = await db.execute(select(Project).order_by(Project.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def get_project_by_id(db: AsyncSession, project_id: UUID):
        result = await db.execute(select(Project).filter(Project.id == project_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_project(db: AsyncSession, project_data: ProjectCreate, commit: bool = True):
        db_project = Project(name=project_data.name, description=project_data.description)
        db.add(db_project)
        if commit:
            await db.commit()
            await db.refresh(db_project)
        return db_project

    @staticmethod
    async def update_project(db: AsyncSession, project_id: UUID, project_data: ProjectCreate, commit: bool = True):
        db_project = await ProjectService.get_project_by_id(db, project_id)
        if not db_project:
            return None
        db_project.name = project_data.name
        db_project.description = project_data.description
        if commit:
            await db.commit()
            await db.refresh(db_project)
        return db_project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: UUID, commit: bool = True):
        db_project = await ProjectService.get_project_by_id(db, project_id)
        if not db_project:
            return False
        db.delete(db_project)
        if commit:
            await db.commit()
        return True
