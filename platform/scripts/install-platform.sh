#!/usr/bin/env bash
# Install operators (OLM + DSC), wait CRDs, data CRs, LibreChat Helm, then the agent overlay.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NS="${NS:-demo-granite}"

oc apply -k "${ROOT}/platform/operators"
"${ROOT}/platform/scripts/wait-crds.sh"

oc new-project "${NS}" --skip-config-write 2>/dev/null || true

if [[ ! -f /tmp/demo-secrets.yaml ]]; then
  echo "Create /tmp/demo-secrets.yaml from gitops/base/secrets/demo-secrets.yaml.example" >&2
  echo "and merge gitops/base/secrets/demo-secrets-operators.yaml.example" >&2
  exit 1
fi
oc apply -f /tmp/demo-secrets.yaml

oc apply -k "${ROOT}/platform/operands"

helm upgrade --install librechat "${ROOT}/platform/charts/librechat" -n "${NS}" \
  --set fullnameOverride=librechat \
  --set existingSecret=demo-librechat \
  --set orchestrator.url=http://orchestrator.${NS}.svc.cluster.local:8080/v1 \
  --set llamastack.url=http://llamastack.${NS}.svc.cluster.local:8321/v1/openai/v1 \
  --set model=granite-3-0-8b-instruct

# Optional equivalent:
# helm upgrade --install granite-agent-stack "${ROOT}/platform/charts/granite-agent-stack" \
#   -n "${NS}" -f "${ROOT}/platform/values/demo.yaml"

oc apply -k "${ROOT}/gitops/overlays/demo-with-operators"
oc -n "${NS}" get pods,route
oc get cluster.postgresql.cnpg.io,mongodbcommunity -n "${NS}"
