#!/usr/bin/env bash
# Create a MaaS API key on the *hub* cluster. Use the hub kubeconfig.
# Prints JSON. Copy .key into Secret demo-maas on the spoke. Do not commit it.
set -euo pipefail

if [[ -n "${KUBECONFIG_MAAS:-}" ]]; then
  export KUBECONFIG="${KUBECONFIG_MAAS}"
fi

HOST="${MAAS_HOST:-}"
if [[ -z "${HOST}" ]]; then
  DOMAIN="$(oc get ingresses.config/cluster -o jsonpath='{.spec.domain}')"
  HOST="https://maas.${DOMAIN}"
  echo "MAAS_HOST unset; using hub ingress domain: ${HOST}" >&2
fi
HOST="${HOST%/}"

SUBSCRIPTION="${MAAS_SUBSCRIPTION:-free-models-subscription}"
NAME="${MAAS_KEY_NAME:-granite-demo-spoke}"
EXPIRES="${MAAS_KEY_EXPIRES:-24h}"
TOKEN="$(oc whoami -t)"

echo "POST ${HOST}/maas-api/v1/api-keys (identity=$(oc whoami))" >&2
curl -sk -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${NAME}\",\"expiresIn\":\"${EXPIRES}\",\"subscription\":\"${SUBSCRIPTION}\"}" \
  "${HOST}/maas-api/v1/api-keys"
echo
