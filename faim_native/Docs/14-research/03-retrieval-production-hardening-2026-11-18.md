# FAIM retrieval and benchmark hardening: 2026-11-18

## Purpose

This note records the production-safety work completed for benchmark isolation
and retrieval acceleration. It is an implementation record, not a claim that
FAIM currently beats published retrieval systems.

## Implemented

- Benchmark upload jobs carry `benchmark_mode=true`.
- Benchmark-mode workers do not claim `evolve` or `domain_autonomy` jobs and do
  not run the periodic self-evolution scan. Existing autonomous jobs remain
  durable and pending for a normal worker after the benchmark window.
- Storage-upload success does not enqueue domain-autonomy work for a benchmark
  payload.
- Worker failures always rollback the SQLAlchemy transaction before recording a
  terminal state. Transient connection/transaction failures are requeued once
  by default (`FAIM_JOB_MAX_RETRIES=1`); non-transient failures are not blindly
  retried.
- Storage-upload batches commit each file's terminal state before processing
  the next file. This releases graph/version locks between files and prevents
  concurrent benchmark producers from amplifying one large transaction; the
  aggregate job remains durable and is finalized after the batch.
- Native and semantic Qdrant writes use one batch upsert per ingest operation.
  PostgreSQL remains canonical truth; Qdrant is rebuildable acceleration.
- Semantic query recall prefers the dimension-specific Qdrant ANN collection
  and falls back to the bounded SQL scan when Qdrant is unavailable or a graph
  has not been backfilled.
- Retrieval-oriented chunking is opt-in with
  `FAIM_CHUNKING_ENABLED=true`. It preserves source offsets and leaves headings,
  tables, code, and image stubs atomic. Default false preserves legacy packet
  hashes and ingestion behavior.
- Large-graph query diagnostics no longer perform synchronous full node/edge
  materialization when the cache is missing. The query path returns bounded
  metrics and leaves full diagnostics to evolution/maintenance work, avoiding
  PostgreSQL idle-in-transaction timeouts while ANN/model work is running.
- The HTTP benchmark adapter skips its catalog-wide raw-ID scan when batch
  upload responses already supplied every mapping, preventing a first-query
  worker timeout on large benchmark graphs.
- Phase-5 large-graph recall builds the sparse lexical shortlist without
  materializing every SQL dense vector. Persistent Qdrant semantic ANN is the
  dense path; the in-process VP-tree remains available to compatibility
  callers and small graphs.

## Runtime controls

```dotenv
FAIM_BENCHMARK_MODE=true
FAIM_SELF_EVOLVE_ENABLED=false
FAIM_CHUNKING_ENABLED=true
FAIM_CHUNK_MAX_CHARS=1200
FAIM_CHUNK_OVERLAP=120
FAIM_PHASE5_DENSE_SQL_MAX_NODES=2000
FAIM_JOB_MAX_RETRIES=1
# Keep the public upload surface bounded during a full local benchmark.
FAIM_BENCH_FAIM_BATCH_SIZE=20
```

These flags should be applied to the API and worker for a benchmark window.
Do not commit live API keys or tenant identifiers; use the ignored benchmark
`.env` file or a secret manager.

## Verification evidence

The targeted local gate executed on 2026-11-18 with:

```text
pytest -o addopts='' -q \
  tests/unit/test_retrieval_acceleration.py \
  tests/unit/test_index_faim_native.py \
  tests/unit/test_job_store_claim_kind_filter.py \
  tests/acceptance/test_AT_O1_ingest_chunk_free.py \
  tests/acceptance/test_AT_Q2_no_chunking_no_ml.py \
  tests/acceptance/test_AT_S10_job_durability.py
```

Result: **30 passed**, with one existing SQLAlchemy deprecation warning.
The test shell does not have `qdrant-client` installed; the dependency is
declared in `requirements.txt` and the Docker runtime installs it. The ANN
batch contract test uses a fake client, while Docker validation must still
exercise the real Qdrant service.

The full guarded run `public-scifact-full-guarded-v10` ingested all `5,183`
documents with zero ingestion errors and evaluated all `300` BM25 queries.
FAIM did not produce a score because the API worker was terminated during the
first query by the pre-fix large-graph transaction/diagnostics path. The
artifact is retained as a failure record, not a score claim:

`faim-benchmarks/results/public-scifact-full-guarded-v10/ret_custom_20261118T140441Z_6f051251.json`

After the fix, a direct authenticated query against that graph completed with
HTTP 200 in `60,468 ms` while the legacy Phase-5 SQL-built index was enabled.
With Phase-5 disabled and the Qdrant/native index path selected, the same
query completed in `15,583 ms` and returned 20 results. This is diagnostic
evidence, not a benchmark result; the complete clean benchmark must be rerun
with the selected configuration.

The subsequent `public-scifact-full-guarded-v12` run verified the ingestion
isolation change at full scale: `5,183/5,183` documents succeeded with zero
ingestion errors. Its FAIM query phase still failed on the first query because
the legacy Phase-5 dense rebuild loaded all SQL vectors and hit PostgreSQL's
idle-in-transaction timeout. BM25 completed all `300` queries
(nDCG@10 `0.6644`, query p50 `46.71 ms`, query p95 `91.90 ms`). This artifact
is retained as a failure record:

`faim-benchmarks/results/public-scifact-full-guarded-v12/ret_custom_20261118T174301Z_caef50c8.json`

The follow-up fix removes that dense SQL materialization from the Phase-5
request path. A direct authenticated query on the same graph then returned
HTTP 200 with 20 results in `34.16 s`; this is a smoke check only and is not a
publication score.

An attempted four-worker, 50-document batch rerun also exposed an operational
limit: concurrent multipart uploads exhausted the API request workers and
caused gunicorn timeouts before a report could be written. That run is not a
result. The release command is therefore bounded to one ingest worker and
20-document batches while the API keeps the same real embedding, persistence,
and Qdrant paths. This protects measurement validity from request overload;
retrieval scoring remains the full 5,183-document/300-query protocol.

The completed `public-scifact-full-guarded-v16` run exposed a separate staging
race: the upload route created a `pending` worker job before it had committed
the complete file list. A worker could claim that partial payload, finish with
zero processed files, and leave those files at `uploaded`. The artifact is
retained as a failure record, not a score claim:

`faim-benchmarks/results/public-scifact-full-guarded-v16/ret_scifact_20261119T160027Z_0bbde539.json`

The fix changes workerized upload jobs to `staging -> pending -> running`.
Only the fully staged `pending` state is claimable; ordinary jobs retain the
existing `pending` default. The focused regression gate passed 16 tests, and
the full suite passed 1,023 tests with one skip. The guarded v17 rerun then
completed against the same pinned dataset: `5,183/5,183` documents and all
`300` queries completed with zero ingestion errors for both systems. The signed
artifact is:

`faim-benchmarks/results/public-scifact-full-guarded-v17/ret_scifact_20261120T003156Z_2a4f4574.json`

Measured results were FAIM-Native nDCG@10 `0.4184`, MRR `0.3908`, query p50
`7,195.68 ms`, p95 `12,320.01 ms`; BM25 nDCG@10 `0.6644`, MRR `0.6366`, query
p50 `48.42 ms`, p95 `89.24 ms`. This proves the guarded pipeline runs end to
end, but the artifact remains `NOT READY` because the worktree was dirty and
non-secret embedding provider/model/revision provenance was missing. FAIM also
remains behind BM25 on this SciFact protocol for quality and latency.

## Benchmark publication gate

The existing full SciFact artifact remains the honest baseline until a clean
rerun is completed:

- FAIM nDCG@10: `0.0517`
- BM25 nDCG@10: `0.6644`
- FAIM query p50: `17,373 ms`
- BM25 query p50: `35 ms`

Those numbers are not competitive and are not a production-quality claim.
The next valid result must use pinned SciFact data, `X-API-Key` plus
`X-Tenant-Id` only, benchmark mode enabled, self-evolution disabled, real
Qdrant, a clean Git state, and an exported manifest containing configuration,
dataset hash, commit, health checks, errors, and latency distributions.
Published figures from other memory systems must be labelled as external
references and must not be presented as directly comparable unless dataset,
cutoff, embedding model, hardware, candidate depth, and metric protocol match.

## Known limitations

The implementation is now safer and has the required ANN/chunking foundations,
but it is not yet evidence for “best in market” performance. A full clean
benchmark and repeated-run variance report are still required. Competitor API
credentials/endpoints are not required for the local BM25 reference, but are
required for any live third-party rerun.
