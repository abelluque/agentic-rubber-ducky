"""Allowlist and dry-run guards shared by every tool server."""

from __future__ import annotations

import os
from typing import Iterable


def env_flag(name: str, default: str = "true") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def dry_run() -> bool:
    return env_flag("DRY_RUN", "true")


def _csv(name: str) -> set[str]:
    raw = os.environ.get(name, "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def allowed_repos() -> set[str]:
    return _csv("ALLOWED_REPOS")


def allowed_apps() -> set[str]:
    return _csv("ALLOWED_ARGOCD_APPS")


def allowed_namespaces() -> set[str]:
    return _csv("ALLOWED_NAMESPACES")


def deny(kind: str, value: str, allowed: Iterable[str]) -> dict:
    allowed_list = sorted(allowed)
    return {
        "ok": False,
        "error": f"{kind} {value!r} is not allowlisted",
        "allowed": allowed_list,
        "dry_run": dry_run(),
    }


def require_repo(repo: str) -> dict | None:
    allowed = allowed_repos()
    if allowed and repo not in allowed:
        return deny("repository", repo, allowed)
    return None


def require_app(app: str) -> dict | None:
    allowed = allowed_apps()
    if allowed and app not in allowed:
        return deny("argocd application", app, allowed)
    return None


def require_namespace(namespace: str) -> dict | None:
    allowed = allowed_namespaces()
    if allowed and namespace not in allowed:
        return deny("namespace", namespace, allowed)
    return None
