#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VPS_HOST="${VPS_HOST:-root@144.91.118.196}"
VPS_PATH="${VPS_PATH:-/opt/faim/FAIM}"

cd "$PROJECT_ROOT"

ssh "$VPS_HOST" "mkdir -p '$VPS_PATH'"

rsync -az --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '.env.localprod' \
  --exclude '.env.localprod.example' \
  --exclude 'deploy/env.vpsprod' \
  --exclude '.venv' \
  --exclude 'node_modules' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/.next' \
  --exclude 'frontend/out' \
  --exclude 'frontend/build' \
  --exclude 'frontend/playwright-report' \
  --exclude 'frontend/test-results' \
  --exclude 'frontend/tsconfig.tsbuildinfo' \
  --exclude 'docs' \
  --exclude 'frontend/Docs' \
  --exclude 'faim_native/Docs' \
  --exclude 'tests' \
  --exclude 'frontend/tests' \
  --exclude 'frontend/e2e' \
  --exclude 'Runtime' \
  --exclude 'faim_native/full_test_log.txt' \
  --exclude 'docs/simulation_run*.txt' \
  ./ "$VPS_HOST:$VPS_PATH/"
