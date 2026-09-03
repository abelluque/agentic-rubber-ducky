#!/usr/bin/env bash
# Install the agentic stack on the SPOKE OpenShift cluster.
# Hub MaaS must already be reachable at MAAS_HOST; API key Secret is applied here.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
NS="${NS:-demo-granite}"

echo "Current context (must be the spoke cluster, not the MaaS hub): $(oc whoami --show-context 2>/dev/null || oc whoami)" >&2

oc apply -k "${ROOT}/platform/operators"
"${ROOT}/platform/scripts/wait-crds.sh"

oc new-project "${NS}" --skip-config-write 2>/dev/null || true

if [[ ! -f /tmp/demo-secrets.yaml ]]; then
  echo "Create /tmp/demo-secrets.yaml from gitops/base/secrets/demo-secrets.yaml.example" >&2
  echo "(demo-maas.api-key must be issued on the HUB with ./scripts/create-maas-key.sh)" >&2
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

oc apply -k "${ROOT}/gitops/overlays/spoke"
oc -n "${NS}" get pods,route
oc get cluster.postgresql.cnpg.io,mongodbcommunity -n "${NS}" || true
echo "Edit gitops/overlays/spoke MAAS hostnames if still CHANGE_ME, then re-apply." >&2
