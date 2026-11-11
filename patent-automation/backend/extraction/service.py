"""Stage implementations for Phase 2: extraction/validation and Markdown conversion."""
import json
import shutil

from backend.core.config import Settings
from backend.core.pipeline import JobContext, StageRunner

from .markdown_writer import render_markdown
from .models import ExtractedDeck
from .ocr import run_ocr
from .pptx_parser import parse_pptx
from .template_validator import TemplateSpec, validate_deck


def extract_stage(ctx: JobContext) -> dict:
    paths = ctx.paths
    src = ctx.store.input_file(paths)
    # clear previous images so reruns don't leave stale files
    shutil.rmtree(paths.images, ignore_errors=True)
    paths.images.mkdir()
    deck = parse_pptx(src, paths.images, paths.root, ocr=run_ocr if ctx.settings.ocr_enabled else None)
    (paths.extracted / "slides.json").write_text(deck.model_dump_json(indent=2), encoding="utf-8")

    spec = TemplateSpec.load(ctx.settings.template_config)
    report = validate_deck(deck, spec)
    (paths.extracted / "validation.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return {"slide_count": deck.slide_count, "validation_status": report.status}


def markdown_stage(ctx: JobContext) -> dict:
    paths = ctx.paths
    deck = ExtractedDeck.model_validate_json((paths.extracted / "slides.json").read_text(encoding="utf-8"))
    md = render_markdown(deck)
    (paths.markdown / "disclosure.md").write_text(md, encoding="utf-8")
    return {"characters": len(md)}


PHASE2_RUNNERS = [
    StageRunner("ppt_extraction", extract_stage, ["extracted/slides.json", "extracted/validation.json"]),
    StageRunner("markdown_conversion", markdown_stage, ["markdown/disclosure.md"]),
]


def load_validation(ctx_paths) -> dict | None:
    f = ctx_paths.extracted / "validation.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
