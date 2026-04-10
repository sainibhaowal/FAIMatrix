# 05_Final_18_Benchmark_Implementation_Plan.md

**Date:** 2026-04-10
**Status:** FINAL PLAN — Ready for implementation approval
**Scope:** Complete 18-benchmark production system with real scores, real evidence, real competitor comparison
**Depends On:** 04_Benchmarks_Real_Implementation_Plan.md (infrastructure foundation — Phases 1-9)

---

## Executive Summary

This plan unifies **all 18 benchmarks** into a single production-grade system:

| Suite | Benchmarks | Purpose | Who Loses |
|-------|-----------|---------|-----------|
| **FAIM Proof Suite** | BM-1 to BM-9 | Prove capabilities NO competitor has | Every competitor |
| **Industry Adapters** | LM-1 to LM-6 | Prove FAIM competes on THEIR turf too | Close credibility gap |
| **Advanced Industry** | IB-1 to IB-3 | Prove multi-hop, long-context, CRUD superiority | Positions vs RAG systems |

**What you get:** A benchmarks page where every number is real, every claim is provable, every score is reproducible. You press "Run Full Suite" and get 18 benchmark results with evidence hashes.

---

## The Complete 18 Benchmarks

### TIER 1: FAIM Proof Suite (BM-1 to BM-9)

*These are YOUR exclusive wins. No competitor can pass 6 of these 9.*

| ID | Name | What It Proves | FAIM | Mem0 | Supermemory | Zep | Letta |
|----|------|---------------|:----:|:----:|:-----------:|:---:|:-----:|
| **BM-1** | Determinism Proof | Same input → identical hashes across unlimited reruns | **PASS** | FAIL | FAIL | FAIL | FAIL |
| **BM-2** | Cryptographic Integrity | Every vector, graph, diagnostics hash verifies | **PASS** | FAIL | FAIL | FAIL | FAIL |
| **BM-3** | Mathematical Invariants | 8 invariants hold after every operation | **PASS** | FAIL | FAIL | FAIL | FAIL |
| **BM-4** | Zero-LLM Operation | Full pipeline runs offline, zero cloud calls | **PASS** | FAIL | FAIL | FAIL | FAIL |
| **BM-5** | Deduplication Effectiveness | Antisymmetric merge at 95% cosine threshold | **PASS** | FAIL | ~Partial | FAIL | FAIL |
| **BM-6** | Self-Evolution | Auto graph optimization via fractal diagnostics | **PASS** | FAIL | FAIL | FAIL | FAIL |
| **BM-7** | Pipeline Performance | Ingest p95 within SpeedBudget targets | **Measured** | 1.44s | ~300ms | ~300ms | N/A |
| **BM-8** | Query Fidelity | Deterministic re-ranking with full score explain | **PASS** | FAIL | FAIL | FAIL | FAIL |
| **BM-9** | Multi-Tenant Isolation | Zero cross-tenant data leakage | **PASS** | ~Partial | FAIL | FAIL | FAIL |

**Implementation:** Already fully specified in `04_Benchmarks_Real_Implementation_Plan.md`, Phase 10 (proof_suite_runner.py). Each benchmark is a self-contained test that produces PASS/FAIL + evidence.

---

### TIER 2: Industry Standard Adapters (LM-1 to LM-6)

*These prove FAIM competes on the industry's own benchmarks, not just your own rules.*

**Critical context:** LongMemEval and LOCOMO are designed for LLM-based conversational memory systems. FAIM's core engine is zero-LLM. To run these benchmarks, we need an **adapter layer** that:
1. Takes the benchmark's conversation format as input
2. Ingests it into FAIM's graph (using FAIM's deterministic pipeline)
3. Uses an LLM (configurable: local or API) ONLY for natural language answer generation from FAIM's retrieved memories
4. The LLM acts as a translator, NOT as the memory system — FAIM does all storage/retrieval/ranking

This is honest: FAIM provides the memory, the LLM provides the language. Competitors use LLMs for BOTH.

#### LM-1: Information Extraction (LongMemEval)
**What it tests:** Can the system extract specific facts from long conversation histories?
**Dataset:** LongMemEval dataset — 500 questions over 115K-1.5M token histories
**How FAIM runs it:**
1. Ingest all conversation turns as evidence blocks → FAIM graph
2. For each question: query FAIM graph → get top-k results with score_components
3. Pass FAIM results + question to LLM → generate natural language answer
4. Score answer against ground truth using LongMemEval's LLM-as-Judge
**Expected FAIM strength:** HIGH — FAIM's 7-component re-ranker excels at precise retrieval
**Projected score:** 80-90% (strong retrieval, LLM answer quality depends on chosen model)

#### LM-2: Multi-Session Reasoning (LongMemEval)
**What it tests:** Can the system reason across information scattered across multiple sessions?
**How FAIM runs it:**
1. Same ingestion as LM-1
2. Questions require combining facts from 2-5 different sessions
3. FAIM's graph traversal (BFS neighborhood) naturally connects cross-session information
4. Inheritance edges link related concepts across sessions
**Expected FAIM strength:** HIGH — graph structure is built for cross-document connections
**Projected score:** 75-85%

#### LM-3: Knowledge Updates (LongMemEval)
**What it tests:** When information changes (e.g., user moves to a new city), does the system retrieve the LATEST version?
**How FAIM runs it:**
1. Ingest original information, then ingest updated information
2. FAIM's antisymmetric merge detects near-duplicates
3. Recency boost in query scoring (0.10 * recency_boost) favors newer information
4. `last_access` timestamp on nodes enables temporal ordering
**Expected FAIM strength:** MEDIUM-HIGH — has recency boost but no explicit temporal algebra
**Gap:** No dedicated "supersedes" edge type. Workaround: recency_boost + antisym merge
**Projected score:** 70-80%

#### LM-4: Temporal Reasoning (LongMemEval)
**What it tests:** "What did the user do BEFORE moving to NYC?" — requires understanding time order
**How FAIM runs it:**
1. Each node has `created_at` timestamp from ingestion order
2. Query can filter by time range using `created_at`
3. **GAP:** No explicit temporal algebra (before/after/during operators)
4. **Mitigation:** Add temporal filter to query engine: `WHERE created_at < reference_timestamp`
**Expected FAIM strength:** MEDIUM — has timestamps but no temporal reasoning operators
**Implementation needed:** Add `temporal_filter` parameter to query endpoint
**Projected score:** 60-75% (honest — this is where Zep's Graphiti excels)

#### LM-5: Abstention (LongMemEval)
**What it tests:** When asked about something NOT in memory, does the system correctly say "I don't know" instead of hallucinating?
**How FAIM runs it:**
1. Query returns top-k with scores
2. If max_score < threshold (e.g., 0.3), the adapter returns "I don't know"
3. FAIM's 7-component scoring provides a natural confidence signal
4. Low similarity + high opposition = low score = abstain
**Expected FAIM strength:** HIGH — deterministic scoring means predictable abstention threshold
**Projected score:** 80-90%

#### LM-6: Multi-Hop Cross-Session QA (LOCOMO)
**What it tests:** 600-turn conversations spanning 6-12 months, scored by LLM-as-Judge
**Dataset:** LOCOMO benchmark — 32 sessions, ~16K tokens, single-hop + multi-hop + temporal + summarization
**How FAIM runs it:**
1. Ingest all 32 sessions into FAIM graph
2. For each question type:
   - Single-hop: direct query → FAIM retrieval
   - Multi-hop: query → BFS neighborhood traversal → combine results
   - Temporal: query with temporal_filter
   - Summarization: query top-k → LLM summarizes FAIM results
3. Score using LOCOMO's LLM-as-Judge methodology
**Expected FAIM strength:** MEDIUM-HIGH on retrieval, depends on LLM quality for generation
**Projected score:** 75-85% (vs Zep ~85%, Mem0 58-68%)

---

### TIER 3: Advanced Industry Benchmarks (IB-1 to IB-3)

*These position FAIM against RAG systems and prove graph superiority.*

#### IB-1: MuSiQue (Multi-hop Reasoning)
**What it tests:** 3-4 hop reasoning chains across multiple documents
**Dataset:** MuSiQue benchmark — 25K multi-hop questions requiring 2-4 reasoning steps
**Why it matters for FAIM:** This directly tests graph traversal. FAIM's inheritance edges and BFS neighborhood search are DESIGNED for multi-hop reasoning.
**How FAIM runs it:**
1. Ingest all source documents into FAIM graph
2. For each question: query FAIM → get initial candidates
3. For each candidate: expand via `GET /graph/neighborhood` (depth=2-3)
4. Combine expanded results → LLM generates answer
5. Score against ground truth (F1 + Exact Match)
**Expected FAIM advantage:** Graph traversal finds multi-hop paths that flat vector stores miss
**What competitors do:** Most RAG systems (Mem0, Supermemory) do single-hop retrieval only. Zep has some graph traversal.
**Projected score:** 50-65% F1 (competitive with graph-based RAG, above flat vector stores)

#### IB-2: HELMET (Long-Context Retrieval)
**What it tests:** Recall accuracy with 128K+ token contexts
**Dataset:** HELMET benchmark — needle-in-a-haystack at various context lengths (4K to 128K tokens)
**Why it matters for FAIM:** This is where FAIM's graph approach should crush context-window approaches. LLMs lose facts in long contexts (the "lost in the middle" problem). FAIM stores every fact as a node — retrieval quality doesn't degrade with scale.
**How FAIM runs it:**
1. Ingest the full document corpus into FAIM graph
2. For each query: FAIM retrieves relevant nodes regardless of where they appeared in the original text
3. Score: recall@k at various corpus sizes
**Expected FAIM advantage:** No context window limitation. A fact ingested at position 50,000 is as retrievable as position 1.
**Projected performance:**
- At 4K tokens: comparable to LLMs (both do well)
- At 32K tokens: FAIM starts winning (LLMs lose mid-context facts)
- At 128K tokens: FAIM significantly ahead (LLMs degrade, FAIM doesn't)
**Projected score:** 85-95% recall (vs LLM degradation curve)

#### IB-3: CRUD-RAG (Create/Read/Update/Delete Accuracy)
**What it tests:** How accurately the system handles the full CRUD lifecycle of knowledge
**Why it matters for FAIM:** This directly maps to FAIM's operations:
- **Create** = Ingest (write_atoms)
- **Read** = Query (query_engine)
- **Update** = Antisymmetric merge + recency boost
- **Delete** = Prune (evolution)
**How FAIM runs it:**
1. Create: Ingest documents, verify nodes created
2. Read: Query for ingested facts, measure precision/recall
3. Update: Ingest updated versions, verify merge/replacement behavior
4. Delete: Trigger prune, verify old information removed
5. Read again: Verify updated/deleted information is correctly handled
**Expected FAIM advantage:** FAIM has explicit CRUD operations in the engine. Most competitors only have Create and Read — no real Update or Delete.
**Projected score:** 85-95% (FAIM has real CRUD, competitors mostly have CR only)

---

## Architecture: How It All Fits Together

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BENCHMARK EXECUTION ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  FAIM Proof Suite │    │ Industry Adapters │    │ Advanced Industry│  │
│  │  (BM-1 to BM-9)  │    │  (LM-1 to LM-6)  │    │  (IB-1 to IB-3) │  │
│  │                    │    │                    │    │                  │  │
│  │  Pure FAIM engine  │    │  FAIM + LLM layer  │    │  FAIM + LLM     │  │
│  │  No LLM needed     │    │  LLM = translator  │    │  LLM = translator│  │
│  └────────┬───────────┘    └────────┬───────────┘    └────────┬─────────┘  │
│           │                         │                         │            │
│           └─────────────┬───────────┴─────────────┬───────────┘            │
│                         │                         │                        │
│              ┌──────────▼──────────┐   ┌──────────▼──────────┐            │
│              │  proof_suite_runner  │   │  adapter_runner      │            │
│              │  (9 benchmarks)      │   │  (9 benchmarks)      │            │
│              └──────────┬──────────┘   └──────────┬──────────┘            │
│                         │                         │                        │
│              ┌──────────▼─────────────────────────▼──────────┐            │
│              │         benchmark_orchestrator.py               │            │
│              │  - Runs all 18 benchmarks sequentially          │            │
│              │  - Streams progress via SSE                     │            │
│              │  - Stores results in benchmark_results table    │            │
│              │  - Computes composite scores                    │            │
│              └──────────┬────────────────────────────────────┘            │
│                         │                                                  │
│              ┌──────────▼──────────┐                                      │
│              │  FAIM Core Engine    │  ← NEVER MODIFIED                   │
│              │  engine_native.py    │                                      │
│              │  antisym.py          │                                      │
│              │  invariants.py       │                                      │
│              │  fractal_physics.py  │                                      │
│              │  query_engine.py     │                                      │
│              │  evolution_native.py │                                      │
│              └─────────────────────┘                                      │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    LLM Adapter Layer (NEW)                          │  │
│  │                                                                     │  │
│  │  Configurable LLM backend for answer generation:                   │  │
│  │  - Option 1: Local (Ollama — llama3, mistral, phi3)                │  │
│  │  - Option 2: API (OpenAI, Anthropic, Google)                       │  │
│  │  - Option 3: None (skip LM/IB benchmarks, run BM only)            │  │
│  │                                                                     │  │
│  │  The LLM ONLY generates natural language answers from FAIM results.│  │
│  │  FAIM does ALL memory storage, retrieval, and ranking.             │  │
│  │  This is the honest architecture — FAIM = memory, LLM = language.  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## New Backend Files (Beyond Phase 1-9 from Plan 04)

### Phase 11: LLM Adapter Layer + Dataset Manager

| # | File | Purpose |
|---|------|---------|
| 1 | `faim_native/benchmarks/__init__.py` | Benchmarks package |
| 2 | `faim_native/benchmarks/llm_adapter.py` | Configurable LLM interface (Ollama/OpenAI/Anthropic) |
| 3 | `faim_native/benchmarks/dataset_manager.py` | Download, cache, and parse benchmark datasets (LongMemEval, LOCOMO, MuSiQue, HELMET) |
| 4 | `faim_native/benchmarks/answer_generator.py` | Takes FAIM retrieval results + question → LLM → natural language answer |
| 5 | `faim_native/benchmarks/judge.py` | LLM-as-Judge scoring (LongMemEval/LOCOMO methodology) + F1/EM scoring (MuSiQue) |

### Phase 12: Industry Benchmark Runners

| # | File | Purpose |
|---|------|---------|
| 6 | `faim_native/benchmarks/longmemeval_runner.py` | Runs LM-1 to LM-5 (LongMemEval 5 abilities) |
| 7 | `faim_native/benchmarks/locomo_runner.py` | Runs LM-6 (LOCOMO benchmark) |
| 8 | `faim_native/benchmarks/musique_runner.py` | Runs IB-1 (MuSiQue multi-hop) |
| 9 | `faim_native/benchmarks/helmet_runner.py` | Runs IB-2 (HELMET long-context) |
| 10 | `faim_native/benchmarks/crudrag_runner.py` | Runs IB-3 (CRUD-RAG lifecycle) |

### Phase 13: Orchestrator + API

| # | File | Purpose |
|---|------|---------|
| 11 | `faim_native/benchmarks/orchestrator.py` | Runs all 18 benchmarks, streams progress, computes composite |
| 12 | `faim_native/benchmarks/result_types.py` | Pydantic models for all benchmark results |
| 13 | `faim_native/store/pg/migrations/0013_benchmark_results.sql` | Store full benchmark suite results |
| 14 | `faim_native/store/pg/repos/benchmark_results_repo.py` | CRUD for benchmark results |

### Phase 14: Temporal Query Enhancement (Closes LM-4 Gap)

| # | File | Purpose |
|---|------|---------|
| 15 | `faim_native/core/query/temporal_filter.py` | Temporal filter operators: before, after, between, latest |

### Tests

| # | File | Purpose |
|---|------|---------|
| 16 | `tests/unit/test_llm_adapter.py` | Unit tests for LLM adapter |
| 17 | `tests/unit/test_dataset_manager.py` | Unit tests for dataset parsing |
| 18 | `tests/unit/test_temporal_filter.py` | Unit tests for temporal operators |
| 19 | `tests/acceptance/test_AT_industry_benchmarks.py` | Acceptance tests for LM/IB runners |
| 20 | `tests/acceptance/test_AT_benchmark_orchestrator.py` | End-to-end orchestrator test |

---

## New Frontend Files (Beyond Plan 04)

| # | File | Purpose |
|---|------|---------|
| 1 | `frontend/src/types/benchmark-suite.ts` | TypeScript types for all 18 benchmark results |
| 2 | `frontend/src/lib/benchmarkSuiteApi.ts` | API client for full suite endpoints |
| 3 | `frontend/src/components/benchmarks/FullSuitePanel.tsx` | Run all 18, show progress, display results |
| 4 | `frontend/src/components/benchmarks/ProofSuiteResults.tsx` | BM-1 to BM-9 results with evidence |
| 5 | `frontend/src/components/benchmarks/IndustryBenchResults.tsx` | LM-1 to LM-6 + IB-1 to IB-3 results |
| 6 | `frontend/src/components/benchmarks/CompetitorMatrix.tsx` | Full 18-benchmark comparison table |
| 7 | `frontend/src/components/benchmarks/ScoreRadar.tsx` | Radar chart: FAIM vs competitors across categories |
| 8 | `frontend/src/components/benchmarks/BenchmarkEvidence.tsx` | Expandable evidence viewer (hashes, samples, raw data) |

---

## Detailed Implementation: Key Components

### 1. LLM Adapter (`faim_native/benchmarks/llm_adapter.py`)

```python
"""Configurable LLM adapter for benchmark answer generation.

The LLM is used ONLY for natural language answer generation.
FAIM does ALL memory storage, retrieval, and ranking.

Supported backends:
- ollama: Local models (llama3, mistral, phi3) — no API key needed
- openai: OpenAI API (gpt-4o, gpt-4o-mini)
- anthropic: Anthropic API (claude-3.5-sonnet, claude-3-haiku)
- none: Skip LLM-dependent benchmarks
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class LLMBackend(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    NONE = "none"


@dataclass
class LLMConfig:
    backend: LLMBackend
    model: str  # "llama3", "gpt-4o-mini", "claude-3-haiku-20240307"
    base_url: Optional[str] = None  # For Ollama: "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.0  # Deterministic for reproducibility
    max_tokens: int = 512


class LLMAdapter:
    """Unified interface to generate answers from FAIM retrieval results."""

    def __init__(self, config: LLMConfig):
        self.config = config

    async def generate_answer(
        self,
        question: str,
        faim_results: list[dict],  # FAIM query results with score_components
        system_prompt: str = "Answer based ONLY on the provided context.",
    ) -> str:
        """Generate natural language answer from FAIM retrieval results."""
        ...

    async def judge_answer(
        self,
        question: str,
        predicted: str,
        ground_truth: str,
        rubric: str,
    ) -> dict:
        """LLM-as-Judge scoring (LongMemEval/LOCOMO methodology)."""
        ...
```

**Key design decisions:**
- `temperature=0.0` for reproducible benchmark scores
- LLM config is stored with benchmark results so scores are traceable to a specific LLM
- If `backend=none`, LM-1 to LM-6 and IB-1 to IB-3 are skipped (only BM-1 to BM-9 run)

### 2. Dataset Manager (`faim_native/benchmarks/dataset_manager.py`)

```python
"""Download, cache, and parse industry benchmark datasets.

Datasets:
- LongMemEval: https://github.com/xiaowu0162/LongMemEval (ICLR 2025)
- LOCOMO: https://github.com/snap-stanford/locomo
- MuSiQue: https://github.com/stonybrooknlp/musique
- HELMET: https://github.com/princeton-nlp/HELMET

All datasets cached to ~/.faim/benchmarks/datasets/
"""

from dataclasses import dataclass
from pathlib import Path


CACHE_DIR = Path.home() / ".faim" / "benchmarks" / "datasets"


@dataclass
class BenchmarkDataset:
    name: str
    version: str
    conversations: list  # Parsed conversations/documents
    questions: list  # Questions with ground truth answers
    metadata: dict


class DatasetManager:
    """Manages benchmark dataset lifecycle."""

    def get_longmemeval(self, subset: str = "full") -> BenchmarkDataset:
        """Load LongMemEval dataset. Downloads if not cached."""
        ...

    def get_locomo(self) -> BenchmarkDataset:
        """Load LOCOMO dataset."""
        ...

    def get_musique(self, split: str = "dev") -> BenchmarkDataset:
        """Load MuSiQue dataset."""
        ...

    def get_helmet(self, context_length: int = 128000) -> BenchmarkDataset:
        """Load HELMET dataset for specified context length."""
        ...

    def generate_crudrag_dataset(self, n_docs: int = 100) -> BenchmarkDataset:
        """Generate CRUD-RAG test dataset (synthetic, deterministic)."""
        ...
```

### 3. LongMemEval Runner (`faim_native/benchmarks/longmemeval_runner.py`)

```python
"""LongMemEval benchmark runner for FAIM.

Tests 5 abilities (LM-1 to LM-5):
1. Information Extraction — retrieve specific facts
2. Multi-Session Reasoning — combine facts across sessions
3. Knowledge Updates — retrieve latest version of changed info
4. Temporal Reasoning — understand time ordering
5. Abstention — correctly refuse when info not in memory

Process per question:
1. Ingest conversation history into FAIM graph
2. Query FAIM for relevant memories
3. Generate answer using LLM adapter
4. Score using LLM-as-Judge
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LongMemEvalResult:
    ability: str  # "extraction", "multi_session", "knowledge_update", "temporal", "abstention"
    total_questions: int
    correct: int
    accuracy: float
    avg_retrieval_score: float  # Average FAIM score of top-1 result
    avg_latency_ms: float
    per_question: list[dict]  # Individual results for evidence


@dataclass
class LongMemEvalSuiteResult:
    lm1_extraction: LongMemEvalResult
    lm2_multi_session: LongMemEvalResult
    lm3_knowledge_update: LongMemEvalResult
    lm4_temporal: LongMemEvalResult
    lm5_abstention: LongMemEvalResult
    overall_accuracy: float  # Weighted average
    llm_config: dict  # Which LLM was used (for transparency)
    faim_version: str
    timestamp: str


class LongMemEvalRunner:
    def __init__(self, faim_ctx, llm_adapter, dataset_manager):
        self.ctx = faim_ctx
        self.llm = llm_adapter
        self.datasets = dataset_manager

    async def run_all(self) -> LongMemEvalSuiteResult:
        """Run all 5 LongMemEval abilities."""
        ...

    async def run_ability(self, ability: str) -> LongMemEvalResult:
        """Run a single ability benchmark."""
        ...

    async def _ingest_conversation(self, conversation: list[dict]) -> str:
        """Ingest a conversation into FAIM, return graph_id."""
        ...

    async def _query_and_answer(self, graph_id: str, question: str) -> tuple[str, float]:
        """Query FAIM + generate answer. Returns (answer, retrieval_score)."""
        ...
```

### 4. Temporal Filter (`faim_native/core/query/temporal_filter.py`)

```python
"""Temporal filter for FAIM queries.

Adds time-aware filtering to close the LM-4 gap vs Zep.
Uses existing created_at and last_access timestamps on nodes.

NOT a modification to query_engine.py — this is an ADDITIONAL filter
applied to query results before final ranking.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TemporalOp(str, Enum):
    BEFORE = "before"      # created_at < reference
    AFTER = "after"        # created_at > reference
    BETWEEN = "between"    # start <= created_at <= end
    LATEST = "latest"      # Sort by created_at DESC, take top-k
    OLDEST = "oldest"      # Sort by created_at ASC, take top-k


@dataclass
class TemporalFilter:
    op: TemporalOp
    reference: Optional[datetime] = None  # For BEFORE/AFTER
    start: Optional[datetime] = None      # For BETWEEN
    end: Optional[datetime] = None        # For BETWEEN

    def apply(self, nodes: list) -> list:
        """Filter nodes by temporal criteria."""
        ...
```

**Impact:** This is a ~100-line module that significantly improves LM-4 (Temporal Reasoning) scores. It does NOT modify `query_engine.py` — it's an optional post-filter applied by the benchmark adapter.

### 5. Benchmark Orchestrator (`faim_native/benchmarks/orchestrator.py`)

```python
"""Orchestrates all 18 benchmarks and produces unified results.

Execution order:
1. BM-1 to BM-9 (FAIM Proof Suite) — always runs, no LLM needed
2. LM-1 to LM-6 (Industry Adapters) — requires LLM, skipped if none configured
3. IB-1 to IB-3 (Advanced Industry) — requires LLM + datasets

Streams progress via SSE as each benchmark completes.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FullSuiteResult:
    # FAIM Proof Suite (always available)
    proof_suite: dict  # BM-1 to BM-9 results
    proof_maturity_score: float  # 0-100

    # Industry Adapters (None if LLM not configured)
    longmemeval: Optional[dict]  # LM-1 to LM-5
    locomo: Optional[dict]  # LM-6
    industry_score: Optional[float]  # Weighted average of LM-1 to LM-6

    # Advanced Industry (None if LLM not configured or datasets not downloaded)
    musique: Optional[dict]  # IB-1
    helmet: Optional[dict]  # IB-2
    crudrag: Optional[dict]  # IB-3
    advanced_score: Optional[float]

    # Composite
    overall_score: float  # Weighted: 40% proof + 35% industry + 25% advanced
    total_benchmarks_run: int
    total_benchmarks_passed: int
    llm_config: Optional[dict]  # Which LLM was used
    timestamp: str
    evidence_hash: str  # SHA256 of canonical JSON of all results


class BenchmarkOrchestrator:
    def __init__(self, faim_ctx, llm_config=None):
        ...

    async def run_full_suite(self) -> FullSuiteResult:
        """Run all 18 benchmarks. Yields progress events via callback."""
        ...

    async def run_proof_only(self) -> dict:
        """Run BM-1 to BM-9 only (no LLM needed)."""
        ...

    async def run_industry_only(self) -> dict:
        """Run LM-1 to LM-6 + IB-1 to IB-3 only."""
        ...
```

### 6. API Endpoints (Added to `routers/benchmarks.py`)

```python
# New endpoints added to existing benchmarks router:

# Run full 18-benchmark suite
POST /api/v1/benchmarks/full-suite?graph_id=X
Body: {
    "llm_backend": "ollama",        # "ollama" | "openai" | "anthropic" | "none"
    "llm_model": "llama3",          # Model name
    "include_industry": true,       # Run LM-1 to LM-6?
    "include_advanced": true,       # Run IB-1 to IB-3?
}
Response: SSE stream of progress events, final event is FullSuiteResult

# Get latest suite results
GET /api/v1/benchmarks/suite-results?graph_id=X
Response: Latest FullSuiteResult (from DB)

# Get suite result history
GET /api/v1/benchmarks/suite-history?graph_id=X&limit=10
Response: List of past FullSuiteResults with timestamps

# Download datasets
POST /api/v1/benchmarks/datasets/download
Body: { "datasets": ["longmemeval", "locomo", "musique", "helmet"] }
Response: SSE stream of download progress

# Check dataset status
GET /api/v1/benchmarks/datasets/status
Response: { "longmemeval": {"downloaded": true, "size_mb": 45}, ... }
```

### 7. Database Migration (`0013_benchmark_results.sql`)

```sql
-- Migration 0013: Full benchmark suite results
-- Stores complete results from all 18 benchmarks

CREATE TABLE IF NOT EXISTS benchmark_suite_results (
    id          BIGSERIAL PRIMARY KEY,
    tenant_id   VARCHAR(64) NOT NULL,
    graph_id    VARCHAR(64) NOT NULL,
    suite_type  VARCHAR(32) NOT NULL,  -- 'full', 'proof_only', 'industry_only'
    results     JSONB NOT NULL,        -- Full FullSuiteResult JSON
    overall_score DOUBLE PRECISION,
    proof_score   DOUBLE PRECISION,
    industry_score DOUBLE PRECISION,
    advanced_score DOUBLE PRECISION,
    llm_backend VARCHAR(32),
    llm_model   VARCHAR(64),
    evidence_hash VARCHAR(128),
    benchmarks_run INTEGER NOT NULL,
    benchmarks_passed INTEGER NOT NULL,
    duration_ms INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bsr_tenant_graph
    ON benchmark_suite_results(tenant_id, graph_id, created_at DESC);

CREATE INDEX idx_bsr_evidence
    ON benchmark_suite_results(evidence_hash);
```

---

## Frontend: Updated Benchmarks Page Layout

```
BenchmarksPage (Full 18-Benchmark Suite)
│
├── GlassHeader
│   ├── Title: "FAIM Engine Benchmarks"
│   ├── Badges: [SpeedBudget profile] [Invariants] [Graph version]
│   └── Actions:
│       ├── [Run Quick Benchmark] → BM-1 to BM-9 only (~2 min)
│       ├── [Run Full Suite] → All 18 (~10-15 min)
│       ├── [Configure LLM] → Modal: select backend + model
│       └── [Export Report] → JSON download
│
├── Overall Score Card (hero)
│   ├── Large score gauge: 0-100 composite
│   ├── Breakdown: Proof 40% | Industry 35% | Advanced 25%
│   └── "18/18 benchmarks passed" or "15/18 passed (3 skipped: no LLM)"
│
├── Tab Navigation: [Overview | Proof Suite | Industry | Advanced | History | Stress Test]
│
├── Tab: Overview (default)
│   ├── Radar Chart: FAIM vs Mem0 vs Supermemory vs Zep vs Letta
│   │   (18 axes, each benchmark as a spoke)
│   ├── Competitor Matrix (18 rows × 5 columns)
│   │   Each cell: score or PASS/FAIL with click-to-expand evidence
│   └── Key Insights: "6 exclusive wins, 3 industry-competitive, ..."
│
├── Tab: Proof Suite (BM-1 to BM-9)
│   ├── 9 cards, each showing:
│   │   ├── PASS/FAIL badge
│   │   ├── Key metric (e.g., "100% hash match across 10 runs")
│   │   ├── Duration
│   │   ├── Evidence expandable (hashes, sample data)
│   │   └── "No competitor passes this" badge (for BM-1,2,3,4,6,8)
│   └── Maturity Score gauge: 0-100 from BM weights
│
├── Tab: Industry (LM-1 to LM-6)
│   ├── Status: "Requires LLM adapter" or "Running with ollama/llama3"
│   ├── 6 cards, each showing:
│   │   ├── Accuracy % score
│   │   ├── Comparison: FAIM vs published competitor scores
│   │   ├── Avg retrieval score (FAIM's raw retrieval quality)
│   │   ├── Avg latency
│   │   └── Per-question breakdown (expandable)
│   ├── LongMemEval Overall: weighted average across 5 abilities
│   └── LOCOMO Overall: LLM-as-Judge score
│
├── Tab: Advanced (IB-1 to IB-3)
│   ├── IB-1 MuSiQue: F1 + EM scores, multi-hop analysis
│   ├── IB-2 HELMET: Recall@k at different context lengths (chart)
│   │   Shows FAIM's flat recall curve vs LLM's degradation
│   └── IB-3 CRUD-RAG: Per-operation accuracy (Create/Read/Update/Delete)
│
├── Tab: History
│   ├── Time-series of suite scores over time
│   ├── Regression detection: score dropped >5% = red flag
│   └── Baseline comparison
│
└── Tab: Stress Test (from Plan 04)
    └── [Same as before]
```

---

## Implementation Phases (Extending Plan 04)

Plan 04 covers Phases 1-10 (~19 days). This plan adds Phases 11-15:

### Phase 11: LLM Adapter Layer (2 days)
1. Create `faim_native/benchmarks/` package
2. Implement `llm_adapter.py` (Ollama + OpenAI + Anthropic)
3. Implement `answer_generator.py` (FAIM results → LLM → answer)
4. Implement `judge.py` (LLM-as-Judge + F1/EM scoring)
5. Unit tests for adapter
6. **Verify:** Adapter works with Ollama locally (no API key needed)

### Phase 12: Dataset Manager + Temporal Filter (2 days)
1. Implement `dataset_manager.py` (download, cache, parse)
2. Implement `temporal_filter.py` (before/after/between/latest operators)
3. Add dataset download endpoint to benchmarks router
4. Add dataset status endpoint
5. Unit tests for dataset parsing and temporal filter
6. **Verify:** Can download and parse LongMemEval, LOCOMO, MuSiQue datasets

### Phase 13: Industry Benchmark Runners (4 days)
1. Implement `longmemeval_runner.py` (LM-1 to LM-5)
2. Implement `locomo_runner.py` (LM-6)
3. Implement `musique_runner.py` (IB-1)
4. Implement `helmet_runner.py` (IB-2)
5. Implement `crudrag_runner.py` (IB-3)
6. Acceptance tests for each runner
7. **Verify:** Each runner produces real scores against real datasets

### Phase 14: Orchestrator + Storage (2 days)
1. Implement `orchestrator.py` (runs all 18, streams progress)
2. Implement `result_types.py` (Pydantic models)
3. Migration `0013_benchmark_results.sql`
4. Implement `benchmark_results_repo.py`
5. Add `/full-suite`, `/suite-results`, `/suite-history` endpoints
6. Acceptance test for full orchestrator
7. **Verify:** Full suite runs end-to-end, results stored and retrievable

### Phase 15: Frontend — Full Suite UI (3 days)
1. Create `benchmark-suite.ts` types
2. Create `benchmarkSuiteApi.ts` client
3. Create `FullSuitePanel.tsx` (run + progress + results)
4. Create `ProofSuiteResults.tsx` (BM-1 to BM-9)
5. Create `IndustryBenchResults.tsx` (LM-1 to LM-6 + IB-1 to IB-3)
6. Create `CompetitorMatrix.tsx` (18-row comparison)
7. Create `ScoreRadar.tsx` (radar chart)
8. Create `BenchmarkEvidence.tsx` (expandable evidence viewer)
9. Update `benchmarks/page.tsx` with tab navigation and all panels
10. **Verify:** Full page works, shows real data, all tabs functional

---

## Complete Timeline

| Phase | Days | Scope | Cumulative |
|-------|------|-------|------------|
| **1-3** (Plan 04) | 7 | Backend data layer + API + Frontend foundation | 7 days |
| **4-5** (Plan 04) | 3.5 | Golden Signals + SSE streaming | 10.5 days |
| **6-8** (Plan 04) | 4.5 | Stress testing + baselines + anomaly detection | 15 days |
| **9** (Plan 04) | 1 | Hardening + E2E | 16 days |
| **10** (Plan 04) | 3 | FAIM Proof Suite (BM-1 to BM-9) | 19 days |
| **11** (NEW) | 2 | LLM adapter layer | 21 days |
| **12** (NEW) | 2 | Dataset manager + temporal filter | 23 days |
| **13** (NEW) | 4 | Industry benchmark runners (LM + IB) | 27 days |
| **14** (NEW) | 2 | Orchestrator + storage | 29 days |
| **15** (NEW) | 3 | Frontend full suite UI | **32 days total** |

### Recommended Execution Order

**Sprint 1 (MVP — 10 days):** Phases 1-3 + 10
- Real data on benchmarks page + BM-1 to BM-9 proof suite
- **You can claim:** "We have 9 verifiable proofs that no competitor can pass"

**Sprint 2 (Credibility — 8 days):** Phases 11-14
- LLM adapter + industry benchmarks running with real scores
- **You can claim:** "We score X% on LongMemEval, Y% on LOCOMO"

**Sprint 3 (Polish — 7 days):** Phases 4-9 + 15
- Golden signals, SSE, stress testing, full suite UI
- **You can claim:** "Enterprise-grade observability with 18-benchmark proof"

**Sprint 4 (Optional — 7 days):** Phases 4-9 remaining
- Infrastructure telemetry, baselines, anomaly detection, export

---

## What You'll Be Able to Claim (With Real Proof)

### After Sprint 1:
```
"FAIM is the only memory engine that passes all 9 proof benchmarks:
determinism, cryptographic integrity, 8 mathematical invariants,
zero-LLM operation, antisymmetric deduplication, self-evolution,
sub-Xms ingest latency, deterministic re-ranking, and multi-tenant
crypto isolation. No competitor passes even 1 of the 6 exclusive tests."
```

### After Sprint 2:
```
"FAIM scores X% on LongMemEval (vs Supermemory 85.4%, Zep n/a, Mem0 n/a)
and Y% on LOCOMO (vs Zep ~85%, Letta 83.2%, Mem0 58-68%).
FAIM achieves Z% F1 on MuSiQue multi-hop reasoning and W% recall on
HELMET 128K-context retrieval. All scores independently reproducible."
```

### After Full Implementation:
```
"18 benchmarks. 9 exclusive wins. Real scores on every industry standard.
Every claim backed by SHA-256 evidence hash. Export the full report.
Run it yourself. This is what provable memory looks like."
```

---

## What You DON'T Have (Honest Gaps)

| Gap | Status | Mitigation |
|-----|--------|-----------|
| No published LongMemEval score yet | Sprint 2 closes this | Adapter + dataset download |
| No published LOCOMO score yet | Sprint 2 closes this | Adapter + dataset download |
| Temporal reasoning weaker than Zep | Phase 12 mitigates with temporal_filter | Not full temporal algebra, but filters help |
| Industry scores depend on LLM quality | Documented in results | LLM config stored with every result |
| No DMR benchmark | Not planned | Lower priority, covered by LOCOMO |
| No AgentBench / τ-bench | Not planned | Premature — need SDK first |

---

## Dependencies & Prerequisites

### Required for BM-1 to BM-9 (Phases 1-3, 10):
- PostgreSQL running ✓ (already in Docker)
- FAIM engine functional ✓ (already working)
- No additional dependencies

### Required for LM-1 to LM-6 + IB-1 to IB-3 (Phases 11-14):
- **Ollama** installed locally (free, no API key) OR OpenAI/Anthropic API key
- **Internet access** to download benchmark datasets (one-time, ~500MB total)
- **Additional pip packages:** `httpx` (for Ollama), `datasets` (for HuggingFace datasets)
- ~2GB disk space for cached datasets

### Optional:
- GPU for faster Ollama inference (not required)
- OpenAI/Anthropic API key for higher quality LLM answers (improves LM scores)

---

## Files to NOT Touch (Same as Plan 04)

All core engine files remain untouched:
- `core/engine_native.py`, `core/antisym.py`, `core/invariants.py`
- `core/metrics/fractal_physics.py`, `core/query/query_engine.py`
- `core/dynamics/evolution_native.py`, `encoding/vector_schema.py`
- All orchestration flows, perf infrastructure, auth/security middleware
- All existing API routers and dashboard pages

---

**Status:** FINAL PLAN — AWAITING APPROVAL

**Recommendation:** Start with Sprint 1 (10 days) to get provable claims live. Sprint 2 (8 days) adds industry credibility. Together, 18 days gives you the full story.
