#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://faimatrix.localhost:8443}"

curl -kfsS "${BASE_URL}/health" >/dev/null
curl -kfsS "${BASE_URL}/ready" >/dev/null
curl -kfsS "${BASE_URL}/version" >/dev/null
curl -kfsS "${BASE_URL}/" >/dev/null

echo "Local production smoke checks passed for ${BASE_URL}"
