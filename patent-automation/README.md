# Patent Automation System

Phases 1-2 implemented: project setup, job workspaces, PPTX extraction, template
validation, Markdown conversion, REST API. Later phases plug in as extra `StageRunner`s
(see `backend/api/jobs.py::RUNNERS`).

## Install (Ubuntu 24.04, Python 3.12)
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env

## Run
    uvicorn backend.main:app --reload --port 8000     # docs at /docs

## Try it
    curl -F "file=@disclosure.pptx" localhost:8000/api/jobs        # -> job_id
    curl -X POST localhost:8000/api/jobs/<job_id>/validate          # template report
    curl -X POST localhost:8000/api/jobs/<job_id>/start             # run pipeline
    curl localhost:8000/api/jobs/<job_id>                           # stage status
    curl localhost:8000/api/jobs/<job_id>/markdown

If `PATENT_API_KEY` is set, send `Authorization: Bearer <key>`.

## Test
    python -m pytest -q
Test decks are synthetic, generated in `tests/conftest.py`.

## Customising the template
Edit `config/disclosure_template.yaml` (section patterns, required flag, expected
content). No code changes needed.

## Known limits (Phase 2)
- `.pptx` only. Legacy `.ppt` must be converted first (e.g. `soffice --headless --convert-to pptx`).
- SmartArt and embedded OLE objects are flagged in validation, not extracted.
- Output keeps text, tables, charts, images separately per slide (not interleaved).
- Diagram captioning via a vision LLM and OCR hooks exist (`ocr.py`, `ImageRef.description`);
  captioning is wired in during the LLM phase.
