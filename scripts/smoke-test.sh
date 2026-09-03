#!/usr/bin/env bash
# Port-forward the orchestrator and run one pipeline turn (expects DRY_RUN=true).
set -euo pipefail

NS="${NS:-demo-granite}"
oc -n "${NS}" port-forward svc/orchestrator 18080:8080 >/tmp/orchestrator-pf.log 2>&1 &
PF_PID=$!
trap 'kill ${PF_PID} 2>/dev/null || true' EXIT
sleep 2

curl -sf http://127.0.0.1:18080/health | jq .
BODY="$(curl -sf http://127.0.0.1:18080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"granite-3-0-8b-instruct","messages":[{"role":"user","content":"Optimiza calculate_order_total, abre un PR y sincroniza orders-qa."}]}')"
echo "${BODY}" | jq -r '.choices[0].message.content'
echo "${BODY}" | jq -e '.choices[0].message.content | test("calculate_order_total")' >/dev/null
echo "smoke-test: ok"
