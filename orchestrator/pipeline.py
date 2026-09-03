"""Multi-agent pipeline: Code → GitHub → Argo CD / OpenShift QA."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import httpx

from agents import CODE_SYSTEM
from maas_client import chat

log = logging.getLogger("orchestrator")

DEFAULT_REPO = os.environ.get("DEFAULT_REPO", "example/orders")
DEFAULT_PATH = os.environ.get("DEFAULT_FILE_PATH", "sample-app/src/orders/pricing.py")
DEFAULT_FUNCTION = os.environ.get("DEFAULT_FUNCTION", "calculate_order_total")
DEFAULT_APP = os.environ.get("DEFAULT_ARGOCD_APP", "orders-qa")
DEFAULT_NS = os.environ.get("DEFAULT_NAMESPACE", "orders-qa")
DEFAULT_DEPLOYMENT = os.environ.get("DEFAULT_DEPLOYMENT", "orders-qa")
BASE_BRANCH = os.environ.get("DEFAULT_BASE_BRANCH", "main")

MCP = {
    "ast": os.environ.get("MCP_AST_URL", "http://mcp-ast:8000"),
    "github": os.environ.get("MCP_GITHUB_URL", "http://mcp-github:8000"),
    "argocd": os.environ.get("MCP_ARGOCD_URL", "http://mcp-argocd:8000"),
    "ocp": os.environ.get("MCP_OCP_URL", "http://mcp-ocp:8000"),
}


def invoke(role: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    url = f"{MCP[role].rstrip('/')}/invoke"
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json={"tool": tool, "arguments": arguments})
        response.raise_for_status()
        payload = response.json()
    log.info("tool", extra={"role": role, "tool": tool, "ok": payload.get("ok")})
    return payload


def _strip_fences(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:python)?\s*([\s\S]*?)\s*```$", text)
    if match:
        return match.group(1).strip()
    return text


def _fallback_source() -> str:
    fallback = os.environ.get("FALLBACK_SOURCE_PATH", "/opt/app-root/src/fallback/pricing.py")
    if os.path.exists(fallback):
        return open(fallback, encoding="utf-8").read()
    return (
        "def calculate_order_total(items, tax_rate=0.21):\n"
        "    total = 0.0\n"
        "    for item in items:\n"
        "        duplicate_count = 0\n"
        "        for other in items:\n"
        "            if other.get('sku') == item.get('sku'):\n"
        "                duplicate_count += 1\n"
        "        unit = float(item.get('price', 0))\n"
        "        qty = int(item.get('qty', 1))\n"
        "        discount = 0.05 if duplicate_count > 1 else 0.0\n"
        "        total += unit * qty * (1.0 - discount)\n"
        "    return round(total * (1.0 + tax_rate), 2)\n"
    )


def run_pipeline(user_text: str) -> str:
    started = time.time()
    steps: list[str] = []

    source_pack = invoke(
        "github",
        "github_get_file",
        {"repo": DEFAULT_REPO, "path": DEFAULT_PATH, "ref": BASE_BRANCH},
    )
    source = source_pack.get("content") or _fallback_source()
    if source_pack.get("ok") and source_pack.get("content"):
        steps.append(f"- Código leído de `{DEFAULT_REPO}@{BASE_BRANCH}:{DEFAULT_PATH}`")
    else:
        steps.append("- Código tomado del fallback local de `sample-app` (GitHub no disponible o dry-run sin token)")

    analysis = invoke(
        "ast",
        "analyze_python_source",
        {"source": source, "function_name": DEFAULT_FUNCTION},
    )
    if not analysis.get("ok"):
        return _fail("Code Agent", analysis, steps)
    steps.append(
        f"- AST: función `{analysis.get('target_function')}` "
        f"nested_loop_depth={analysis.get('nested_loop_depth')} hotspot={analysis.get('hotspot')}"
    )

    prompt = (
        f"Pedido del usuario:\n{user_text}\n\n"
        f"Informe AST:\n{analysis}\n\n"
        f"Archivo actual:\n{source}\n"
    )
    refactored = None
    last_error = None
    for attempt in range(1, 3):
        raw = chat(
            [
                {"role": "system", "content": CODE_SYSTEM},
                {
                    "role": "user",
                    "content": prompt
                    if last_error is None
                    else prompt + f"\nEl intento anterior no compiló: {last_error}\nCorrige y devuelve el archivo completo.\n",
                },
            ]
        )
        candidate = _strip_fences(raw)
        validation = invoke("ast", "validate_python_source", {"source": candidate})
        if validation.get("ok"):
            refactored = candidate
            steps.append(f"- Granite (MaaS) refactor válido en intento {attempt}")
            break
        last_error = validation.get("error")
        steps.append(f"- Intento {attempt} inválido: {last_error}")
    if refactored is None:
        return _fail("Code Agent", {"error": last_error}, steps)

    branch_name = f"agent/granite-{int(time.time())}"
    branch = invoke(
        "github",
        "github_create_branch",
        {"repo": DEFAULT_REPO, "from_ref": BASE_BRANCH, "branch": branch_name},
    )
    if not branch.get("ok"):
        return _fail("GitHub Agent", branch, steps)
    actual_branch = branch.get("branch") or branch_name
    steps.append(f"- Rama `{actual_branch}` (dry_run={branch.get('dry_run')})")

    commit = invoke(
        "github",
        "github_commit_files",
        {
            "repo": DEFAULT_REPO,
            "branch": actual_branch,
            "message": f"refactor: linearize {DEFAULT_FUNCTION} via Granite MaaS agent",
            "files": [{"path": DEFAULT_PATH, "content": refactored}],
        },
    )
    if not commit.get("ok"):
        return _fail("GitHub Agent", commit, steps)

    pr = invoke(
        "github",
        "github_create_pr",
        {
            "repo": DEFAULT_REPO,
            "title": f"refactor: {DEFAULT_FUNCTION} (Granite MaaS agent)",
            "head": actual_branch,
            "base": BASE_BRANCH,
            "body": (
                "Pull Request abierto por el agente DevOps (IBM Granite sobre RHOAI MaaS).\n\n"
                f"Hotspot original: nested_loop_depth={analysis.get('nested_loop_depth')}.\n"
            ),
        },
    )
    if not pr.get("ok"):
        return _fail("GitHub Agent", pr, steps)
    steps.append(f"- PR: {pr.get('html_url')} (dry_run={pr.get('dry_run')})")

    sync = invoke("argocd", "argocd_sync_app", {"app": DEFAULT_APP, "prune": False})
    if not sync.get("ok"):
        return _fail("Deploy Agent", sync, steps)
    steps.append(
        f"- Argo CD `{DEFAULT_APP}` sync={sync.get('sync')} health={sync.get('health')} dry_run={sync.get('dry_run')}"
    )

    pods = invoke("ocp", "ocp_list_pods", {"namespace": DEFAULT_NS})
    if not pods.get("ok"):
        return _fail("Deploy Agent", pods, steps)
    dep = invoke(
        "ocp",
        "ocp_deployment_status",
        {"namespace": DEFAULT_NS, "name": DEFAULT_DEPLOYMENT},
    )

    elapsed_ms = int((time.time() - started) * 1000)
    pod_rows = "\n".join(
        f"| `{item.get('name')}` | {item.get('phase')} | {item.get('ready')} | {item.get('restarts')} |"
        for item in pods.get("pods") or []
    ) or "| — | — | — | — |"

    dry = any(
        [
            branch.get("dry_run"),
            commit.get("dry_run"),
            pr.get("dry_run"),
            sync.get("dry_run"),
            pods.get("dry_run"),
        ]
    )
    banner = "*(DRY_RUN: no se mutó GitHub ni Argo CD)*\n\n" if dry else ""

    return (
        f"{banner}## Refactor (`{DEFAULT_FUNCTION}`)\n\n"
        f"- Informe AST: nested_loop_depth={analysis.get('nested_loop_depth')}, hotspot={analysis.get('hotspot')}\n"
        f"- Validación `compile()`: OK\n"
        f"- Modelo: `{os.environ.get('MAAS_MODEL', 'granite-3-0-8b-instruct')}` vía MaaS\n\n"
        f"```python\n{refactored}\n```\n\n"
        f"## GitHub\n\n"
        f"- Repositorio: `{DEFAULT_REPO}`\n"
        f"- Rama: `{actual_branch}`\n"
        f"- Pull Request: {pr.get('html_url')}\n\n"
        f"## GitOps (Argo CD)\n\n"
        f"- Application: `{DEFAULT_APP}`\n"
        f"- Sync: `{sync.get('sync')}`\n"
        f"- Health: `{sync.get('health')}`\n\n"
        f"## OpenShift QA (`{DEFAULT_NS}`)\n\n"
        f"| Pod | Phase | Ready | Restarts |\n| --- | --- | --- | --- |\n{pod_rows}\n\n"
        f"Deployment `{DEFAULT_DEPLOYMENT}`: ready={dep.get('ready_replicas')}/{dep.get('replicas')} "
        f"(dry_run={dep.get('dry_run')})\n\n"
        f"## Pasos\n\n" + "\n".join(steps) + f"\n\n_elapsed_ms={elapsed_ms}_\n"
    )


def _fail(agent: str, payload: dict[str, Any], steps: list[str]) -> str:
    return (
        f"## Error en {agent}\n\n"
        f"```json\n{payload}\n```\n\n"
        f"## Pasos completados\n\n" + "\n".join(steps) + "\n"
    )
