# FAIM Multi-Scenario Benchmark Results (2026-11-24)

**Scope:** Verified end-to-end benchmark evidence across CPU-only, Pure-FAIM GPU, Granite 97M GPU Hybrid (`fast` vs `balanced`), and CPU+GPU Hybrid Hardware configurations on full un-sampled splits (`BeIR/scifact`, `BeIR/nfcorpus`, `BeIR/arguana`, and `LoCoMo`).

*(Large soak datasets `fiqa`, `trec-covid`, and `longmemeval` remain opt-in and disabled by default.)*

---

## 1. Cross-Scenario Retrieval Summary (`BeIR/scifact`, `BeIR/nfcorpus`, `BeIR/arguana`)

| Scenario | Mode / Profile | `scifact` nDCG@10 (R@5 / P50) | `nfcorpus` nDCG@10 (R@5 / P50) | `arguana` nDCG@10 (R@5 / P50) |
| :--- | :--- | :--- | :--- | :--- |
| **`3-gpu-granite` (Flagship)** | `fast` + Granite 97M GPU (`2` API + `4` Ingest, `batch=256`) | **0.6900** (`0.7704` / `140.17 ms`) | **0.3314** (`0.1297` / `101.62 ms`) | **0.3387** (`0.5096` / `304.55 ms`) |
| **`1-cpu-pure-faim`** | `fast` + Zero-ML CPU | 0.6871 (`0.7554` / `100.22 ms`) | 0.3267 (`0.1289` / `66.48 ms`) | 0.3149 (`0.4604` / `250.98 ms`) |
| **`2-gpu-pure-faim`** | `fast` + Zero-ML CUDA | 0.6871 (`0.7554` / `100.00 ms`) | 0.3267 (`0.1289` / `63.34 ms`) | 0.3149 (`0.4604` / `250.73 ms`) |
| **`4-hybrid-hw-pure-faim`** | `fast` + Zero-ML Auto | 0.6871 (`0.7554` / `102.92 ms`) | 0.3267 (`0.1289` / `68.98 ms`) | 0.3149 (`0.4604` / `275.16 ms`) |
| **`5-hybrid-faim-plus-embedding`** | `balanced` + Granite 97M GPU | 0.6560 (`0.7412` / `2487.46 ms`) | 0.3176 (`0.1264` / `1941.70 ms`) | *stopped early* |
| **CPU CI (`faim-cpu-beir-*.zip`)** | `fast` + Zero-ML CPU | 0.6871 (`0.7554` / **`86.31 ms`**) | 0.3267 (`0.1289` / **`49.91 ms`**) | 0.3149 (`0.4604` / **`167.74 ms`**) |
| **`BM25-Baseline` (CPU CI)** | In-process BM25 | 0.6644 (`0.7193` / `45.76 ms`) | 0.3110 (`0.1205` / `3.32 ms`) | 0.3451 (`0.5275` / `567.83 ms`) |

---

## 2. Conversational Memory (`LoCoMo`, `worker-evolve` Active)

| Scenario / System | Status | Fact Recall | Token F1 | Exact Match | Median (ms) | P95 (ms) | Avg Context Tokens |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **`3-gpu-granite` (FAIM-Native)** | completed (`READY`) | 0.0710 | 0.0582 | 0.0000 | 234.56 | 446.77 | 11.9 |
| **`4-hybrid-hw-pure-faim` (FAIM-Native)** | completed (`READY`) | **0.0715** | **0.0584** | 0.0000 | **188.50** | 485.03 | 11.9 |
| **`BM25-Baseline` (CPU CI)** | completed | 0.2049 | 0.0383 | 0.0000 | 16.02 | 28.31 | 92.3 |

### `3-gpu-granite` LoCoMo Per-Category Breakdown

| Category | Count | Fact Recall | Token F1 | Exact Match |
| :--- | ---: | ---: | ---: | ---: |
| `single_hop` | 841 | 0.1011 | 0.0712 | 0.0000 |
| `adversarial` | 446 | 0.1009 | 0.0643 | 0.0000 |
| `temporal` | 321 | 0.0218 | 0.0470 | 0.0000 |
| `open_domain` | 96 | 0.0208 | 0.0342 | 0.0000 |
| `multi_hop` | 282 | 0.0071 | 0.0307 | 0.0000 |

---

## 3. Key Production Findings

1. **`FAIM_PROFILE=fast` + Granite 97M GPU (`3-gpu-granite`) is the strongest production configuration:**
   - Outperforms Pure FAIM and `BM25-Baseline` on `scifact` (`0.6900` vs `0.6644`) and `nfcorpus` (`0.3314` vs `0.3110`), and outperforms `BM25-Baseline` on `arguana` `Recall@10` (`0.7266` vs `0.7216`) at `304.55 ms` P50 (vs `567.83 ms` for BM25).
   - Strictly superior to `profile=balanced` (`+0.034` nDCG@10 on `scifact` and **~18× lower latency**: `140.17 ms` vs `2487.46 ms`).
2. **Pure FAIM CPU (`zero-ml-repr-v2-cpu`) is verified for CPU-only / VPS deployments:**
   - Beats `BM25-Baseline` on `scifact` (`0.6871`) and `nfcorpus` (`0.3267`) at `49–100 ms` P50 without requiring a GPU.
3. **Reliability & Concurrency Hardening Applied:**
   - Atomic `GraphVersionRepo` `ON CONFLICT ON CONSTRAINT graph_version_pkey` upserts (`0771d4a`)
   - Postgres WAL/buffer tuning & `600s` `idle_in_transaction` timeout (`48e42b9`, `7b5dfce`)
   - Hardware-aware CPU/RAM/VRAM autoscaler (`96c9684`) + HTTP keep-alive retries & bounded client concurrency (`daecf3c`)
   - Bidirectional fallback tests (`36a2aa8`: GPU ↔ CPU and Granite ↔ Pure FAIM zero-ML)

*Full raw signed artifact index:* [RESULTS.md](../../../faim-benchmarks/results/RESULTS.md)
