from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import make_url
from core.config import settings

# Parse the standard Database URL and convert it to asyncpg format if necessary
try:
    url = make_url(settings.DATABASE_URL)
    if url.drivername.startswith("postgresql") and url.drivername != "postgresql+asyncpg":
        url = url.set(drivername="postgresql+asyncpg")
    # Note: Passing the URL object directly to create_async_engine to preserve 
    # the password, as str(url) in SQLAlchemy 2.0 masks it (e.g., ***).
    ASYNC_DATABASE_URL = url
except Exception as exc:
    # Fail fast with a clear error if the DATABASE_URL cannot be parsed or normalized
    raise ValueError(f"Invalid DATABASE_URL configuration: {settings.DATABASE_URL!r}") from exc

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
