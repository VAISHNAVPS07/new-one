import json
from app.models import FeatureExtraction, AnalysisResult
from app.services.llm_client import chat

FEATURE_PROMPT = '''
You are assisting with technical prior-art discovery. Extract only facts supported by
the disclosure. Do not infer missing technical details. Return valid JSON only with:
invention_title, technical_domain, problem, proposed_solution, key_features (array),
components (array), advantages (array), keywords (array), synonyms (object of arrays).
If a field is absent, use an empty string or empty array.
'''

QUERY_PROMPT = '''
Create a diverse set of patent prior-art search queries from the supplied invention
features. Include exact phrase, feature combinations, component/architecture,
synonym-expanded, and broader concept queries. Keep queries concise and suitable for
patent search systems. Return valid JSON only: {"search_queries": ["..."]}.
Do not add facts not present in the input.
'''

def _json_from_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(text[start:end+1])

async def analyze_markdown(markdown: str) -> AnalysisResult:
    raw_features = await chat(FEATURE_PROMPT, markdown)
    features = FeatureExtraction.model_validate(_json_from_text(raw_features))
    raw_queries = await chat(QUERY_PROMPT, features.model_dump_json(indent=2))
    query_data = _json_from_text(raw_queries)
    queries = query_data.get("search_queries", [])
    if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
        raise ValueError("search_queries must be an array of strings")
    return AnalysisResult(features=features, search_queries=queries)
