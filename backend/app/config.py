"""
Settings, read from environment variables or the .env file.

Nothing secret is ever written in code: passwords and keys live in .env
(which git ignores) or in the hosting provider's settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://waypoint:waypoint@localhost:5432/waypoint"
    test_database_url: str = "postgresql://waypoint:waypoint@localhost:5432/waypoint_test"
    # Comma-separated list of website origins allowed to call the API.
    cors_origins: str = "http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """The settings, loaded once."""
    return Settings()
