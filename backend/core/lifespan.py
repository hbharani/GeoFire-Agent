from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.session import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Centralized lifespan for the FastAPI application.
    Initializes database tables on startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
