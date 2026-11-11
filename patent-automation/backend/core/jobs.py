"""File-based job store. One isolated workspace per job; no database required.

Swap this class for a DB-backed implementation later without touching callers.
"""
import json
import os
import re
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

STAGES = [
    "ppt_extraction",
    "markdown_conversion",
    "feature_extraction",
    "query_generation",
    "patent_search",
    "similarity_analysis",
    "llm_comparison",
    "report_generation",
]
SUBDIRS = ["input", "markdown", "images", "extracted", "queries", "results", "analysis", "reports"]
JOB_ID_RE = re.compile(r"^JOB_[0-9A-Za-z_]+$")


class JobNotFound(Exception):
    pass


@dataclass(frozen=True)
class JobPaths:
    root: Path

    @property
    def input(self) -> Path:
        return self.root / "input"

    @property
    def markdown(self) -> Path:
        return self.root / "markdown"

    @property
    def images(self) -> Path:
        return self.root / "images"

    @property
    def extracted(self) -> Path:
        return self.root / "extracted"

    @property
    def queries(self) -> Path:
        return self.root / "queries"

    @property
    def results(self) -> Path:
        return self.root / "results"

    @property
    def analysis(self) -> Path:
        return self.root / "analysis"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def job_file(self) -> Path:
        return self.root / "job.json"

    @property
    def stage_file(self) -> Path:
        return self.root / "stage_status.json"

    @property
    def job_id(self) -> str:
        return self.root.name

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


def safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return base or "upload"


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


class JobStore:
    def __init__(self, base_dir: Path):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # --- creation / lookup -------------------------------------------------
    def create(self, original_filename: str, owner: str = "anonymous") -> JobPaths:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        job_id = f"JOB_{stamp}_{secrets.token_hex(3)}"
        root = self.base / job_id
        root.mkdir(parents=True)
        for sub in SUBDIRS:
            (root / sub).mkdir()
        paths = JobPaths(root)
        _atomic_write(
            paths.job_file,
            {
                "job_id": job_id,
                "original_filename": safe_filename(original_filename),
                "owner": owner,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        _atomic_write(paths.stage_file, {s: {"status": "pending"} for s in STAGES})
        return paths

    def paths(self, job_id: str) -> JobPaths:
        if not JOB_ID_RE.match(job_id):  # blocks path traversal
            raise JobNotFound(job_id)
        root = self.base / job_id
        if not root.is_dir():
            raise JobNotFound(job_id)
        return JobPaths(root)

    def input_file(self, paths: JobPaths) -> Path:
        files = sorted(p for p in paths.input.glob("*") if p.is_file())
        if not files:
            raise FileNotFoundError("no input file in job workspace")
        return files[0]

    # --- stage status ------------------------------------------------------
    def read_stages(self, paths: JobPaths) -> dict:
        return json.loads(paths.stage_file.read_text(encoding="utf-8"))

    def set_stage(self, paths: JobPaths, stage: str, status: str, error: str | None = None, **extra) -> None:
        with self._lock:
            stages = self.read_stages(paths)
            entry = stages.get(stage, {})
            entry.update({"status": status, "updated_at": datetime.now(timezone.utc).isoformat(), **extra})
            if error:
                entry["error"] = error
            else:
                entry.pop("error", None)
            stages[stage] = entry
            _atomic_write(paths.stage_file, stages)

    # --- summaries ---------------------------------------------------------
    @staticmethod
    def overall_status(stages: dict, registered: list[str]) -> str:
        statuses = [stages.get(s, {}).get("status", "pending") for s in registered]
        if any(s == "failed" for s in statuses):
            return "failed"
        if any(s == "running" for s in statuses):
            return "processing"
        if registered and all(s == "done" for s in statuses):
            return "completed"
        if any(s == "done" for s in statuses):
            return "processing"
        return "uploaded"

    def summary(self, paths: JobPaths, registered: list[str]) -> dict:
        job = json.loads(paths.job_file.read_text(encoding="utf-8"))
        stages = self.read_stages(paths)
        return {**job, "status": self.overall_status(stages, registered), "stages": stages}

    def list_ids(self) -> list[str]:
        return sorted(
            (p.name for p in self.base.iterdir() if p.is_dir() and JOB_ID_RE.match(p.name)),
            reverse=True,
        )
