from __future__ import annotations

import os

import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")
MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")


def chat(*, system: str, user: str, model: str = MODEL,
         temperature: float = 0.3, json_mode: bool = True) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": temperature,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    r = httpx.post(f"{OLLAMA_URL}/chat/completions", json=payload, timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
