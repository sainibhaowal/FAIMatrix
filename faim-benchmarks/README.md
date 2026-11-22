# `faim-benchmarks` — External Standalone Benchmark Harness

Black-box, reproducible benchmark suite comparing **FAIM-Native** against **BM25**, **Mem0**, **Zep**, **SuperMemory**, **Letta**, and **Full-Context LLMs** across **BEIR**, **LoCoMo**, and **LongMemEval**.

## Design Guarantees
- **Zero internal shortcuts:** Calls FAIM strictly over public HTTP (`/api/v1/ingest`, `/api/v1/memory/write`, `/api/v1/query`).
- **Fair locked splits:** Identical corpus, queries, `top_k=20`, `seed=42`, and scorer across every configured system.
- **No fabricated numbers:** Unconfigured competitors are explicitly marked `skipped` with the missing credential name.
- **Failure isolation:** An adapter outage is marked `failed` and receives no score; other systems continue to run.
- **Tamper-evident reports:** Every run writes a canonical JSON + Markdown report stamped with `integrity_sha256`.

The harness is a measurement tool, not a leaderboard publisher. A public result
must include the dataset version/source, full command, seed, model/provider
configuration, completed-system statuses, and the signed JSON artifact.

## Clean FAIM run controls

For release evidence, configure the ignored `.env` file with a real scoped
`FAIM_API_KEY` and `FAIM_TENANT_ID`, then run the API and worker with benchmark
isolation enabled. Self-evolution and domain-autonomy work stays outside the
ingest workload and remains durable for normal workers later:

```bash
FAIM_BENCHMARK_MODE=true \
FAIM_SELF_EVOLVE_ENABLED=false \
FAIM_CHUNKING_ENABLED=true \
docker compose up -d api worker

set -a; . faim-benchmarks/.env; set +a
export FAIM_BENCHMARK_MODE=true
export FAIM_BENCH_FAIM_BATCH_SIZE=20
faim-bench beir --dataset custom \
  --local-dir /path/to/pinned/scifact \
  --top-k 20 --seed 42 --retain-query-traces \
  --systems faim,bm25 --ingest-workers 1 \
  --out-dir results/public-scifact-release
```

The bounded one-worker/20-document setting is intentional for the public
upload surface: larger concurrent multipart batches can exhaust API request
workers before the durable job layer starts. It does not change the retrieval
corpus, scorer, model, Qdrant index, or 300-query evaluation protocol.

The API accepts `benchmark_mode` on JSON and multipart ingest as an explicit
side-effect isolation signal. Worker transactions rollback before a transient
retry, and Qdrant/native vector writes are batch operations; PostgreSQL remains
canonical truth. Do not publish a run while Git is dirty or while the artifact
reports ingest errors, failed health checks, or non-comparable competitors.

## Canonical completed run

The repository retains the latest canonical full run under
`results/public-scifact-full-guarded-v17/`. It evaluates the official SciFact
split (5,183 documents and 300 queries) with FAIM-Native and BM25. Both systems
completed all queries with zero ingest errors. The report records FAIM nDCG@10
`0.4184`, BM25 nDCG@10 `0.6644`, FAIM query p50 `7,195.68 ms`, and BM25 query
p50 `48.42 ms`. The report is an honest evidence artifact, but its publication
gate is `NOT READY`: the worktree was dirty and model provenance was incomplete.
The earlier v9 artifact remains available as historical evidence; it is not the
current release benchmark.

The latest completed guarded rerun is under
`results/public-scifact-full-guarded-v17/`. It completed the full pinned split
with zero ingestion errors, but it is not a production-claim result: FAIM-Native
scored nDCG@10 `0.4184` with query p50 `7,195.68 ms`, while BM25 scored
`0.6644` with query p50 `48.42 ms`. Its publication gate remains `NOT READY`
because the worktree was dirty and model provenance was incomplete.

Published Mem0, Zep, Supermemory, and Letta numbers are documented in the root
README as external, non-comparable references. They are not inserted into this
run's system table unless the same public dataset, scorer, model, and protocol
are actually executed.

## FAST retrieval strategy

The Docker production defaults make the `FAST` profile relevance-first when
Representation V2 and Phase 5 are enabled. FAST skips the graph-wide IDF scan
and broad graph expansion by default, then gives the bounded lexical shortlist
the largest fusion weight. The guarded switches are:

```text
FAIM_FAST_RELEVANCE_FIRST=true
FAIM_FAST_GRAPH_EXPANSION=false
FAIM_FAST_IDF=false
```

Enable graph expansion or IDF only for a measured ablation; they are not
assumed to improve retrieval quality. The API still updates usage, journal,
and touch events, while STRICT and BALANCED retain their existing graph and
IDF behavior. A clean benchmark must report the per-stage timings and compare
this strategy with BM25 on the identical retained split.

## Setup
```bash
cd faim-benchmarks
python -m pip install -e ".[datasets,dev]"
cp .env.example .env
```

## Run BEIR Retrieval Benchmarks
```bash
faim-bench beir --dataset scifact --top-k 20 --seed 42 --out-dir results
# Release-evidence mode: retain per-query IDs, metrics, latency, and safe diagnostics
faim-bench beir --dataset scifact --top-k 20 --seed 42 --retain-query-traces --out-dir results
# Example explicit release gates (the run is NOT READY when any gate fails)
faim-bench beir --dataset scifact --top-k 20 --seed 42 \
  --retain-query-traces --min-ndcg-at-10 0.70 --max-query-p95-ms 500 \
  --require-faim-beats-bm25 --out-dir results
# Optional bounded concurrency for a real API load test:
faim-bench beir --dataset scifact --top-k 20 --seed 42 --ingest-workers 4 --out-dir results
# Optional public memory-write path (reported separately from file ingest):
FAIM_BENCH_FAIM_WRITE_MODE=memory faim-bench beir --dataset scifact --top-k 20 --seed 42 --out-dir results
# Offline/custom BEIR folder:
faim-bench beir --dataset custom --local-dir ./data/scifact --out-dir results
```

## Run Conversational / Agent Memory Benchmarks (`LoCoMo`, `LongMemEval`)
```bash
faim-bench memory --suite locomo --data-path ./data/locomo10.json --out-dir results
faim-bench memory --suite longmemeval --data-path ./data/longmemeval_s.json --out-dir results
```

Use the datasets from their official releases: [BEIR](https://github.com/beir-cellar/beir),
[LoCoMo](https://github.com/snap-research/LoCoMo), and
[LongMemEval](https://github.com/xiaowu0162/LongMemEval). Keep downloaded datasets
outside the repository unless their license explicitly permits redistribution.

## Release checklist

```bash
pytest -q
python -m compileall -q faim_benchmarks
faim-bench beir --dataset scifact --max-queries 100 --out-dir results
```

Before publishing a report, verify that FAIM is configured with a scoped key or
bearer token, every claimed comparison system has `status=completed`, no system
has `status=failed`, the report hash is present, and the run used the intended
dataset and seed. Retrieval publication also requires retained per-query traces
and non-secret embedding provider/model/revision metadata. Missing competitor
credentials are acceptable only when the published report clearly shows them as
`skipped`.

The trace artifact contains document IDs, qrel IDs, metrics, latency, and
whitelisted adapter diagnostics. It does not contain query text, document text,
credentials, or provider response bodies. Set these non-secret variables when
running FAIM retrieval benchmarks so the signed artifact identifies the model:

```bash
export FAIM_EMBEDDING_PROVIDER_ID=local
export FAIM_EMBEDDING_MODEL_ID=ibm-granite-granite-embedding-97m-multilingual-r2
export FAIM_EMBEDDING_MODEL_REVISION=<pinned-model-revision>
```

## Run Harness Verification Tests
```bash
pytest -q
```
