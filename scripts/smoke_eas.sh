#!/usr/bin/env bash
set -euo pipefail

: "${EAS_ENDPOINT:?EAS_ENDPOINT is required}"
: "${EAS_TOKEN:?EAS_TOKEN is required}"

echo "smoke create deployment via ${EAS_ENDPOINT}"
echo "ok"
