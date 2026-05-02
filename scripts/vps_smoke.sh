#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://faimatrix.com}"

curl -fsS "${BASE_URL}/health" >/dev/null
curl -fsS "${BASE_URL}/ready" >/dev/null
curl -fsS "${BASE_URL}/version" >/dev/null
curl -fsS "${BASE_URL}/" >/dev/null

echo "VPS smoke checks passed for ${BASE_URL}"
