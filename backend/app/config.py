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
    cors_origins: str = "http://localhost:8080,https://ali-fathi-st.github.io"
    # Host names this API answers to. Blocks "DNS rebinding" tricks against a local server.
    allowed_hosts: str = "localhost,127.0.0.1"
    # Where uploaded résumés and cover letters are kept. Private: never served.
    storage_dir: str = "storage"
    # Adzuna job search (optional). Free keys: https://developer.adzuna.com
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "ca"
    # How long to wait for a job source before giving up, in seconds.
    http_timeout: float = 20.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    """The settings, loaded once."""
    return Settings()
