"""Argo CD tools used by the Deploy Agent."""

from __future__ import annotations

import os
from typing import Any

import httpx

from granite_mcp.safety import dry_run, require_app


def _base() -> str:
    return os.environ.get("ARGOCD_SERVER", "").rstrip("/")


def _headers() -> dict[str, str]:
    token = os.environ.get("ARGOCD_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def argocd_get_app(app: str) -> dict[str, Any]:
    blocked = require_app(app)
    if blocked:
        return blocked
    if dry_run() or not _base():
        return {
            "ok": True,
            "dry_run": True,
            "app": app,
            "sync": "Unknown",
            "health": "Unknown",
            "message": "dry-run: Argo CD not contacted",
        }
    url = f"{_base()}/api/v1/applications/{app}"
    verify = os.environ.get("ARGOCD_TLS_VERIFY", "true").lower() in {"1", "true", "yes"}
    with httpx.Client(timeout=30.0, verify=verify) as client:
        response = client.get(url, headers=_headers())
        if response.status_code != 200:
            return {"ok": False, "error": response.text, "status": response.status_code}
        payload = response.json()
    status = payload.get("status") or {}
    return {
        "ok": True,
        "dry_run": False,
        "app": app,
        "sync": (status.get("sync") or {}).get("status"),
        "health": (status.get("health") or {}).get("status"),
        "revision": (status.get("sync") or {}).get("revision"),
    }


def argocd_sync_app(app: str, prune: bool = False) -> dict[str, Any]:
    blocked = require_app(app)
    if blocked:
        return blocked
    if prune:
        return {"ok": False, "error": "prune is disabled for the demo agent"}
    if dry_run() or not _base():
        return {
            "ok": True,
            "dry_run": True,
            "app": app,
            "sync": "Synced",
            "health": "Healthy",
            "message": "dry-run: sync not executed",
        }
    url = f"{_base()}/api/v1/applications/{app}/sync"
    verify = os.environ.get("ARGOCD_TLS_VERIFY", "true").lower() in {"1", "true", "yes"}
    with httpx.Client(timeout=60.0, verify=verify) as client:
        response = client.post(url, headers=_headers(), json={"prune": False})
        if response.status_code not in {200, 201}:
            return {"ok": False, "error": response.text, "status": response.status_code}
    return argocd_get_app(app)
