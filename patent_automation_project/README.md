# Patent Automation Platform — Starter

A file-based starter for an internal prior-art discovery and technical-comparison workflow.

## What it does today
- Accepts a `.pptx` patent disclosure.
- Extracts slide text and tables into Markdown with slide references.
- Uses a configurable OpenAI-compatible LLM endpoint to extract structured invention features and propose search queries.
- Provides a safe MCP discovery scaffold: it connects to the configured MCP server, lists its tools, and requires you to map an actual tool name/schema before calling it.
- Stores each job in an isolated folder under `storage/jobs/`.

## What is intentionally not implemented yet
Patent-site-specific retrieval, legal novelty opinions, production authentication/authorization, OCR for image-only slides, robust claim parsing, and corporate report generation are extension points. Do not treat similarity scores as legal conclusions.

## Requirements
- Python 3.11+
- Node.js 20+ (for the optional React UI)
- Access to an approved Hermes-compatible LLM endpoint
- An existing MCP server process/endpoint with web search and page retrieval tools, if you want MCP search

## Backend setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

Set `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `.env`. The adapter expects an OpenAI-compatible `/chat/completions` endpoint. If your Hermes endpoint uses a different API shape, change `app/services/llm_client.py`.

## MCP setup (important)
This starter does not assume tool names or schemas. Configure `MCP_SERVER_COMMAND` and `MCP_SERVER_ARGS` only after inspecting your installed MCP server's documented launch method. Start by calling `GET /api/mcp/tools`; inspect the returned names and JSON schemas. Then set `MCP_SEARCH_TOOL` and update `MCP_SEARCH_ARGUMENTS_TEMPLATE` to match the real schema. Never guess a tool name or send arbitrary arguments.

The current MCP adapter supports a stdio MCP server. If your MCP server uses HTTP/SSE or Streamable HTTP, replace the transport setup in `app/services/mcp_client.py` with the transport supported by your installed SDK/server version.

## Frontend setup
```bash
cd frontend
npm install
npm run dev
```
The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## API workflow
1. `POST /api/jobs` with a `.pptx` file.
2. `POST /api/jobs/{job_id}/extract` to create Markdown.
3. `POST /api/jobs/{job_id}/analyze` to extract features and generate search queries.
4. `GET /api/jobs/{job_id}` to inspect the job artifacts.

## Data and security
- Local file storage only; no database is required for this starter.
- Treat uploaded disclosures as confidential. Do not send them to external model providers unless your organization has approved the endpoint, retention policy, and data-processing terms.
- Add SSO/RBAC, encryption at rest, audit logging, malware scanning, upload limits, retention/deletion controls, and secrets management before corporate deployment.
- Patent search coverage depends on the configured provider and its terms/rate limits. Preserve original source URLs and retrieval timestamps.

## Project layout
```text
backend/app/
  main.py
  config.py
  models.py
  api/routes.py
  services/pptx_extractor.py
  services/llm_client.py
  services/patent_pipeline.py
  services/mcp_client.py
storage/jobs/
frontend/
templates/
docs/
```
