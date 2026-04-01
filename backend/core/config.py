from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "GeoFire-Agent API"
    VERSION: str = "0.3.0"
    
    # Storage Settings
    DATA_DIR: Path = Path("/data")
    
    # Database Settings
    DATABASE_URL: str = "postgresql+asyncpg://geofire:geofire_secret@db:5432/geofire"
    
    # Dagster Settings
    DAGSTER_HOST: str = "dagster"
    DAGSTER_PORT: str = "3000"
    
    @property
    def DAGSTER_URL(self) -> str:
        return f"http://{self.DAGSTER_HOST}:{self.DAGSTER_PORT}/graphql"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
