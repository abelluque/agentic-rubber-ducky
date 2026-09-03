#!/usr/bin/env bash
# Create a short-lived MaaS API key for the free Granite subscription.
# Prints the JSON response. Do not redirect into Git.
set -euo pipefail

DOMAIN="${DOMAIN:-$(oc get ingresses.config/cluster -o jsonpath='{.spec.domain}')}"
HOST="${MAAS_HOST:-https://maas.${DOMAIN}}"
SUBSCRIPTION="${MAAS_SUBSCRIPTION:-free-models-subscription}"
NAME="${MAAS_KEY_NAME:-granite-demo}"
EXPIRES="${MAAS_KEY_EXPIRES:-24h}"
TOKEN="$(oc whoami -t)"

curl -sk -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${NAME}\",\"expiresIn\":\"${EXPIRES}\",\"subscription\":\"${SUBSCRIPTION}\"}" \
  "${HOST}/maas-api/v1/api-keys"
echo
