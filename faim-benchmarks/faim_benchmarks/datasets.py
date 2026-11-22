"""Dataset loaders for BEIR, LoCoMo, and LongMemEval."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RetrievalBenchmarkSplit:
    name: str
    corpus: Dict[str, Dict[str, str]]
    queries: Dict[str, str]
    qrels: Dict[str, Dict[str, float]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationalTurn:
    speaker: str
    text: str
    timestamp: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class MemoryQACase:
    case_id: str
    category: str
    question: str
    answer: str
    evidence_ids: List[str]


@dataclass
class ConversationalBenchmarkSplit:
    name: str
    turns: List[ConversationalTurn]
    qa_cases: List[MemoryQACase]
    metadata: Dict[str, Any] = field(default_factory=dict)


BEIR_HF_DATASETS: Dict[str, Dict[str, str]] = {
    "scifact": {
        "corpus": "BeIR/scifact",
        "queries": "BeIR/scifact",
        "qrels": "BeIR/scifact-qrels",
    },
    "nfcorpus": {
        "corpus": "BeIR/nfcorpus",
        "queries": "BeIR/nfcorpus",
        "qrels": "BeIR/nfcorpus-qrels",
    },
    "fiqa": {"corpus": "BeIR/fiqa", "queries": "BeIR/fiqa", "qrels": "BeIR/fiqa-qrels"},
    "arguana": {
        "corpus": "BeIR/arguana",
        "queries": "BeIR/arguana",
        "qrels": "BeIR/arguana-qrels",
    },
    "trec-covid": {
        "corpus": "BeIR/trec-covid",
        "queries": "BeIR/trec-covid",
        "qrels": "BeIR/trec-covid-qrels",
    },
    "scidocs": {
        "corpus": "BeIR/scidocs",
        "queries": "BeIR/scidocs",
        "qrels": "BeIR/scidocs-qrels",
    },
    "hotpotqa": {
        "corpus": "BeIR/hotpotqa",
        "queries": "BeIR/hotpotqa",
        "qrels": "BeIR/hotpotqa-qrels",
    },
    "fever": {
        "corpus": "BeIR/fever",
        "queries": "BeIR/fever",
        "qrels": "BeIR/fever-qrels",
    },
    "nq": {"corpus": "BeIR/nq", "queries": "BeIR/nq", "qrels": "BeIR/nq-qrels"},
    "msmarco": {
        "corpus": "BeIR/msmarco",
        "queries": "BeIR/msmarco",
        "qrels": "BeIR/msmarco-qrels",
    },
}


def load_beir_split(
    dataset_name: str,
    *,
    local_dir: Optional[str] = None,
    max_corpus: Optional[int] = None,
    max_queries: Optional[int] = None,
    seed: int = 42,
) -> RetrievalBenchmarkSplit:
    """Load a BEIR split from a local directory (corpus.jsonl, queries.jsonl, qrels/test.tsv)
    or from HuggingFace `BeIR/*` via `datasets`."""
    if local_dir:
        return _load_beir_local(
            dataset_name,
            Path(local_dir),
            max_corpus=max_corpus,
            max_queries=max_queries,
            seed=seed,
        )

    if dataset_name not in BEIR_HF_DATASETS:
        raise ValueError(
            f"Unsupported BEIR dataset '{dataset_name}'. Supported: {sorted(BEIR_HF_DATASETS)}"
        )

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "Install `faim-benchmarks[datasets]` (`pip install datasets`) or pass --local-dir for BEIR."
        ) from exc

    spec = BEIR_HF_DATASETS[dataset_name]
    cache_dir = os.path.expanduser(
        os.getenv("FAIM_BENCH_DATA_DIR", "~/.faim/bench_datasets")
    )
    corpus_revision = (
        os.getenv("FAIM_BEIR_CORPUS_REVISION", "").strip()
        or os.getenv("FAIM_BEIR_REVISION", "").strip()
        or None
    )
    queries_revision = (
        os.getenv("FAIM_BEIR_QUERIES_REVISION", "").strip()
        or os.getenv("FAIM_BEIR_REVISION", "").strip()
        or None
    )
    qrels_revision = (
        os.getenv("FAIM_BEIR_QRELS_REVISION", "").strip()
        or os.getenv("FAIM_BEIR_REVISION", "").strip()
        or None
    )
    if not corpus_revision or not queries_revision or not qrels_revision:
        raise RuntimeError(
            "Pinned Hugging Face revisions are required for reproducible BEIR loads; "
            "set FAIM_BEIR_REVISION or all three FAIM_BEIR_*_REVISION variables."
        )
    corpus_kwargs = {"revision": corpus_revision}
    queries_kwargs = {"revision": queries_revision}
    qrels_kwargs = {"revision": qrels_revision}
    corpus_ds = load_dataset(  # nosec B615 - revision is required above
        spec["corpus"], "corpus", split="corpus", cache_dir=cache_dir, **corpus_kwargs
    )
    queries_ds = load_dataset(  # nosec B615 - revision is required above
        spec["queries"],
        "queries",
        split="queries",
        cache_dir=cache_dir,
        **queries_kwargs,
    )

    qrels_ds = None
    qrels_split = None
    for split_name in ("test", "dev", "validation", "train"):
        try:
            qrels_ds = load_dataset(  # nosec B615 - revision is required above
                spec["qrels"], split=split_name, cache_dir=cache_dir, **qrels_kwargs
            )
            qrels_split = split_name
            break
        except Exception:
            continue
    if qrels_ds is None:
        raise RuntimeError(f"Could not load qrels split for {dataset_name}")

    corpus: Dict[str, Dict[str, str]] = {}
    for row in corpus_ds:
        doc_id = str(row["_id"])
        corpus[doc_id] = {
            "title": str(row.get("title") or ""),
            "text": str(row.get("text") or ""),
        }

    queries_all: Dict[str, str] = {
        str(row["_id"]): str(row["text"]) for row in queries_ds
    }
    qrels: Dict[str, Dict[str, float]] = {}
    for row in qrels_ds:
        qid = str(row["query-id"])
        did = str(row["corpus-id"])
        score = float(row["score"])
        if score > 0 and qid in queries_all and did in corpus:
            qrels.setdefault(qid, {})[did] = score

    queries = {qid: queries_all[qid] for qid in qrels if qid in queries_all}
    return _subsample_retrieval(
        dataset_name,
        corpus,
        queries,
        qrels,
        max_corpus,
        max_queries,
        seed,
        metadata={
            "source_type": "huggingface_datasets",
            "corpus_source": spec["corpus"],
            "queries_source": spec["queries"],
            "qrels_source": spec["qrels"],
            "qrels_split": qrels_split,
            "revisions": {
                "corpus": corpus_revision or "unspecified",
                "queries": queries_revision or "unspecified",
                "qrels": qrels_revision or "unspecified",
            },
        },
    )


def _load_beir_local(
    name: str,
    root: Path,
    *,
    max_corpus: Optional[int],
    max_queries: Optional[int],
    seed: int,
) -> RetrievalBenchmarkSplit:
    corpus: Dict[str, Dict[str, str]] = {}
    with (root / "corpus.jsonl").open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            corpus[str(row["_id"])] = {
                "title": str(row.get("title") or ""),
                "text": str(row.get("text") or ""),
            }

    queries_all: Dict[str, str] = {}
    with (root / "queries.jsonl").open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            queries_all[str(row["_id"])] = str(row["text"])

    qrels_path = root / "qrels" / "test.tsv"
    if not qrels_path.exists():
        qrels_path = root / "qrels.tsv"
    qrels: Dict[str, Dict[str, float]] = {}
    with qrels_path.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if idx == 0 and parts[0].lower() in {"query-id", "qid"}:
                continue
            qid, did, score = parts[0], parts[1], float(parts[2])
            if score > 0 and qid in queries_all and did in corpus:
                qrels.setdefault(qid, {})[did] = score

    queries = {qid: queries_all[qid] for qid in qrels if qid in queries_all}
    return _subsample_retrieval(
        name,
        corpus,
        queries,
        qrels,
        max_corpus,
        max_queries,
        seed,
        metadata={
            "source_type": "local_beir_folder",
            "source_path": str(root.resolve()),
            "qrels_file": str(qrels_path.resolve()),
            # Local benchmark folders are commonly downloaded outside the
            # repository.  Operators can provide the archive/content digest so
            # the signed report remains reproducible and publication-gated.
            "revision": os.getenv("FAIM_BEIR_LOCAL_REVISION", "unspecified"),
        },
    )


def _subsample_retrieval(
    name: str,
    corpus: Dict[str, Dict[str, str]],
    queries: Dict[str, str],
    qrels: Dict[str, Dict[str, float]],
    max_corpus: Optional[int],
    max_queries: Optional[int],
    seed: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> RetrievalBenchmarkSplit:
    rng = random.Random(seed)
    qids = sorted(queries.keys())
    if max_queries is not None and len(qids) > max_queries:
        qids = sorted(rng.sample(qids, max_queries))
    sel_queries = {qid: queries[qid] for qid in qids}
    sel_qrels = {qid: qrels[qid] for qid in qids}

    if max_corpus is not None and len(corpus) > max_corpus:
        required_docs = {did for qr in sel_qrels.values() for did in qr.keys()}
        remaining = [did for did in sorted(corpus.keys()) if did not in required_docs]
        extra_needed = max(0, max_corpus - len(required_docs))
        picked = set(required_docs) | set(
            rng.sample(remaining, min(extra_needed, len(remaining)))
        )
        sel_corpus = {did: corpus[did] for did in sorted(picked)}
    else:
        sel_corpus = corpus

    return RetrievalBenchmarkSplit(
        name=name,
        corpus=sel_corpus,
        queries=sel_queries,
        qrels=sel_qrels,
        metadata={
            **(metadata or {}),
            "sampling": {
                "seed": seed,
                "max_corpus": max_corpus,
                "max_queries": max_queries,
                "corpus_size": len(sel_corpus),
                "query_count": len(sel_queries),
            },
        },
    )


def load_locomo_split(
    path: str, *, max_cases: Optional[int] = None
) -> ConversationalBenchmarkSplit:
    """Load LoCoMo JSON conversation + QA file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else [data]
    turns: List[ConversationalTurn] = []
    qa_cases: List[MemoryQACase] = []

    for conv_idx, conv in enumerate(records):
        conv_obj = conv.get("conversation", conv)
        for key, val in conv_obj.items():
            if key.startswith("session_") and isinstance(val, list):
                ts = conv_obj.get(f"{key}_date_time")
                for turn in val:
                    turns.append(
                        ConversationalTurn(
                            speaker=str(turn.get("speaker") or "user"),
                            text=str(turn.get("text") or ""),
                            timestamp=str(ts) if ts else None,
                            session_id=f"c{conv_idx}_{key}",
                        )
                    )
        for qa_idx, qa in enumerate(conv.get("qa", [])):
            qa_cases.append(
                MemoryQACase(
                    case_id=f"locomo_{conv_idx}_{qa_idx}",
                    category=str(qa.get("category", "general")),
                    question=str(qa["question"]),
                    answer=str(qa["answer"]),
                    evidence_ids=[str(e) for e in qa.get("evidence", [])],
                )
            )
    if max_cases is not None:
        qa_cases = qa_cases[:max_cases]
    return ConversationalBenchmarkSplit(
        name="locomo",
        turns=turns,
        qa_cases=qa_cases,
        metadata={
            "source_type": "local_json",
            "source_path": str(Path(path).resolve()),
        },
    )


def load_longmemeval_split(
    path: str, *, max_cases: Optional[int] = None
) -> ConversationalBenchmarkSplit:
    """Load LongMemEval JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else data.get("items", [])
    turns: List[ConversationalTurn] = []
    qa_cases: List[MemoryQACase] = []

    for idx, item in enumerate(records):
        sessions = item.get("haystack_sessions") or item.get("sessions") or []
        dates = item.get("haystack_dates") or []
        for s_idx, session in enumerate(sessions):
            ts = dates[s_idx] if s_idx < len(dates) else None
            for msg in session:
                turns.append(
                    ConversationalTurn(
                        speaker=str(msg.get("role") or "user"),
                        text=str(msg.get("content") or ""),
                        timestamp=str(ts) if ts else None,
                        session_id=f"lme_{idx}_{s_idx}",
                    )
                )
        qa_cases.append(
            MemoryQACase(
                case_id=str(item.get("question_id") or f"lme_{idx}"),
                category=str(item.get("question_type") or "general"),
                question=str(item["question"]),
                answer=str(item["answer"]),
                evidence_ids=[str(e) for e in item.get("answer_session_ids", [])],
            )
        )
    if max_cases is not None:
        qa_cases = qa_cases[:max_cases]
    return ConversationalBenchmarkSplit(
        name="longmemeval",
        turns=turns,
        qa_cases=qa_cases,
        metadata={
            "source_type": "local_json",
            "source_path": str(Path(path).resolve()),
        },
    )
