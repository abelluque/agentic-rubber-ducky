"""GitHub tools used by the GitHub Agent. Mutations honor DRY_RUN."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from granite_mcp.safety import dry_run, require_repo

API = os.environ.get("GITHUB_API", "https://api.github.com")


def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    }


def _split(repo: str) -> tuple[str, str]:
    owner, name = repo.split("/", 1)
    return owner, name


def github_get_file(repo: str, path: str, ref: str = "main") -> dict[str, Any]:
    blocked = require_repo(repo)
    if blocked:
        return blocked
    if dry_run() and not os.environ.get("GITHUB_TOKEN"):
        return {
            "ok": True,
            "dry_run": True,
            "repo": repo,
            "path": path,
            "ref": ref,
            "content": None,
            "message": "dry-run: file fetch skipped (no GitHub token)",
        }
    owner, name = _split(repo)
    url = f"{API}/repos/{owner}/{name}/contents/{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, headers=_headers(), params={"ref": ref})
        if response.status_code != 200:
            return {"ok": False, "error": response.text, "status": response.status_code}
        payload = response.json()
    import base64

    content = base64.b64decode(payload.get("content") or "").decode("utf-8")
    return {
        "ok": True,
        "dry_run": False,
        "path": path,
        "sha": payload.get("sha"),
        "content": content,
    }


def github_create_branch(repo: str, from_ref: str = "main", branch: str | None = None) -> dict[str, Any]:
    blocked = require_repo(repo)
    if blocked:
        return blocked
    branch = branch or f"agent/granite-{int(time.time())}"
    if dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "repo": repo,
            "branch": branch,
            "from_ref": from_ref,
            "message": "dry-run: branch not created",
        }
    owner, name = _split(repo)
    with httpx.Client(timeout=30.0) as client:
        ref = client.get(f"{API}/repos/{owner}/{name}/git/ref/heads/{from_ref}", headers=_headers())
        if ref.status_code != 200:
            return {"ok": False, "error": ref.text, "status": ref.status_code}
        sha = ref.json()["object"]["sha"]
        created = client.post(
            f"{API}/repos/{owner}/{name}/git/refs",
            headers=_headers(),
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        if created.status_code not in {200, 201}:
            return {"ok": False, "error": created.text, "status": created.status_code}
    return {"ok": True, "dry_run": False, "branch": branch, "sha": sha}


def github_commit_files(
    repo: str,
    branch: str,
    files: list[dict[str, str]],
    message: str,
) -> dict[str, Any]:
    """Create or update files on a branch. Each item is {path, content}."""
    blocked = require_repo(repo)
    if blocked:
        return blocked
    if dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "repo": repo,
            "branch": branch,
            "files": [item.get("path") for item in files],
            "message": message,
        }
    owner, name = _split(repo)
    results = []
    with httpx.Client(timeout=30.0) as client:
        for item in files:
            path = item["path"]
            existing = client.get(
                f"{API}/repos/{owner}/{name}/contents/{path}",
                headers=_headers(),
                params={"ref": branch},
            )
            sha = existing.json().get("sha") if existing.status_code == 200 else None
            import base64

            body = {
                "message": message,
                "content": base64.b64encode(item["content"].encode("utf-8")).decode("ascii"),
                "branch": branch,
            }
            if sha:
                body["sha"] = sha
            put = client.put(
                f"{API}/repos/{owner}/{name}/contents/{path}",
                headers=_headers(),
                json=body,
            )
            if put.status_code not in {200, 201}:
                return {"ok": False, "error": put.text, "path": path, "status": put.status_code}
            results.append({"path": path, "commit": put.json().get("commit", {}).get("sha")})
    return {"ok": True, "dry_run": False, "files": results}


def github_create_pr(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> dict[str, Any]:
    blocked = require_repo(repo)
    if blocked:
        return blocked
    if dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "html_url": f"https://github.com/{repo}/compare/{base}...{head}?expand=1",
            "title": title,
            "head": head,
            "base": base,
            "message": "dry-run: pull request not opened",
        }
    owner, name = _split(repo)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{API}/repos/{owner}/{name}/pulls",
            headers=_headers(),
            json={"title": title, "body": body, "head": head, "base": base},
        )
        if response.status_code not in {200, 201}:
            return {"ok": False, "error": response.text, "status": response.status_code}
        payload = response.json()
    return {
        "ok": True,
        "dry_run": False,
        "number": payload.get("number"),
        "html_url": payload.get("html_url"),
        "title": payload.get("title"),
    }
