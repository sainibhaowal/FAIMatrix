#!/usr/bin/env bash
# Production GPU Benchmark Suite (CUDA Pure FAIM-Native + Granite GPU Hybrid Ablation)
# Requires docker-compose.gpu.yml stack running on an NVIDIA GPU host.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

OUT_BASE="${OUT_BASE:-results/gpu}"
INGEST_WORKERS="${INGEST_WORKERS:-4}"
export FAIM_BENCH_FAIM_BATCH_SIZE="${FAIM_BENCH_FAIM_BATCH_SIZE:-50}"
export FAIM_EMBEDDING_PROVIDER_ID="${FAIM_EMBEDDING_PROVIDER_ID:-faim-native-gpu}"
export FAIM_EMBEDDING_MODEL_ID="${FAIM_EMBEDDING_MODEL_ID:-zero-ml-repr-v2-cuda-concept-maxsim}"
export FAIM_EMBEDDING_MODEL_REVISION="${FAIM_EMBEDDING_MODEL_REVISION:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"

run_beir() {
  local ds="$1" corpus_rev="$2" qrels_rev="$3" tag="$4"
  echo "=== [GPU BEIR] $ds ($tag) ==="
  FAIM_SELF_EVOLVE_ENABLED=false \
  FAIM_BEIR_CORPUS_REVISION="$corpus_rev" \
  FAIM_BEIR_QUERIES_REVISION="$corpus_rev" \
  FAIM_BEIR_QRELS_REVISION="$qrels_rev" \
  faim-bench beir \
    --dataset "$ds" \
    --systems faim,bm25 \
    --ingest-workers "$INGEST_WORKERS" \
    --require-faim-beats-bm25 \
    --retain-query-traces \
    --out-dir "$OUT_BASE/$tag"
}

run_beir scifact   b3b5335604bf5ee3c4447671af975ea25143d4f5 2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029 scifact
run_beir nfcorpus  b5026a0e96e8a7ac4f95f482a596389289d46269 a451b3b26d3ae1358f259c1a3a4dd61fcea35a65 nfcorpus
run_beir arguana   9bcf8fc0320c4e3860e25b8b85fa205fcdd7078f ae5468c6f1c198109a8af5f0d4dc58bd18b6fea7 arguana
