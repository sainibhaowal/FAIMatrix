-- 0030_semantic_signature_v1.sql
--
-- Phase A: Semantic Signature V1
-- Add deterministic semantic-style channels beside the existing
-- Representation V2 sidecar without changing the canonical v_native contract.

ALTER TABLE node_repr_v2
    ADD COLUMN IF NOT EXISTS semantic_phrase_counts JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS concept_counts JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS morphology_counts JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS alias_families JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS transliterated_tokens JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS stem_families JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS relation_cues JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS value_cues JSONB NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS temporal_cues JSONB NOT NULL DEFAULT '[]';

COMMENT ON COLUMN node_repr_v2.semantic_phrase_counts IS
    'Hashed semantic phrase and skip-phrase buckets for FAIM-native late-interaction style recall';
COMMENT ON COLUMN node_repr_v2.concept_counts IS
    'Hashed concept-family buckets derived from deterministic alias and concept-key expansion';
COMMENT ON COLUMN node_repr_v2.morphology_counts IS
    'Hashed morphology buckets derived from prefix, suffix, shape, and stem-family signals';
COMMENT ON COLUMN node_repr_v2.alias_families IS
    'Deterministic alias-family tuples such as llm|large_language_model';
COMMENT ON COLUMN node_repr_v2.transliterated_tokens IS
    'Cross-lingual transliteration tokens for zero-setup lexical bridging';
COMMENT ON COLUMN node_repr_v2.stem_families IS
    'Stem-family tuples preserving morphology-level lexical similarity';
COMMENT ON COLUMN node_repr_v2.relation_cues IS
    'Deterministic relation cues such as relation:ownership or relation:dependency';
COMMENT ON COLUMN node_repr_v2.value_cues IS
    'Deterministic numeric/currency/range cues mined from text';
COMMENT ON COLUMN node_repr_v2.temporal_cues IS
    'Deterministic temporal cues mined from date, year, and time language';
