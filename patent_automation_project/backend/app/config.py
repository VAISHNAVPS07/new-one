from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Patent Automation Platform"
    storage_dir: str = "storage/jobs"
    max_upload_mb: int = 50
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 90
    mcp_server_command: str = ""
    mcp_server_args: str = "[]"
    mcp_search_tool: str = ""
    mcp_search_arguments_template: str = "{}"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def jobs_dir(self) -> Path:
        p = Path(self.storage_dir)
        if not p.is_absolute():
            p = (Path(__file__).resolve().parents[2] / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()
