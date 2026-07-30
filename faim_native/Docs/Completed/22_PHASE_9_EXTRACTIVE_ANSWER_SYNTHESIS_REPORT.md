# 22 - Phase 9 Extractive Answer Synthesis Report

Status: Completed

Phase 9 adds a deterministic answer layer on top of FAIM retrieval.

## Scope

- deterministic span selection
- citation-first answer output
- contradiction-aware answer notes
- confidence scoring from evidence support
- provenance block and supporting quotes

## Runtime Shape

1. run normal FAIM retrieval and reranking
2. collect normalized evidence text from top ranked results
3. select the best supporting spans deterministically
4. build direct answer from the top surviving span
5. attach citations, contradiction notes, confidence, and provenance

## Safety Constraints

- no freeform generation
- zero-hallucination default
- additive API field only
- retrieval/ranking order unchanged

## Backend Areas

- `core/query/span_selection.py`
- `core/query/quote_extraction.py`
- `core/query/confidence_scoring.py`
- `core/query/answer_synthesis.py`
- `orchestration/query_flow.py`
- `api/routers/query.py`
- `api/routers/memory.py`

## Validation

Phase 9 is verified by:

- unit tests for span selection
- unit tests for quote extraction
- unit tests for confidence scoring
- unit tests for answer synthesis
- acceptance tests for direct answers and contradiction notes
