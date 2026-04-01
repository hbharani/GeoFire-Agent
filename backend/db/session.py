import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import make_url

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://geofire:geofire_secret@db:5432/geofire")

# Ensure the URL uses the asyncpg driver for any PostgreSQL DSN
try:
    url = make_url(DATABASE_URL)
    if url.drivername.startswith("postgresql") and url.drivername != "postgresql+asyncpg":
        url = url.set(drivername="postgresql+asyncpg")
    ASYNC_DATABASE_URL = str(url)
except Exception:
    # Fallback to the raw DATABASE_URL if parsing fails for any reason
    ASYNC_DATABASE_URL = DATABASE_URL

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
