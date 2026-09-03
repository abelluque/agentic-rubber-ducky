#!/usr/bin/env bash
set -euo pipefail

wait_crd() {
  local crd="$1"
  echo "waiting for CRD ${crd}"
  for _ in $(seq 1 60); do
    if oc get crd "${crd}" >/dev/null 2>&1; then
      oc wait --for=condition=Established "crd/${crd}" --timeout=120s
      return 0
    fi
    sleep 10
  done
  echo "timeout waiting for ${crd}" >&2
  return 1
}

wait_crd llamastackdistributions.llamastack.io
wait_crd clusters.postgresql.cnpg.io
wait_crd mongodbcommunity.mongodbcommunity.mongodb.com
echo "all demo CRDs Established"
