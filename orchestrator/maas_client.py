"""Call IBM Granite through the RHOAI MaaS OpenAI-compatible gateway."""

from __future__ import annotations

import os
from openai import OpenAI


def maas_client() -> OpenAI:
    base = os.environ.get("MAAS_BASE_URL", "").rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    api_key = os.environ.get("MAAS_API_KEY", "dummy")
    verify = os.environ.get("MAAS_TLS_VERIFY", "true").lower() in {"1", "true", "yes"}
    return OpenAI(base_url=base, api_key=api_key, http_client=_http(verify))


def _http(verify: bool):
    import httpx

    return httpx.Client(verify=verify, timeout=120.0)


def chat(messages: list[dict[str, str]], temperature: float = 0.1, max_tokens: int = 2048) -> str:
    model = os.environ.get("MAAS_MODEL", "granite-3-0-8b-instruct")
    client = maas_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("empty completion from MaaS")
    return content
