# FAIM benchmark evidence

## Scope

This directory documents benchmark methodology, evidence selection, and
publication criteria for FAIM-Native. It does not replace the executable
harness in [`faim-benchmarks`](../../../faim-benchmarks/README.md) or the signed
JSON and Markdown artifacts produced by that harness.

## Canonical evidence

The current canonical full-split SciFact comparison (`Publication gate: READY`) is:

- Report:
  [`ret_scifact_20261122T124757Z_df5d93fc.md`](../../../faim-benchmarks/results/gpu/scifact-v19-ready/ret_scifact_20261122T124757Z_df5d93fc.md)
- Signed data:
  [`ret_scifact_20261122T124757Z_df5d93fc.json`](../../../faim-benchmarks/results/gpu/scifact-v19-ready/ret_scifact_20261122T124757Z_df5d93fc.json)
- Harness instructions and release controls:
  [`faim-benchmarks/README.md`](../../../faim-benchmarks/README.md)

The run used the pinned BeIR SciFact corpus and test qrels, seed `42`,
`top_k=20`, 300 queries, retained per-query traces, and the explicitly
selected systems FAIM-Native and BM25. Both systems completed without ingest
errors.

## Current result and interpretation

The `scifact-v19-ready` artifact reports:

| System | nDCG@10 | Query p50 | Query p95 | Status |
| --- | ---: | ---: | ---: | --- |
| FAIM-Native | 0.6878 | 104.52 ms | 159.15 ms | completed (`READY`) |
| BM25 baseline | 0.6644 | 38.44 ms | 70.96 ms | completed (`READY`) |

These values are evidence for the stated run on a clean worktree (`fbae575`).
See [`RESULTS.md`](../../../faim-benchmarks/results/RESULTS.md) for the complete
CPU, GPU, hybrid, NFCorpus, ArguAna, and LoCoMo evidence suite.

## Publication requirements

A benchmark report may be presented as public release evidence only when all
of the following are recorded in the artifact:

1. The dataset source, immutable revisions, split, seed, query count, and
   scoring configuration.
2. The complete command and non-secret model/provider identifiers, including
   pinned model revisions.
3. The exact FAIM commit and a clean Git worktree at run time.
4. Completed health checks and zero ingest errors for every claimed system.
5. Retained per-query traces and a verified integrity hash.
6. An explicit status for every configured comparison system. Unconfigured
   systems must be reported as `skipped`, not assigned an inferred score.

Published results from other memory systems may be cited only as external
references when their dataset, protocol, model, and metric definitions are
not identical. They must not be merged into the FAIM run's system table or
described as a direct head-to-head comparison.

## Reproducibility and safety

Run the harness with a scoped benchmark API key, a dedicated tenant, pinned
dataset revisions, benchmark isolation enabled, self-evolution disabled, and
the configured ingestion/indexing services available. Keep credentials in the
ignored benchmark environment file; never commit them or include them in
reports. Preserve the signed JSON artifact beside its Markdown rendering and
do not edit either artifact after a run.
