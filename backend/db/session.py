from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import make_url
from core.config import settings

# Parse the standard Database URL and convert it to asyncpg format if necessary
try:
    url = make_url(settings.DATABASE_URL)
    if url.drivername.startswith("postgresql") and url.drivername != "postgresql+asyncpg":
        url = url.set(drivername="postgresql+asyncpg")
    ASYNC_DATABASE_URL = str(url)
except Exception:
    # Fallback to the raw DATABASE_URL if parsing fails
    ASYNC_DATABASE_URL = settings.DATABASE_URL

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
