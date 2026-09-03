#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/mcp-servers/src"
python3 - <<'PY'
from granite_mcp.ast_analyzer import analyze_python_source, validate_python_source

src = open("sample-app/src/orders/pricing.py", encoding="utf-8").read()
report = analyze_python_source(src, "calculate_order_total")
assert report["ok"], report
assert report["hotspot"] is True
assert report["nested_loop_depth"] >= 2
assert validate_python_source(src)["ok"]
print("ast-selftest: ok", report["hint"])
PY
