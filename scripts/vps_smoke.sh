#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://faimatrix.com}"

check_2xx() {
  local path="$1"
  local code
  code="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 5 --max-time 30 "${BASE_URL}${path}")"
  if [[ ! "$code" =~ ^2[0-9][0-9]$ ]]; then
    echo "Smoke check failed: ${BASE_URL}${path} returned HTTP ${code}" >&2
    return 1
  fi
}

check_2xx /health
check_2xx /ready
check_2xx /version
check_2xx /

echo "VPS smoke checks passed for ${BASE_URL}"
