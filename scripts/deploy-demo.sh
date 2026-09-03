#!/usr/bin/env bash
# Build MCP + orchestrator images in-cluster and apply the demo overlay.
set -euo pipefail

NS="${NS:-demo-granite}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

oc new-project "${NS}" --skip-config-write 2>/dev/null || true

if [[ ! -f /tmp/demo-secrets.yaml ]]; then
  echo "Create /tmp/demo-secrets.yaml from gitops/base/secrets/demo-secrets.yaml.example first." >&2
  exit 1
fi
oc apply -f /tmp/demo-secrets.yaml

oc -n "${NS}" new-build --name=mcp-tools --binary --strategy=docker 2>/dev/null || true
oc -n "${NS}" start-build mcp-tools --from-dir="${ROOT}/mcp-servers" --follow

oc -n "${NS}" new-build --name=orchestrator --binary --strategy=docker 2>/dev/null || true
oc -n "${NS}" start-build orchestrator --from-dir="${ROOT}/orchestrator" --follow

oc apply -k "${ROOT}/gitops/overlays/demo"
oc -n "${NS}" rollout status deploy/orchestrator --timeout=180s || true
oc -n "${NS}" get pods,route
