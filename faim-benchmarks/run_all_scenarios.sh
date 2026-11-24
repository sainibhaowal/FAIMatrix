#!/usr/bin/env bash
# Run any or all 6 FAIM benchmark scenarios (fiqa, trec-covid, longmemeval stay disabled)
# and aggregate all signed reports into faim-benchmarks/results/RESULTS.md.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$ROOT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

SCENARIOS="${1:-all}" # comma-separated or "all"
SYSTEMS="${SYSTEMS:-faim}"
DEMAND="${DEMAND:-max}"
export FAIM_BENCH_FAIM_BATCH_SIZE="${FAIM_BENCH_FAIM_BATCH_SIZE:-100}"
export FAIM_BENCH_FAIM_JOB_POLL_SECONDS="${FAIM_BENCH_FAIM_JOB_POLL_SECONDS:-0.25}"
REV="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo local)"

run_beir_set() {
  local scenario="$1" provider_id="$2" model_id="$3" profile="$4" workers="$5"
  local gate_args=()
  if [[ ",$SYSTEMS," == *",bm25,"* ]]; then
    gate_args+=(--require-faim-beats-bm25)
  fi
  for spec in \
    "scifact b3b5335604bf5ee3c4447671af975ea25143d4f5 2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029" \
    "nfcorpus b5026a0e96e8a7ac4f95f482a596389289d46269 a451b3b26d3ae1358f259c1a3a4dd61fcea35a65" \
    "arguana 9bcf8fc0320c4e3860e25b8b85fa205fcdd7078f ae5468c6f1c198109a8af5f0d4dc58bd18b6fea7"; do
    read -r ds crev qrev <<< "$spec"
    echo "=== [$scenario] BEIR $ds (systems=$SYSTEMS, profile=$profile, workers=$workers) ==="
    FAIM_PROFILE="$profile" \
    FAIM_SELF_EVOLVE_ENABLED=false \
    FAIM_EMBEDDING_PROVIDER_ID="$provider_id" \
    FAIM_EMBEDDING_MODEL_ID="$model_id" \
    FAIM_EMBEDDING_MODEL_REVISION="$REV" \
    FAIM_BEIR_CORPUS_REVISION="$crev" \
    FAIM_BEIR_QUERIES_REVISION="$crev" \
    FAIM_BEIR_QRELS_REVISION="$qrev" \
    faim-bench beir \
      --dataset "$ds" \
      --systems "$SYSTEMS" \
      --ingest-workers "$workers" \
      "${gate_args[@]}" \
      --retain-query-traces \
      --out-dir "results/scenarios/$scenario/$ds"
  done

  local data_dir="${FAIM_BENCH_DATA_DIR:-$HOME/.faim/bench_datasets}"
  if [ -f "$data_dir/locomo10.json" ]; then
    echo "=== [$scenario] Memory locomo (workers=$workers) ==="
    FAIM_PROFILE="$profile" \
    FAIM_SELF_EVOLVE_ENABLED=true \
    FAIM_EMBEDDING_PROVIDER_ID="$provider_id" \
    FAIM_EMBEDDING_MODEL_ID="$model_id" \
    FAIM_EMBEDDING_MODEL_REVISION="$REV" \
    faim-bench memory \
      --suite locomo \
      --data-path "$data_dir/locomo10.json" \
      --systems "$SYSTEMS" \
      --ingest-workers "$workers" \
      --out-dir "results/scenarios/$scenario/locomo"
  fi
}

autoscale_and_up() {
  local mode="$1" fast_ml="$2" emb_dev="$3" gpu_be="$4" compose_files="$5"
  eval "$(PYTHONPATH="$REPO_ROOT" python3 -m faim_native.runtime.hardware_autoscaler \
    --mode "$mode" --demand "$DEMAND" --vram-budget-mib 5632 --max-workers 18 --format env)"
  echo "=== Starting $mode stack (API=$FAIM_API_WORKERS Ingest=$FAIM_INGEST_WORKERS ML=$fast_ml Dev=$emb_dev GPUBackend=$gpu_be) ==="
  (cd "$REPO_ROOT" && \
    FAIM_API_WORKERS="$FAIM_API_WORKERS" \
    FAIM_INGEST_WORKERS="$FAIM_INGEST_WORKERS" \
    FAIM_FAST_ML_EMBEDDING="$fast_ml" \
    FAIM_EMBEDDING_DEVICE="$emb_dev" \
    FAIM_USE_GPU_BACKEND="$gpu_be" \
    FAIM_MIN_CUDA_FREE_MIB="$FAIM_MIN_CUDA_FREE_MIB" \
    FAIM_EMBEDDING_BATCH_SIZE="$FAIM_EMBEDDING_BATCH_SIZE" \
    FAIM_DB_IDLE_IN_TRANSACTION_TIMEOUT_MS=600000 \
    docker compose $compose_files up -d api worker-ingest worker-evolve)
  BENCH_WORKERS="$INGEST_WORKERS"
}

should_run() {
  [ "$SCENARIOS" = "all" ] || [[ ",$SCENARIOS," == *",$1,"* ]]
}

if should_run "1-cpu-pure-faim"; then
  autoscale_and_up "native" "false" "cpu" "false" "-f docker-compose.yml"
  run_beir_set "1-cpu-pure-faim" "faim-native-cpu" "zero-ml-repr-v2-cpu" "fast" "$BENCH_WORKERS"
fi

if should_run "2-gpu-pure-faim"; then
  autoscale_and_up "native" "false" "cuda" "cuda" "-f docker-compose.yml -f docker-compose.gpu.yml"
  run_beir_set "2-gpu-pure-faim" "faim-native-gpu" "zero-ml-repr-v2-cuda" "fast" "$BENCH_WORKERS"
fi

if should_run "3-gpu-granite"; then
  autoscale_and_up "hybrid" "true" "cuda" "cuda" "-f docker-compose.yml -f docker-compose.gpu.yml"
  run_beir_set "3-gpu-granite" "local-gpu-granite" "ibm-granite/granite-embedding-97m-multilingual-r2" "fast" "$BENCH_WORKERS"
fi

if should_run "4-hybrid-hw-pure-faim"; then
  autoscale_and_up "native" "false" "auto" "auto" "-f docker-compose.yml -f docker-compose.gpu.yml"
  run_beir_set "4-hybrid-hw-pure-faim" "faim-hybrid-hw-native" "zero-ml-repr-v2-auto" "fast" "$BENCH_WORKERS"
fi

if should_run "5-hybrid-faim-plus-embedding"; then
  autoscale_and_up "hybrid" "true" "auto" "auto" "-f docker-compose.yml -f docker-compose.gpu.yml"
  run_beir_set "5-hybrid-faim-plus-embedding" "faim-plus-embedding" "ibm-granite/granite-embedding-97m-multilingual-r2" "balanced" "$BENCH_WORKERS"
fi

if should_run "6-hybrid-ml-granite"; then
  autoscale_and_up "hybrid" "true" "auto" "auto" "-f docker-compose.yml -f docker-compose.gpu.yml"
  run_beir_set "6-hybrid-ml-granite" "local-gpu-hybrid" "ibm-granite/granite-embedding-97m-multilingual-r2" "fast" "$BENCH_WORKERS"
fi

python3 "$ROOT_DIR/scripts/collect_results.py"
