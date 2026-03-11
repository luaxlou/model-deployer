#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${MDP_ENDPOINT:-}" ]]; then
  HOST_PORT=$(docker inspect -f '{{(index (index .NetworkSettings.Ports "18080/tcp") 0).HostPort}}' example-model-prod 2>/dev/null || true)
  if [[ -z "${HOST_PORT}" ]]; then
    ENDPOINT="http://127.0.0.1:18080"
  else
    ENDPOINT="http://127.0.0.1:${HOST_PORT}"
  fi
else
  ENDPOINT="${MDP_ENDPOINT}"
fi

curl -fsS "${ENDPOINT}/healthz" >/dev/null

RESP=$(curl -fsS -X POST "${ENDPOINT}/predict" \
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
