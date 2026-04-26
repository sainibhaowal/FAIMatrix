"""Dataset manager for FAIM-Bench v1.

Downloads and caches BEIR-format datasets from HuggingFace.
Datasets are cached in FAIM_BENCH_DATA_DIR (default: ~/.faim/bench_datasets).

BEIR datasets available on HuggingFace under BeIR/ organization:
    - scifact        5,183 corpus docs, 300 test queries  (~5 MB)
    - nfcorpus       3,633 corpus docs, 323 test queries  (~3 MB)
    - nq             2,681,468 corpus docs — large, skip for quick runs
    - hotpotqa       5,233 corpus docs, 7,405 test queries
    - fever          5,416 corpus docs, 6,666 test queries
    - msmarco        8.8M corpus docs, 6,980 dev queries
    - fiqa           57,638 corpus docs, 648 test queries (~50 MB)
    - scidocs        25,657 corpus docs, 1,000 test queries (~40 MB)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)

DATA_DIR = os.environ.get(
    "FAIM_BENCH_DATA_DIR",
    str(Path.home() / ".faim" / "bench_datasets"),
)

# HuggingFace dataset names for BEIR corpus/queries/qrels
# Each dataset has separate corpus, queries, and qrels splits
BEIR_HF_DATASETS: Dict[str, Dict[str, str]] = {
    "scifact": {
        "corpus": "BeIR/scifact",
        "queries": "BeIR/scifact",
        "qrels": "BeIR/scifact-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "fiqa": {
        "corpus": "BeIR/fiqa",
        "queries": "BeIR/fiqa",
        "qrels": "BeIR/fiqa-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "nfcorpus": {
        "corpus": "BeIR/nfcorpus",
        "queries": "BeIR/nfcorpus",
        "qrels": "BeIR/nfcorpus-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "scidocs": {
        "corpus": "BeIR/scidocs",
        "queries": "BeIR/scidocs",
        "qrels": "BeIR/scidocs-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "nq": {
        "corpus": "BeIR/nq",
        "queries": "BeIR/nq",
        "qrels": "BeIR/nq-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "hotpotqa": {
        "corpus": "BeIR/hotpotqa",
        "queries": "BeIR/hotpotqa",
        "qrels": "BeIR/hotpotqa-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "fever": {
        "corpus": "BeIR/fever",
        "queries": "BeIR/fever",
        "qrels": "BeIR/fever-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "validation,test,dev,train",
    },
    "msmarco": {
        "corpus": "BeIR/msmarco",
        "queries": "BeIR/msmarco",
        "qrels": "BeIR/msmarco-qrels",
        "corpus_split": "corpus",
        "queries_split": "queries",
        "qrels_splits": "dev,test,validation,train",
    },
}


class BeirDataset:
    """Loaded BEIR dataset ready for evaluation."""

    def __init__(
        self,
        name: str,
        corpus: Dict[str, Dict],  # doc_id → {"title": ..., "text": ...}
        queries: Dict[str, str],  # query_id → query_text
        qrels: Dict[str, Set[str]],  # query_id → set of relevant doc_ids
    ):
        self.name = name
        self.corpus = corpus
        self.queries = queries
        self.qrels = qrels

    @property
    def corpus_size(self) -> int:
        return len(self.corpus)

    @property
    def query_count(self) -> int:
        return len(self.queries)


def load_beir_dataset(
    name: str, max_corpus: Optional[int] = None, max_queries: Optional[int] = None
) -> BeirDataset:
    """Load a BEIR dataset from HuggingFace.

    Args:
        name: Dataset name (e.g. "scifact", "fiqa", "nfcorpus")
        max_corpus: Limit corpus size (for quick test runs). None = full corpus.
        max_queries: Limit query count. None = all test queries.
    """
    try:
        from datasets import load_dataset as hf_load
    except ImportError as exc:
        raise RuntimeError("datasets package required: pip install datasets") from exc

    if name not in BEIR_HF_DATASETS:
        raise ValueError(
            f"Unknown BEIR dataset '{name}'. Available: {list(BEIR_HF_DATASETS)}"
        )

    cfg = BEIR_HF_DATASETS[name]
    logger.info("Loading BEIR dataset '%s' from HuggingFace...", name)

    def _load_hf(repo: str, config_name: Optional[str], split: str):
        """Load a HuggingFace dataset while handling both old and new signatures."""
        attempts = []
        if config_name:
            attempts.append(lambda: hf_load(repo, config_name, split=split))
        attempts.append(lambda: hf_load(repo, split=split))
        last_error: Optional[Exception] = None
        for attempt in attempts:
            try:
                return attempt()
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"Unable to load dataset {repo}:{config_name}/{split}")

    # Corpus
    corpus_ds = _load_hf(cfg["corpus"], cfg["corpus_split"], cfg["corpus_split"])
    corpus: Dict[str, Dict] = {}
    for row in corpus_ds:
        doc_id = str(row.get("_id") or row.get("id") or "")
        if not doc_id:
            continue
        corpus[doc_id] = {
            "title": str(row.get("title") or ""),
            "text": str(row.get("text") or ""),
        }
        if max_corpus and len(corpus) >= max_corpus:
            break

    # Queries
    queries_ds = _load_hf(cfg["queries"], cfg["queries_split"], cfg["queries_split"])
    queries: Dict[str, str] = {}
    for row in queries_ds:
        qid = str(row.get("_id") or row.get("id") or "")
        text = str(row.get("text") or "")
        if qid and text:
            queries[qid] = text

    # Qrels
    qrels: Dict[str, Set[str]] = {}
    qrels_splits = [
        part.strip()
        for part in str(cfg.get("qrels_splits", "train,test")).split(",")
        if part.strip()
    ]
    last_error: Optional[Exception] = None
    for split_name in qrels_splits:
        try:
            qrels_ds = _load_hf(cfg["qrels"], None, split_name)
        except Exception as exc:
            last_error = exc
            continue

        for row in qrels_ds:
            qid = str(
                row.get("query-id") or row.get("query_id") or row.get("_id") or ""
            )
            doc_id = str(
                row.get("corpus-id") or row.get("corpus_id") or row.get("doc_id") or ""
            )
            score = int(row.get("score") or 0)
            if qid and doc_id and score > 0:
                qrels.setdefault(qid, set()).add(doc_id)

    if not qrels:
        raise RuntimeError(f"Unable to load qrels for {name}: {last_error}")

    # Only keep queries that have qrels and are in the corpus
    queries = {qid: text for qid, text in queries.items() if qid in qrels}
    if max_queries and len(queries) > max_queries:
        queries = dict(list(queries.items())[:max_queries])

    logger.info(
        "Loaded %s: %d corpus docs, %d queries, %d queries with qrels",
        name,
        len(corpus),
        len(queries),
        len(qrels),
    )
    return BeirDataset(name=name, corpus=corpus, queries=queries, qrels=qrels)
