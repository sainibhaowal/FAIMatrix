-- 0014_repr_v2_normalized_text.sql
--
-- Add normalized_text to the additive Representation V2 sidecar.

ALTER TABLE node_repr_v2
    ADD COLUMN normalized_text TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN node_repr_v2.normalized_text IS
    'Deterministic normalized lexical text for explainable reranking';
