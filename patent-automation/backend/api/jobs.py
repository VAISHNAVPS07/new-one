import json
import shutil
import threading

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse

from backend.core.audit import append_audit
from backend.core.jobs import JobNotFound, JobPaths, safe_filename
from backend.core.pipeline import JobContext, run_pipeline
from backend.extraction.service import PHASE2_RUNNERS, load_validation

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Later phases append their runners here (feature extraction, search, ...).
RUNNERS = list(PHASE2_RUNNERS)
ALLOWED_EXT = {".pptx"}


def require_api_key(request: Request) -> str:
    key = request.app.state.settings.api_key
    if not key:
        return "anonymous"  # auth disabled (local development)
    auth = request.headers.get("authorization", "")
    if auth != f"Bearer {key}":
        raise HTTPException(401, "Invalid or missing API key")
    return "api-key"


def _paths(request: Request, job_id: str) -> JobPaths:
    try:
        return request.app.state.store.paths(job_id)
    except JobNotFound:
        raise HTTPException(404, f"Job {job_id} not found")


def _summary(request: Request, paths: JobPaths) -> dict:
    return request.app.state.store.summary(paths, [r.stage for r in RUNNERS])


def _run_locked(request_app, ctx: JobContext, runners) -> bool:
    sem: threading.BoundedSemaphore = request_app.state.job_semaphore
    with sem:
        return run_pipeline(ctx, runners)


@router.post("", status_code=201)
async def create_job(request: Request, file: UploadFile = File(...), actor: str = Depends(require_api_key)):
    name = file.filename or "upload.pptx"
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == ".ppt":
        raise HTTPException(415, "Legacy .ppt is not supported; please save the file as .pptx.")
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, "Only .pptx files are accepted.")

    settings, store = request.app.state.settings, request.app.state.store
    limit = settings.max_upload_mb * 1024 * 1024
    paths = store.create(name, owner=actor)
    dest = paths.input / safe_filename(name)
    size, first = 0, True
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                if first:
                    if not chunk.startswith(b"PK"):  # pptx is a zip container
                        raise HTTPException(400, "File is not a valid .pptx (OOXML) document.")
                    first = False
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "Empty file.")
    except HTTPException:
        shutil.rmtree(paths.root, ignore_errors=True)
        raise
    append_audit(paths.root, "job_created", actor, filename=name, bytes=size)
    return _summary(request, paths)


@router.get("")
def list_jobs(request: Request, _: str = Depends(require_api_key)):
    store = request.app.state.store
    return [_summary(request, store.paths(j)) for j in store.list_ids()]


@router.get("/{job_id}")
def get_job(job_id: str, request: Request, _: str = Depends(require_api_key)):
    return _summary(request, _paths(request, job_id))


@router.post("/{job_id}/validate")
def validate_job(job_id: str, request: Request, actor: str = Depends(require_api_key)):
    """Run extraction + template validation only (no markdown); returns the validation report."""
    paths = _paths(request, job_id)
    ctx = JobContext(request.app.state.store, request.app.state.settings, paths, force=True, actor=actor)
    if not _run_locked(request.app, ctx, RUNNERS[:1]):
        err = request.app.state.store.read_stages(paths)["ppt_extraction"].get("error")
        raise HTTPException(422, f"Could not parse presentation: {err}")
    return load_validation(paths)


@router.post("/{job_id}/start", status_code=202)
def start_job(job_id: str, request: Request, background: BackgroundTasks,
              force: bool = False, actor: str = Depends(require_api_key)):
    """Start (or resume) the pipeline. A failed template validation blocks start unless force=true."""
    paths = _paths(request, job_id)
    report = load_validation(paths)
    if report and report["status"] == "fail" and not force:
        raise HTTPException(409, {"message": "Template validation failed; fix the deck or pass force=true.",
                                  "validation": report})
    ctx = JobContext(request.app.state.store, request.app.state.settings, paths, force=False, actor=actor)
    append_audit(paths.root, "job_started", actor, force=force)
    background.add_task(_run_locked, request.app, ctx, RUNNERS)
    return _summary(request, paths)


@router.get("/{job_id}/stages/{stage}")
def get_stage(job_id: str, stage: str, request: Request, _: str = Depends(require_api_key)):
    paths = _paths(request, job_id)
    stages = request.app.state.store.read_stages(paths)
    if stage not in stages:
        raise HTTPException(404, f"Unknown stage {stage}")
    return {"stage": stage, **stages[stage]}


@router.get("/{job_id}/validation")
def get_validation(job_id: str, request: Request, _: str = Depends(require_api_key)):
    report = load_validation(_paths(request, job_id))
    if report is None:
        raise HTTPException(404, "No validation report yet; call POST /validate first.")
    return report


@router.get("/{job_id}/markdown", response_class=PlainTextResponse)
def get_markdown(job_id: str, request: Request, _: str = Depends(require_api_key)):
    f = _paths(request, job_id).markdown / "disclosure.md"
    if not f.exists():
        raise HTTPException(404, "Markdown not generated yet.")
    return f.read_text(encoding="utf-8")


@router.get("/{job_id}/audit")
def get_audit(job_id: str, request: Request, _: str = Depends(require_api_key)):
    f = _paths(request, job_id).root / "audit.log"
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
