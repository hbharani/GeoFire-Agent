from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class AnalysisRunBase(BaseModel):
    name: Optional[str] = None

class AnalysisRunCreate(AnalysisRunBase):
    project_id: UUID

class AnalysisRun(AnalysisRunBase):
    id: UUID
    project_id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
