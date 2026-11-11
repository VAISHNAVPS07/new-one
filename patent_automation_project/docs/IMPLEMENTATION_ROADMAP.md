# Implementation Roadmap

## Phase 1 — Disclosure intake
- Confirm PPTX template version and required fields.
- Extract text, tables, speaker notes and images; add OCR/diagram captioning only through approved services.
- Validate missing sections and preserve slide/shape provenance.

## Phase 2 — Structured understanding
- Define a versioned Pydantic schema for invention disclosures.
- Use LLM structured output / JSON schema where supported.
- Add human review and edit/approve steps before search.

## Phase 3 — Search integrations
- Inspect the existing MCP server tool catalog and schemas.
- Configure only verified search/fetch tools.
- Add official EPO OPS and USPTO/PATENTSCOPE or other licensed interfaces where access permits.
- Respect provider terms, rate limits and result attribution.
- Save raw responses, normalized records, query, timestamp and source URL.

## Phase 4 — Ranking and comparison
- Normalize publication number, title, abstract, inventors, dates, family and claims.
- Deduplicate family/publication variants.
- Implement BM25/TF-IDF and embedding similarity; compare independent claims and technical features.
- Calibrate weights using reviewed examples. Display evidence snippets and explain ranking.
- Clearly label results as relevance indicators, not legal opinions.

## Phase 5 — Corporate reports
- Generate DOCX from the approved template, then PDF.
- Include scope, disclosure version, search timestamp, query coverage, sources, evidence and limitations.
- Add report versioning and reproducibility manifest.

## Phase 6 — Production hardening
- SSO/RBAC, tenant/job isolation, encryption, audit events, retention controls, secret vault.
- Queue/background workers, retries, idempotency, cancellation and resumable jobs.
- Monitoring, structured logs, metrics, backups, vulnerability scanning and deployment runbooks.
- Security review for confidential invention disclosures and external model/data processing.
