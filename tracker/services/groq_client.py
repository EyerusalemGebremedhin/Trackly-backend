import json
import httpx

from tracker.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def call_groq_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Calls Groq's chat completions endpoint and expects a JSON object back.
    Raises RuntimeError with a clear message if the key is missing or the call fails,
    so the caller can decide how to degrade gracefully.
    """
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set - add it to backend/.env")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(GROQ_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return json.loads(content)
