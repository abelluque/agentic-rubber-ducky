"""OpenAI-compatible adapter so LibreChat can drive the multi-agent pipeline."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from pipeline import run_pipeline

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
app = FastAPI(title="granite-devops-orchestrator", version="0.1.0")
MODEL = os.environ.get("MAAS_MODEL", "granite-3-0-8b-instruct")


class ChatMessage(BaseModel):
    role: str
    content: str | None = ""


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool | None = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [{"id": MODEL, "object": "model", "owned_by": "rhoai-maas"}],
    }


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest) -> dict[str, Any]:
    user_text = _last_user(req.messages)
    content = run_pipeline(user_text)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model or MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _last_user(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content:
            return message.content
    return "Optimiza calculate_order_total, abre un PR y despliega orders-qa."
