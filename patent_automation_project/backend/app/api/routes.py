import json, re, uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.models import JobStatus
from app.services.pptx_extractor import pptx_to_markdown
from app.services.patent_pipeline import analyze_markdown
from app.services.mcp_client import list_mcp_tools, call_configured_search_tool

router = APIRouter(prefix="/api")

def job_path(job_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(404, "Job not found")
    path = settings.jobs_dir / job_id
    if not path.exists():
        raise HTTPException(404, "Job not found")
    return path

@router.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(400, "Upload a .pptx file")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File exceeds configured upload limit")
    job_id = uuid.uuid4().hex[:12]
    root = settings.jobs_dir / job_id
    (root / "input").mkdir(parents=True)
    (root / "markdown").mkdir()
    (root / "analysis").mkdir()
    safe_name = Path(file.filename).name
    (root / "input" / safe_name).write_bytes(content)
    metadata = {"job_id": job_id, "status": "uploaded", "original_filename": safe_name}
    (root / "job.json").write_text(json.dumps(metadata, indent=2))
    return metadata

@router.post("/jobs/{job_id}/extract")
async def extract_job(job_id: str):
    root = job_path(job_id)
    inputs = list((root / "input").glob("*.pptx"))
    if not inputs:
        raise HTTPException(400, "No PPTX input found")
    markdown = pptx_to_markdown(inputs[0])
    target = root / "markdown" / "disclosure.md"
    target.write_text(markdown, encoding="utf-8")
    meta = json.loads((root / "job.json").read_text())
    meta["status"] = "extracted"
    meta["markdown_path"] = str(target)
    (root / "job.json").write_text(json.dumps(meta, indent=2))
    return {"job_id": job_id, "status": "extracted", "markdown": markdown}

@router.post("/jobs/{job_id}/analyze")
async def analyze_job(job_id: str):
    root = job_path(job_id)
    md_path = root / "markdown" / "disclosure.md"
    if not md_path.exists():
        raise HTTPException(400, "Run extraction first")
    try:
        result = await analyze_markdown(md_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(502, f"Analysis failed: {exc}") from exc
    out = root / "analysis" / "analysis.json"
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    meta = json.loads((root / "job.json").read_text())
    meta["status"] = "analyzed"
    meta["analysis_path"] = str(out)
    (root / "job.json").write_text(json.dumps(meta, indent=2))
    return result.model_dump()

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    root = job_path(job_id)
    meta = json.loads((root / "job.json").read_text())
    return meta

@router.get("/mcp/tools")
async def get_mcp_tools():
    try:
        return {"tools": await list_mcp_tools()}
    except Exception as exc:
        raise HTTPException(502, f"MCP discovery failed: {exc}") from exc

@router.post("/jobs/{job_id}/search")
async def search_job(job_id: str):
    root = job_path(job_id)
    analysis_file = root / "analysis" / "analysis.json"
    if not analysis_file.exists():
        raise HTTPException(400, "Run analysis first")
    analysis = json.loads(analysis_file.read_text())
    results = []
    for query in analysis.get("search_queries", []):
        try:
            results.append({"query": query, "result": await call_configured_search_tool(query)})
        except Exception as exc:
            results.append({"query": query, "error": str(exc)})
    target = root / "analysis" / "mcp_search_results.json"
    target.write_text(json.dumps(results, indent=2))
    return {"results": results}
