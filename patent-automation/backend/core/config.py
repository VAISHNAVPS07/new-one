from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based configuration. All variables are prefixed PATENT_."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="PATENT_", extra="ignore")

    storage_dir: Path = Path("storage/jobs")
    template_config: Path = Path("config/disclosure_template.yaml")
    max_upload_mb: int = 100
    max_concurrent_jobs: int = 2
    api_key: str | None = None
    ocr_enabled: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
