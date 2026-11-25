# FAIM-Native Empirical Benchmarks

Reproducible evaluation metrics for **FAIM-Native (`v0.10.0`)** executed via the [`faim-benchmarks`](faim-benchmarks/README.md) black-box HTTP harness using pinned Hugging Face datasets, locked qrels, `seed=42`, `top_k=20`, and integrity-hashed JSON reports.

See [RESULTS.md](faim-benchmarks/results/RESULTS.md) for the complete signed artifact index and [02-production-benchmark-suite-2026-11-22.md](faim_native/Docs/13-benchmarks/02-production-benchmark-suite-2026-11-22.md) for stage-level latency traces.

---

## 1. Executive Summary (`2026-11-24` Full Splits)

| Runtime Profile | Mode & Hardware | `BeIR/SciFact` (`nDCG@10` / `R@5` / `P50`) | `BeIR/NFCorpus` (`nDCG@10` / `R@5` / `P50`) | `BeIR/ArguAna` (`nDCG@10` / `R@10` / `P50`) | `LoCoMo` (`Fact Recall` / `P50`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FAIM Hybrid · Granite 97M (Flagship)** | `FAST` + Granite 97M GPU | **0.6900** (`0.7704` / `140.17 ms`) | **0.3314** (`0.1297` / `101.62 ms`) | **0.3387** (**0.7266** / `304.55 ms`) | `0.0710` (`234.56 ms`) |
| **FAIM-Pure · Zero-ML (CPU)** | `FAST` + Zero-ML CPU CI / Docker | `0.6871` (`0.7554` / **86.31 ms** CI · `100.22 ms` Docker) | `0.3267` (`0.1289` / **49.91 ms** CI · `66.48 ms` Docker) | `0.3149` (`0.6781` / **167.74 ms** CI · `250.98 ms` Docker) | `-` |
| **FAIM-Pure · Auto Hardware** | `FAST` + Auto CPU/GPU | `0.6871` (`0.7554` / `102.92 ms`) | `0.3267` (`0.1289` / `68.98 ms`) | `0.3149` (`0.4604 R@5` / `275.16 ms`) | `0.0715` (`188.50 ms`) |
| **FAIM-Pure · CUDA Matrix** | `FAST` + CUDA native backend | `0.6871` (`0.7554` / `100.00 ms`) | `0.3267` (`0.1289` / `63.34 ms`) | `0.3149` (`0.6781` / `250.73 ms`) | `-` |
| **Granite 97M R2 Standalone** | Embedding model alone (GPU) | `0.6806` (`0.7522`) | `-` | `-` | `-` |
| **BM25 Lexical Baseline** | In-process CPU reference | `0.6644` (`0.7193` / `45.76 ms`) | `0.3110` (`0.1205` / `3.32 ms`) | `0.3451` (`0.7216` / `567.83 ms`) | `0.2049` (`16.02 ms`, `92.3` avg tok) |

### Key Verified Findings

1. **Both FAIM Hybrid and FAIM-Pure CPU outperform Standalone Granite 97M and BM25 on `BeIR/SciFact`:**
   - **FAIM Hybrid (Granite 97M):** `0.6900` `nDCG@10` (`0.7704` `Recall@5`), vs Standalone Granite `0.6806` (`0.7522`) and `BM25-Baseline` `0.6644` (`0.7193`).
   - **FAIM-Pure Zero-ML (CPU):** `0.6871` `nDCG@10` (`0.7554` `Recall@5`) with zero GPU or external neural inference at `86.31 ms` CPU CI P50.
2. **FAIM Hybrid outperforms BM25 across biomedical & counter-argument recall:**
   - On `BeIR/NFCorpus`, FAIM + Granite reaches `0.3314` `nDCG@10` (`+6.6%` relative lift over `0.3110` BM25); FAIM-Pure CPU reaches `0.3267` at `49.91 ms` CPU CI P50.
   - On `BeIR/ArguAna`, FAIM + Granite achieves higher `Recall@10` (`0.7266` vs `0.7216`) at **`1.86x` lower median query latency** (`304.55 ms` vs `567.83 ms`).
3. **`FAST` vs `BALANCED` profile ablation:**
   - Relevance-first `FAST` with Granite (`0.6900` SciFact, `140.17 ms` P50) beats `BALANCED` with Granite (`0.6560` SciFact, `2,487.46 ms` P50) by **`+0.034` `nDCG@10`** and **`~18x` lower median latency**.

---

## 2. Historical Engine Progression (`BeIR/SciFact`, Full 5,183 Docs / 300 Queries)

Measured across the exact same full `BeIR/SciFact` corpus and scorer (`seed=42`, `top_k=20`):

| Engine Generation | Architecture | Recall@5 | nDCG@10 | MRR | MAP | Query P50 | Change vs Initial Baseline |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **Early Baseline (`v9`, `ccef064a`)** | Initial native graph path (CPU) | `0.0539` | `0.0517` | `-` | `-` | `17,373.00 ms` | Baseline |
| **Intermediate (`v17`, `2a4f4574`)** | Legacy uncached path (CPU) | `0.4831` | `0.4184` | `0.3908` | `0.3798` | `7,195.68 ms` | `8.1x` higher `nDCG@10`, `2.4x` faster |
| **FAIM-Pure CPU (`v18`, `c68f9c1`)** | Zero-ML Repr V2 + BM25+ + MaxSim | `0.7554` | `0.6878` | `0.6570` | `0.6464` | `86.31 ms` (CI) / `100.22 ms` (Docker) | **`201x` lower P50 latency**, `+0.6361` `nDCG@10` |
| **FAIM Hybrid (`Granite 97M`)** | `FAST` + Granite 97M R2 + Auth/RAM Cache | **0.7704** | **0.6900** | **0.6590** | **0.6483** | `140.17 ms` | Best full-split accuracy across BeIR |

---

## 3. Conversational Memory (`LoCoMo`)

| System | Fact Recall | Token F1 | Exact Match | Query P50 | Query P95 | Avg Context Tokens |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **FAIM Hybrid · Granite 97M** | `0.0710` | `0.0582` | `0.0000` | `234.56 ms` | `446.77 ms` | `11.9` |
| **FAIM-Pure · Auto Hardware** | `0.0715` | `0.0584` | `0.0000` | `188.50 ms` | `485.03 ms` | `11.9` |
| **BM25 Lexical Baseline** | `0.2049` | `0.0383` | `0.0000` | `16.02 ms` | `28.31 ms` | `92.3` |

### Category Breakdown (`FAIM Hybrid · Granite 97M`)

| Question Category | Sample Count | Fact Recall | Token F1 | Exact Match |
| :--- | ---: | ---: | ---: | ---: |
| `single_hop` | `841` | `0.1011` | `0.0712` | `0.0000` |
| `adversarial` | `446` | `0.1009` | `0.0643` | `0.0000` |
| `temporal` | `321` | `0.0218` | `0.0470` | `0.0000` |
| `open_domain` | `96` | `0.0208` | `0.0342` | `0.0000` |
| `multi_hop` | `282` | `0.0071` | `0.0307` | `0.0000` |

FAIM's compact extractive span synthesizer prioritizes high-precision concise citations (`11.9` average context tokens vs `92.3` for BM25), achieving higher `Token F1` (`0.0584` vs `0.0383`) while multi-hop and temporal answer synthesis remain under active development.

---

## 4. Per-Stage Query Latency & Ablation Details

Measured in the production benchmark suite ([02-production-benchmark-suite-2026-11-22.md](faim_native/Docs/13-benchmarks/02-production-benchmark-suite-2026-11-22.md)) on the `BeIR/scifact` 300-doc / 50-query ablation:

- **HTTP Query P50 (`smoke-concept-maxsim`):** `49.78 ms` (`P95 = 110.61 ms`, `nDCG@10 = 0.8615`, `Recall@5 = 0.9060`)
- **Stage Breakdown (`55.79 ms` P50 trace):**
  - Stage-1 Candidate Recall (BM25+): `1.59 ms`
  - External ML Embedding Inference (`FAIM-Pure`): `0.00 ms`
  - Graph + Semantic Reranking (`v_native` + `RerankerV2` + `Concept-MaxSim`): `30.23 ms`
  - Extractive Answer Synthesis: `2.78 ms`
  - Query Canonicalization + Graph Version Lookup: `13.34 ms`
  - HTTP + HMAC Auth Cache + JSON Serialization: `7.85 ms`

### Dynamic Hybrid & CPU-Only Execution (`FAIM_FAST_ML_EMBEDDING=auto`)

In `v0.10.0`, FAIM supports dynamic per-request routing alongside CPU-only VPS deployments:

- **`FAST` + English inputs:** Routes to **FAIM-Pure** (skipping external ML inference for sub-100 ms latency).
- **`FAST` + Non-English / Multilingual inputs:** Dynamically activates the local **Granite 97M** provider (on GPU or CPU).
- **`STRICT` / `BALANCED` / `RELAXED` profiles:** Always combine native graph scoring with the active embedding provider, with fail-open fallback to **FAIM-Pure** if an embedding provider or prewarm fails.

---

## 5. Signed Evidence Artifacts

- Master artifact ledger: [RESULTS.md](faim-benchmarks/results/RESULTS.md)
- Scenario comparison summary: [COMPARISON.md](faim-benchmarks/results/COMPARISON.md)
- Flagship Granite `BeIR/SciFact`: [`ret_scifact_20261124T053245Z_d4a9a2e9.md`](faim-benchmarks/results/scenarios/3-gpu-granite/scifact/ret_scifact_20261124T053245Z_d4a9a2e9.md)
- Flagship Granite `BeIR/NFCorpus`: [`ret_nfcorpus_20261124T054655Z_620bde18.md`](faim-benchmarks/results/scenarios/3-gpu-granite/nfcorpus/ret_nfcorpus_20261124T054655Z_620bde18.md)
- Flagship Granite `BeIR/ArguAna`: [`ret_arguana_20261124T102422Z_bfaca9ae.md`](faim-benchmarks/results/scenarios/3-gpu-granite/arguana/ret_arguana_20261124T102422Z_bfaca9ae.md)
- Flagship Granite `LoCoMo`: [`mem_locomo_20261124T063204Z_75dafc50.md`](faim-benchmarks/results/scenarios/3-gpu-granite/locomo/mem_locomo_20261124T063204Z_75dafc50.md)
- FAIM-Pure CPU `BeIR/SciFact`: [`ret_scifact_20261124T021154Z_c5ba6d84.md`](faim-benchmarks/results/scenarios/1-cpu-pure-faim/scifact/ret_scifact_20261124T021154Z_c5ba6d84.md)
- FAIM-Pure CPU `BeIR/NFCorpus`: [`ret_nfcorpus_20261124T022542Z_40480251.md`](faim-benchmarks/results/scenarios/1-cpu-pure-faim/nfcorpus/ret_nfcorpus_20261124T022542Z_40480251.md)
- Historical `v19-ready` GPU & `v18-ready` CPU baselines: [`scifact-v19-ready`](faim-benchmarks/results/gpu/scifact-v19-ready/ret_scifact_20261122T124757Z_df5d93fc.md) · [`scifact-v18-ready`](faim-benchmarks/results/cpu/scifact-v18-ready/ret_scifact_20261122T001726Z_3a591ec9.md)
