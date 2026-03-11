#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://127.0.0.1:8080/healthz >/dev/null

RESP=$(curl -fsS -X POST "http://127.0.0.1:8080/predict" \
  -H "Content-Type: application/json" \
  -d '{"x1": 1.5, "x2": 0.2}')

python3 - "$RESP" <<'PY'
import json
import sys
obj = json.loads(sys.argv[1])
assert "label" in obj
assert "probability" in obj
print("smoke ok", obj)
PY
