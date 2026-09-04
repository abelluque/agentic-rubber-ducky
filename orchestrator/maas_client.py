"""Call IBM Granite through the RHOAI MaaS OpenAI-compatible gateway."""

from __future__ import annotations

import os
from openai import BadRequestError, OpenAI


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


def _estimate_tokens(messages: list[dict[str, str]]) -> int:
    chars = sum(len(message.get("content") or "") + 16 for message in messages)
    return max(1, chars // 3)


def chat(
    messages: list[dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> str:
    model = os.environ.get("MAAS_MODEL", "granite-3-0-8b-instruct")
    # Hub granite-3-1-2b-instruct is served with max_model_len=4096 (prompt + output).
    context_len = int(os.environ.get("MAAS_CONTEXT_LEN", "4096"))
    requested = max_tokens if max_tokens is not None else int(os.environ.get("MAAS_MAX_TOKENS", "1024"))
    room = context_len - _estimate_tokens(messages) - 32
    if room < 16:
        raise RuntimeError(
            f"prompt too large for MaaS context (limit={context_len}, requested_output={requested})"
        )
    max_tokens = max(16, min(requested, room))
    client = maas_client()
    last_error: Exception | None = None
    for _ in range(3):
        try:
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
        except BadRequestError as exc:
            last_error = exc
            if max_tokens <= 32:
                break
            max_tokens = max(16, max_tokens // 2)
    assert last_error is not None
    raise last_error
