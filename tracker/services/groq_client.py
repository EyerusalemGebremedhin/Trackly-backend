import json
import httpx

from tracker.core.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def call_groq_json(system_prompt: str, user_prompt: str, model: str = "openai/gpt-oss-20b") -> dict:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(GROQ_URL, headers=headers, json=body)
        if resp.status_code != 200:
            print(f"GROQ ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def call_groq_chat(system_prompt: str = None, user_prompt: str = None, model: str = None, temperature: float = 0.7, messages: list = None) -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    use_model = model or "openai/gpt-oss-20b"

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    if messages is not None:
        body = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2048,
        }
    else:
        body = {
            "model": use_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 2048,
        }

    with httpx.Client(timeout=90.0) as client:
        resp = client.post(GROQ_URL, headers=headers, json=body)
        if resp.status_code != 200:
            print(f"GROQ ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return content


def call_groq_vision(system_prompt: str, user_text: str, image_data_url: str, model: str = "qwen/qwen3.6-27b") -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text or "Analyze this image."},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    with httpx.Client(timeout=90.0) as client:
        resp = client.post(GROQ_URL, headers=headers, json=body)
        if resp.status_code != 200:
            print(f"GROQ ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    return content


def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm") -> str:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
    }
    files = {"file": (filename, file_bytes)}
    data = {"model": "whisper-large-v3-turbo", "response_format": "json"}

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(GROQ_TRANSCRIBE_URL, headers=headers, files=files, data=data)
        if resp.status_code != 200:
            print(f"GROQ ERROR {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        result = resp.json()

    return result.get("text", "")
