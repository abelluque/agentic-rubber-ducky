#!/usr/bin/env bash
# From the *spoke* cluster, call hub MaaS using the orchestrator pod env (MAAS_HOST + MAAS_API_KEY).
set -euo pipefail

NS="${NS:-demo-granite}"
POD="$(oc -n "${NS}" get pod -l app=orchestrator -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "${POD}" ]]; then
  echo "no orchestrator pod in ${NS}" >&2
  exit 1
fi
echo "spoke pod ${POD}" >&2
oc -n "${NS}" exec "${POD}" -- python3 -c '
import json, os, ssl, urllib.request
host = os.environ["MAAS_HOST"].rstrip("/")
key = os.environ["MAAS_API_KEY"]
model = os.environ.get("MAAS_MODEL", "granite-3-0-8b-instruct")
url = f"{host}/ai-models/{model}/v1/chat/completions"
body = json.dumps({
    "model": model,
    "messages": [{"role": "user", "content": "Reply with granite."}],
    "max_tokens": 16,
}).encode()
req = urllib.request.Request(
    url,
    data=body,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    method="POST",
)
print(urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=60).read().decode())
'
