#!/usr/bin/env bash
# Probe Granite (or another MaaS model) through the cluster gateway.
set -euo pipefail

DOMAIN="${DOMAIN:-$(oc get ingresses.config/cluster -o jsonpath='{.spec.domain}')}"
HOST="${MAAS_HOST:-https://maas.${DOMAIN}}"
MODEL="${MODEL:-granite-3-0-8b-instruct}"
KEY="${MAAS_API_KEY:-}"

if [[ -z "${KEY}" ]]; then
  echo "MAAS_API_KEY is empty; create one with ./scripts/create-maas-key.sh" >&2
  exit 1
fi

echo "GET ${HOST}/v1/models"
curl -sk -H "Authorization: Bearer ${KEY}" "${HOST}/v1/models" | jq .

URL="${HOST}/ai-models/${MODEL}/v1/chat/completions"
echo "POST ${URL}"
curl -sk -H "Authorization: Bearer ${KEY}" -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with the word granite.\"}],\"max_tokens\":32}" \
  "${URL}" | jq .
