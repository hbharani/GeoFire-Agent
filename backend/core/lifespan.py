from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from db.session import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Centralized lifespan for the FastAPI application.
    Initializes database tables on startup.
    """
    async with engine.begin() as conn:
        # Idempotent migration to ensure weather_data column exists on existing tables
        await conn.execute(text("ALTER TABLE analysis_runs ADD COLUMN IF NOT EXISTS weather_data JSONB;"))
        await conn.run_sync(Base.metadata.create_all)
    yield
