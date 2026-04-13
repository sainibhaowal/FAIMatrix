# Phase 7: Multimodal Without ML

Phase 7 adds deterministic document-modality support to FAIM-Native.

## Scope

- OCR text reuse from existing extraction pipeline
- stable table linearization
- layout token capture
- deterministic image hash proxy
- filename / caption / metadata token indexing
- optional Docling extraction adapter
- explicit multimodal sidecar rebuild route
- additive modality-aware rerank boost

## Runtime Shape

1. extract blocks through current router or optional Docling adapter
2. derive modality sidecar features per stored file
3. persist sidecars keyed by node id
4. at query time, compute a bounded modality overlap bonus
5. existing FAIM rerank remains the primary scorer

## Determinism Constraints

- no learned multimodal model in retrieval
- stable table normalization
- stable image hash
- stable metadata tokenization
- deterministic fallback if Docling is unavailable

## Safety Constraints

- additive sidecar only
- no mutation of existing node vectors or graph edges
- query result contract unchanged
- fallback extractor path always available

## Backend Areas

- `encoding/table_linearizer.py`
- `encoding/image_phash.py`
- `encoding/modality_features.py`
- `perception/extract/docling_service.py`
- `orchestration/multimodal_backfill.py`
- `store/pg/repos/modality_repo.py`
- `api/routers/storage.py`
- `core/query/query_engine.py`

## Validation

Phase 7 is verified by:

- unit tests for modality feature determinism
- acceptance tests for multimodal sidecar rebuild
- acceptance tests for modality-aware rerank contribution
- storage/query/graph regression coverage
- full repository suite
