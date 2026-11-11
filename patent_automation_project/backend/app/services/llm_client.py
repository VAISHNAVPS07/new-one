import httpx
from app.config import settings

class LLMNotConfigured(RuntimeError):
    pass

async def chat(system_prompt: str, user_prompt: str) -> str:
    if not (settings.llm_base_url and settings.llm_model):
        raise LLMNotConfigured("Configure LLM_BASE_URL and LLM_MODEL in backend/.env")
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    payload = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]
