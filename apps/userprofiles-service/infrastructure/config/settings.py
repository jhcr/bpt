from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    env: str = "development"
    debug: bool = True

    # Database
    pg_dsn: str = "postgresql://postgres:password@localhost:5432/appdb"

    # Service info
    service_name: str = "userprofiles-service"
    service_version: str = "1.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
