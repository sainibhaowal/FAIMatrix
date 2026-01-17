# FAIM-Native Encoding Layer Documentation

Pure FAIM-native encoding with NO ML models, NO SentenceTransformer, NO randomness.

## Quick Start

```bash
# Encode atoms from file
python scripts/encode_atoms.py raw_id --file document.pdf --output vectors.json --validate
```

## FAIMVector v1 Schema

```python
from encoding.vector_schema import FAIMVector, VECTOR_DIMENSION, SCHEMA_VERSION

# SCHEMA_VERSION = "v1"
# VECTOR_DIMENSION = 256
```

### Fields

| Field            | Type         | Description                             |
| ---------------- | ------------ | --------------------------------------- |
| `id`             | UUID7        | Unique identifier                       |
| `schema_version` | str          | Always "v1"                             |
| `raw_id`         | str          | Reference to RawRef                     |
| `block_id`       | str          | Reference to EvidenceBlock              |
| `block_type`     | str          | "text", "table", etc.                   |
| `anchor_dict`    | dict         | BlockAnchor serialized                  |
| `v_native`       | tuple[float] | 256-dimensional vector                  |
| `parents`        | tuple[str]   | Parent IDs (Stage-4)                    |
| `fractions`      | tuple[float] | Parent weights (Stage-4)                |
| `residual`       | float        | Novelty proxy 0-1                       |
| `opp_signature`  | dict         | Opposition signature                    |
| `level`          | int          | Hierarchy level (0 for atoms)           |
| `usage`          | dict         | {touch_count, last_access}              |
| `provenance`     | dict         | {raw_id, anchor, extractor, confidence} |
| `vector_hash`    | str          | SHA256 of canonical JSON                |

## Usage

### Vectorize Block

```python
from encoding.text_vectorizer import vectorize_block

anchor = BlockAnchor(doc_type="text", char_start=0, char_end=100)
block = EvidenceBlock.create(raw_id="abc", anchor=anchor, content="Hello world")

vector = vectorize_block(block)
print(vector.vector_hash)
print(len(vector.v_native))  # 256
```

### Vectorize Multiple Blocks

```python
from encoding.text_vectorizer import vectorize_blocks

vectors = vectorize_blocks(blocks)
```

### Verify Hash

```python
assert vector.verify_hash()
```

## Algorithm

1. **Normalize**: whitespace collapse, NFC, lowercase
2. **N-grams**: 3,4,5-gram hashed to 240 buckets
3. **L2 normalize**: unit-length n-gram vector
4. **Stats**: 16 features appended
5. **Final**: 240 + 16 = **256 dimensions**

## Opposition Signature

Used for antisymmetric operations:

```python
{
    "norm": 0.98,      # L2 norm
    "density": 0.15,   # Non-zero ratio
    "max_val": 0.12,   # Max bucket value
    "mean_val": 0.04,  # Mean of non-zero
    "length": 0.05,    # Normalized text length
    "entropy": 0.23,   # Unique chars / length
    "top_0": 0.45,     # Top bucket index (normalized)
    "top_1": 0.12,
    "top_2": 0.78,
}
```

## Rules

| Rule            | Implementation                |
| --------------- | ----------------------------- |
| No ML models    | Hashed n-grams only           |
| No randomness   | Deterministic hashing         |
| Fixed dimension | Always 256                    |
| Stable hash     | Same input → same vector_hash |
| L2 bounded      | N-gram part is unit length    |
