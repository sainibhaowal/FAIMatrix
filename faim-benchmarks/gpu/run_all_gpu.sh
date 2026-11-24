#!/usr/bin/env bash
# Production GPU Benchmark Suite:
#   1) Pure FAIM-Native GPU (FAIM_FAST_ML_EMBEDDING=false)
#   2) FAIM + Granite GPU Hybrid (FAIM_FAST_ML_EMBEDDING=true, 3 API / 3 Ingest workers + VRAM OOM guard)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

OUT_BASE="${OUT_BASE:-results/gpu}"
INGEST_WORKERS="${INGEST_WORKERS:-4}"
export FAIM_BENCH_FAIM_BATCH_SIZE="${FAIM_BENCH_FAIM_BATCH_SIZE:-100}"
REV="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"

run_beir() {
  local ds="$1" corpus_rev="$2" qrels_rev="$3" out_sub="$4" provider_id="$5" model_id="$6"
  echo "=== [GPU BEIR] $ds ($out_sub | $model_id) ==="
  FAIM_SELF_EVOLVE_ENABLED=false \
  FAIM_EMBEDDING_PROVIDER_ID="$provider_id" \
  FAIM_EMBEDDING_MODEL_ID="$model_id" \
  FAIM_EMBEDDING_MODEL_REVISION="$REV" \
  FAIM_BEIR_CORPUS_REVISION="$corpus_rev" \
  FAIM_BEIR_QUERIES_REVISION="$corpus_rev" \
  FAIM_BEIR_QRELS_REVISION="$qrels_rev" \
  faim-bench beir \
    --dataset "$ds" \
    --systems faim,bm25 \
    --ingest-workers "$INGEST_WORKERS" \
    --require-faim-beats-bm25 \
    --retain-query-traces \
    --out-dir "$OUT_BASE/$out_sub"
}

run_suite_set() {
  local mode="$1" provider_id="$2" model_id="$3"
  run_beir scifact   b3b5335604bf5ee3c4447671af975ea25143d4f5 2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029 "$mode/scifact"  "$provider_id" "$model_id"
  run_beir nfcorpus  b5026a0e96e8a7ac4f95f482a596389289d46269 a451b3b26d3ae1358f259c1a3a4dd61fcea35a65 "$mode/nfcorpus" "$provider_id" "$model_id"
  run_beir arguana   9bcf8fc0320c4e3860e25b8b85fa205fcdd7078f ae5468c6f1c198109a8af5f0d4dc58bd18b6fea7 "$mode/arguana"  "$provider_id" "$model_id"
}

MODE="${1:-all}" # native | hybrid | all

if [ "$MODE" = "native" ] || [ "$MODE" = "all" ]; then
  echo "=== Starting Pure FAIM-Native GPU Stack (6 API / 8 Ingest) ==="
  (cd "$REPO_ROOT" && FAIM_API_WORKERS=6 FAIM_INGEST_WORKERS=8 FAIM_FAST_ML_EMBEDDING=false FAIM_EMBEDDING_DEVICE=auto FAIM_MIN_CUDA_FREE_MIB=1024 FAIM_DB_IDLE_IN_TRANSACTION_TIMEOUT_MS=600000 docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d api worker-ingest worker-evolve)
  run_suite_set "native" "faim-native-gpu" "zero-ml-repr-v2-cuda-concept-maxsim"
fi

if [ "$MODE" = "hybrid" ] || [ "$MODE" = "all" ]; then
  echo "=== Starting FAIM + Granite GPU Hybrid Stack (3 API / 3 Ingest, VRAM Guard 1024 MiB) ==="
  (cd "$REPO_ROOT" && FAIM_API_WORKERS=3 FAIM_INGEST_WORKERS=3 FAIM_FAST_ML_EMBEDDING=true FAIM_EMBEDDING_DEVICE=auto FAIM_MIN_CUDA_FREE_MIB=1024 FAIM_DB_IDLE_IN_TRANSACTION_TIMEOUT_MS=600000 docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d api worker-ingest worker-evolve)
  run_suite_set "granite-hybrid" "local-gpu-hybrid" "ibm-granite/granite-embedding-97m-multilingual-r2"
  echo "=== Restoring Default Pure FAIM-Native Stack ==="
  (cd "$REPO_ROOT" && FAIM_FAST_ML_EMBEDDING=false docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d api worker-ingest worker-evolve)
fi
