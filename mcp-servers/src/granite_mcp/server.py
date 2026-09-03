"""Unified REST + MCP server. ROLE selects the tool family."""

from __future__ import annotations

import os
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from granite_mcp import argocd_tool, ast_analyzer, github_tool, target_ocp_checker

ROLE = os.environ.get("MCP_ROLE", "ast")

TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "analyze_python_source": ast_analyzer.analyze_python_source,
    "extract_function": ast_analyzer.extract_function,
    "validate_python_source": ast_analyzer.validate_python_source,
    "github_get_file": github_tool.github_get_file,
    "github_create_branch": github_tool.github_create_branch,
    "github_commit_files": github_tool.github_commit_files,
    "github_create_pr": github_tool.github_create_pr,
    "argocd_get_app": argocd_tool.argocd_get_app,
    "argocd_sync_app": argocd_tool.argocd_sync_app,
    "ocp_list_pods": target_ocp_checker.ocp_list_pods,
    "ocp_deployment_status": target_ocp_checker.ocp_deployment_status,
}

ROLE_TOOLS = {
    "ast": ["analyze_python_source", "extract_function", "validate_python_source"],
    "github": ["github_get_file", "github_create_branch", "github_commit_files", "github_create_pr"],
    "argocd": ["argocd_get_app", "argocd_sync_app"],
    "ocp": ["ocp_list_pods", "ocp_deployment_status"],
    "all": list(TOOLS),
}


class InvokeRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title=f"granite-mcp-{ROLE}", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "role": ROLE, "tools": ROLE_TOOLS.get(ROLE, [])}


@app.get("/tools")
def list_tools() -> dict[str, Any]:
    names = ROLE_TOOLS.get(ROLE, [])
    return {"ok": True, "tools": names}


@app.post("/invoke")
def invoke(req: InvokeRequest) -> dict[str, Any]:
    allowed = ROLE_TOOLS.get(ROLE, [])
    if req.tool not in allowed:
        raise HTTPException(status_code=400, detail=f"tool {req.tool!r} not enabled for role {ROLE}")
    fn = TOOLS[req.tool]
    try:
        result = fn(**req.arguments)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "tool": req.tool}
    if isinstance(result, dict) and "ok" not in result:
        result = {"ok": True, **result}
    return result


def _register_mcp() -> None:
    """Optional FastMCP surface for Llama Stack remote::model-context-protocol."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        return

    try:
        mcp = FastMCP(f"granite-{ROLE}")
        for tool_name in ROLE_TOOLS.get(ROLE, []):
            fn = TOOLS[tool_name]
            mcp.tool(name=tool_name)(fn)
        asgi = getattr(mcp, "streamable_http_app", None) or getattr(mcp, "sse_app", None)
        if asgi:
            app.mount("/mcp", asgi() if callable(asgi) else asgi)
    except Exception:  # noqa: BLE001 — REST /invoke remains the supported contract
        return


_register_mcp()
