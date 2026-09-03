#!/usr/bin/env bash
# Probe Granite through the *hub* MaaS gateway (OpenAI-compatible).
# Do NOT derive the hostname from the spoke cluster ingress.
set -euo pipefail

MODEL="${MODEL:-granite-3-0-8b-instruct}"
KEY="${MAAS_API_KEY:-}"
HOST="${MAAS_HOST:-}"

if [[ -z "${HOST}" ]]; then
  echo "Set MAAS_HOST=https://maas.apps.<HUB_DOMAIN> (MaaS cluster, not the spoke)." >&2
  exit 1
fi
if [[ -z "${KEY}" ]]; then
  echo "MAAS_API_KEY is empty; create one with KUBECONFIG of the hub: ./scripts/create-maas-key.sh" >&2
  exit 1
fi

HOST="${HOST%/}"
echo "GET ${HOST}/v1/models"
curl -sk -H "Authorization: Bearer ${KEY}" "${HOST}/v1/models" | jq .

URL="${HOST}/ai-models/${MODEL}/v1/chat/completions"
echo "POST ${URL}"
curl -sk -H "Authorization: Bearer ${KEY}" -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the word granite.\"}],\"max_tokens\":32}" \
  "${URL}" | jq .
