import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from .session import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="IDLE")

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=True)
    status = Column(String(50), default="IDLE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GeospatialAsset(Base):
    __tablename__ = "geospatial_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String(50), nullable=False) # 'UTILITY_LINE' or 'RISK_POLYGON'
    risk_level = Column(String(50), nullable=True)  # Low, Medium, High
    # Spatial Vector Column natively tracking WGS84 for dynamic intersection caching
    geometry = Column(Geometry(geometry_type="GEOMETRY", srid=4326))
