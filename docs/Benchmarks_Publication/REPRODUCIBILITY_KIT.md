# Reproducibility Kit

## Required Environment
- API running with /api/v1 routes
- Python dependencies from requirements.txt
- sentence-transformers installed for MTEB-like baseline (optional; run is skipped if missing)

## Commands
1. Run publication suite:
   POST /api/v1/faim-bench/{graph_id}/publication/run
   body:
   {
       "dataset_names": ["scifact", "nq", "hotpotqa", "fever", "msmarco"],
     "max_corpus": null,
     "max_queries": null
   }

2. Fetch latest run:
   GET /api/v1/faim-bench/{graph_id}/publication/latest

3. Fetch leaderboard only:
   GET /api/v1/faim-bench/{graph_id}/publication/leaderboard

4. Fetch benchmark spec:
   GET /api/v1/faim-bench/{graph_id}/publication/spec

5. Fetch repro payload:
   GET /api/v1/faim-bench/{graph_id}/publication/repro

## Output Schema (Core)
- run_id: string
- datasets: string[]
- faim_track_a.metrics: object
- baselines.<name>[]: dataset metrics + CI
- track_e: agent workflow results + system comparison rows
- track_f: real-world task results + system comparison rows
- mteb: status + datasets
- workflow_checks: memory continuity + api key lifecycle
- system_comparison[]: FAIM, BM25, dense, summary, Mem0, Zep, SuperMemory, full-context
- leaderboard[]: system + Recall@5/nDCG@10/MRR/MAP/task completion
- results_report: methodology + ablations + failure cases
- reproducibility_kit: commands + schema summary
- benchmark_spec: run rules + hyperparameters
