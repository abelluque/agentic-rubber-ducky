"""Read-only OpenShift checks against the target/QA cluster."""

from __future__ import annotations

import os
from typing import Any

from granite_mcp.safety import dry_run, require_namespace

try:
    from kubernetes import client, config
except ImportError:  # pragma: no cover - optional at unit-test time
    client = None
    config = None


def _load() -> None:
    kubeconfig = os.environ.get("TARGET_KUBECONFIG", "/var/run/secrets/target/kubeconfig")
    if config is None:
        raise RuntimeError("kubernetes client is not installed")
    if os.path.exists(kubeconfig):
        config.load_kube_config(config_file=kubeconfig)
    else:
        config.load_incluster_config()


def ocp_list_pods(namespace: str, label_selector: str | None = None) -> dict[str, Any]:
    blocked = require_namespace(namespace)
    if blocked:
        return blocked
    if dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "namespace": namespace,
            "pods": [
                {
                    "name": "orders-qa-demo-0",
                    "phase": "Running",
                    "ready": "1/1",
                    "restarts": 0,
                }
            ],
            "message": "dry-run: target cluster not contacted",
        }
    _load()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace=namespace, label_selector=label_selector or None)
    items = []
    for pod in pods.items:
        ready = 0
        total = len(pod.status.container_statuses or [])
        restarts = 0
        for status in pod.status.container_statuses or []:
            if status.ready:
                ready += 1
            restarts += status.restart_count
        items.append(
            {
                "name": pod.metadata.name,
                "phase": pod.status.phase,
                "ready": f"{ready}/{total}",
                "restarts": restarts,
            }
        )
    return {"ok": True, "dry_run": False, "namespace": namespace, "pods": items}


def ocp_deployment_status(namespace: str, name: str) -> dict[str, Any]:
    blocked = require_namespace(namespace)
    if blocked:
        return blocked
    if dry_run():
        return {
            "ok": True,
            "dry_run": True,
            "namespace": namespace,
            "name": name,
            "ready_replicas": 1,
            "replicas": 1,
            "message": "dry-run: target cluster not contacted",
        }
    _load()
    apps = client.AppsV1Api()
    dep = apps.read_namespaced_deployment(name=name, namespace=namespace)
    spec_replicas = dep.spec.replicas or 0
    ready = dep.status.ready_replicas or 0
    return {
        "ok": True,
        "dry_run": False,
        "namespace": namespace,
        "name": name,
        "replicas": spec_replicas,
        "ready_replicas": ready,
        "available": ready >= spec_replicas and spec_replicas > 0,
    }
