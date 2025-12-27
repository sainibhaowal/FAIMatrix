#!/usr/bin/env bash
set -euo pipefail

# Go to repo root
cd "$(dirname "$0")/.."

# Activate venv
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

OUT_DIR="Runtime/Benchmarks"
mkdir -p "$OUT_DIR"

GRAPH="RAVIN_MAIN"
K=8
RUNS=3  # how many repeats per workload

run_workload() {
  local NAME="$1"
  local QFILE="$2"
  local QAFILE="$3"

  for RUN in $(seq 1 "$RUNS"); do
    local TS
    TS=$(date -u +"%Y%m%dT%H%M%SZ")

    echo "=== FAIM :: $NAME run $RUN ==="
    python scripts/benchmarks.py \
      --graph-id "$GRAPH" \
      --queries "$QFILE" \
      --qa-file "$QAFILE" \
      --k "$K" \
      --output "$OUT_DIR/faim_${NAME}_run${RUN}_${TS}.json"

    echo "=== RAG baseline :: $NAME run $RUN ==="
    python scripts/baseline_rag_benchmarks.py \
      --queries "$QFILE" \
      --qa "$QAFILE" \
      --workload "$NAME" \
      --k "$K" \
      --out "$OUT_DIR/rag_${NAME}_run${RUN}_${TS}.json"
  done
}

run_workload "longchat" "Data/Benchmarks/longchat_queries.txt" "Data/Benchmarks/longchat_qa.txt"
run_workload "contradictions" "Data/Benchmarks/contradiction_queries.txt" "Data/Benchmarks/contradiction_qa.txt"
run_workload "multiproject" "Data/Benchmarks/multiproject_queries.txt" "Data/Benchmarks/multiproject_qa.txt"
