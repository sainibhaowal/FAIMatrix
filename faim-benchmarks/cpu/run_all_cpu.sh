#!/usr/bin/env bash
# Production CPU-Only Benchmark Suite (Zero-ML FAIM-Native vs BM25-Baseline)
# Runs BEIR (scifact, nfcorpus, arguana, fiqa, trec-covid) and Memory (locomo, longmemeval, optional beam/tm).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

OUT_BASE="${OUT_BASE:-results/cpu}"
INGEST_WORKERS="${INGEST_WORKERS:-4}"
export FAIM_BENCH_FAIM_BATCH_SIZE="${FAIM_BENCH_FAIM_BATCH_SIZE:-50}"
export FAIM_EMBEDDING_PROVIDER_ID="${FAIM_EMBEDDING_PROVIDER_ID:-faim-native-cpu}"
export FAIM_EMBEDDING_MODEL_ID="${FAIM_EMBEDDING_MODEL_ID:-zero-ml-repr-v2-cpu}"
export FAIM_EMBEDDING_MODEL_REVISION="${FAIM_EMBEDDING_MODEL_REVISION:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"

run_beir() {
  local ds="$1" corpus_rev="$2" qrels_rev="$3"
  echo "=== [CPU BEIR] $ds ==="
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
    --out-dir "$OUT_BASE/$ds"
}

run_beir scifact   b3b5335604bf5ee3c4447671af975ea25143d4f5 2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029
run_beir nfcorpus  b5026a0e96e8a7ac4f95f482a596389289d46269 a451b3b26d3ae1358f259c1a3a4dd61fcea35a65
run_beir arguana   9bcf8fc0320c4e3860e25b8b85fa205fcdd7078f ae5468c6f1c198109a8af5f0d4dc58bd18b6fea7
run_beir fiqa      979c07a7cb5ccc6ca009792241fa1250b98055dd 252958f2d646e22cab6d0c72dd3f0d5de6d0655a
run_beir trec-covid 7e16fde3016c639c7f856e803f4bab92645562c4 532ac68ee6756ac22c9346eebf65bd3c6a042e10

DATA_DIR="${FAIM_BENCH_DATA_DIR:-$HOME/.faim/bench_datasets}"
if [ -f "$DATA_DIR/locomo10.json" ]; then
  echo "=== [CPU MEMORY] locomo ==="
  FAIM_SELF_EVOLVE_ENABLED=true faim-bench memory --suite locomo --data-path "$DATA_DIR/locomo10.json" --systems faim,bm25 --out-dir "$OUT_BASE/locomo"
fi
if [ -f "$DATA_DIR/longmemeval_s_cleaned.json" ]; then
  echo "=== [CPU MEMORY] longmemeval ==="
  FAIM_SELF_EVOLVE_ENABLED=true faim-bench memory --suite longmemeval --data-path "$DATA_DIR/longmemeval_s_cleaned.json" --systems faim,bm25 --out-dir "$OUT_BASE/longmemeval"
fi
if [ -n "${BEAM_DATA_PATH:-}" ] && [ -f "$BEAM_DATA_PATH" ]; then
  echo "=== [CPU MEMORY] beam ==="
  FAIM_SELF_EVOLVE_ENABLED=true faim-bench memory --suite beam --data-path "$BEAM_DATA_PATH" --systems faim,bm25 --out-dir "$OUT_BASE/beam"
fi
if [ -n "${TM_DATA_PATH:-}" ] && [ -f "$TM_DATA_PATH" ]; then
  echo "=== [CPU MEMORY] tm ==="
  FAIM_SELF_EVOLVE_ENABLED=true faim-bench memory --suite tm --data-path "$TM_DATA_PATH" --systems faim,bm25 --out-dir "$OUT_BASE/tm"
fi
