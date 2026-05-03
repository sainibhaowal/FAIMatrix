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
  --exclude '.codex' \
  --exclude '.github' \
  --exclude '.vscode' \
  --exclude '.ruff_cache' \
  --exclude '__pycache__' \
  --exclude '.cache' \
  --exclude '.pytest_cache' \
  --exclude '.env' \
  --exclude '.env.localprod' \
  --exclude '.env.localprod.example' \
  --exclude 'deploy/env*.example' \
  --exclude 'deploy/env.vpsprod' \
  --exclude 'deploy/ssl' \
  --exclude '.venv' \
  --exclude 'node_modules' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/.next' \
  --exclude 'frontend/out' \
  --exclude 'frontend/build' \
  --exclude 'frontend/playwright-report' \
  --exclude 'frontend/test-results' \
  --exclude 'frontend/tsconfig.tsbuildinfo' \
  --exclude 'frontend/tests' \
  --exclude 'frontend/e2e' \
  --exclude 'docs' \
  --exclude 'Docs' \
  --exclude 'frontend/Docs' \
  --exclude 'faim_native/Docs' \
  --exclude 'faim_native/faim-m' \
  --exclude 'faim_native/store/raw/blobs' \
  --exclude 'tests' \
  --exclude 'Runtime' \
  --exclude 'storage_prototype.html' \
  --exclude 'faim_native/full_test_log.txt' \
  --exclude 'scripts/pdf-generator' \
  --exclude 'docs/simulation_run*.txt' \
  ./ "$VPS_HOST:$VPS_PATH/"
