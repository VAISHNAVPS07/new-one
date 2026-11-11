import threading

from fastapi import FastAPI

from backend.api import jobs
from backend.core.config import Settings, get_settings
from backend.core.jobs import JobStore
from backend.core.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(title="Patent Automation API", version="0.1.0")
    app.state.settings = settings
    app.state.store = JobStore(settings.storage_dir)
    app.state.job_semaphore = threading.BoundedSemaphore(settings.max_concurrent_jobs)
    app.include_router(jobs.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}  # MCP / LLM reachability checks are added in later phases

    return app


app = create_app()
