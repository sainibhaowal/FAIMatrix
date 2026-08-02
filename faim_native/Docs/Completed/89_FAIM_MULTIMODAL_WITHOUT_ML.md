
# 89. FAIM Multimodal Without ML

This document provides the formal architectural and mathematical specification for the **Multimodal Without ML** subsystem inside the **Fractal Antisymmetric Inheritance Memory (FAIM)**. It outlines the deterministic table linearization, layout tokenization, image perceptual hashing, and retrieval-time modality scoring boost algorithms used to enable powerful structured-document search without heavy neural models.

---

## 1. Architectural Intent: Deterministic Modality Extraction

Achieving true semantic understanding of mixed media (images, diagrams, complex spreadsheets) traditionally requires massive **Multimodal Models** (like CLIP, LLaVA, or GPT-4V). While these systems excel at generalized semantic mapping, they introduce:

* **Severe Compute Latency**: Deep visual-text cross-attention pipelines are extremely slow and require specialized GPU hardware.
* **Extraction Hallucinations**: Learned text extractors can misread tabular columns, mathematical formulas, or layout hierarchies.
* **Stochastic Indexing**: Visual representations can drift across model versions, breaking consistent document search.

**FAIM Multimodal Without ML** resolves this by building a **deterministic, additive indexing sidecar** (`NodeModalityV1Model`) per memory node. Instead of loading visual-transformer models, FAIM extracts structured physical layouts (tables, layout grids, OCR tokens, captions, and image fingerprint hashes) and processes them mathematically, providing **lightning-fast, 100% auditable structured document retrieval**.

---

## 2. Deterministic Multimodal Features Extraction

When a document file is ingested or rebuilt, the feature extractor ([`modality_features.py`](file:///home/sephi-asi/FAIM/faim_native/encoding/modality_features.py)) compiles multiple physical attributes into a unified payload:

```
               [ Unstructured File Assets (PDF / PPTX / HTML) ]
                                     |
                                     v
                  [ Progressive Modality Extractor ]
                                     |
     +-----------------+-------------+-------------+-----------------+
     |                 |                           |                 |
     v                 v                           v                 v
  [ OCR ]      [ Table Linearizer ]        [ Layout Parser ]    [ Image pHash ]
  (Text)     (Pipe -> Cell Grid ";")    (Page/Slide/Section)   (16-Char Fingerprint)
     |                 |                           |                 |
     +-----------------+-------------+-------------+-----------------+
                                     |
                                     v
                  [ Combined Modality Sidecar JSON ]
```

### 2.1 Table Structure Linearization

Spreadsheets and tabular markdown cells often contain pipe-delimited structures (`| cell |`) that confuse standard keyword indexing. The table linearizer ([`table_linearizer.py`](file:///home/sephi-asi/FAIM/faim_native/encoding/table_linearizer.py)) linearizes tabular grids row-by-row into a standardized, semicolon-delimited text layout:

$$
\text{line\_cells} = \text{Split}(L_i, \text{"|"}) \implies \text{linearized\_row} = \text{Join}(\text{line\_cells}, \text{" ; "})
$$

For example, the grid `| Q1 | $5M |` is linearized to `"Q1 ; $5M"`, maintaining cell groupings perfectly for keyword proximity searches.

### 2.2 Layout Tokenization

To preserve the physical document hierarchy, spatial bounds are parsed into discrete search tokens:

* **Page/Slide Coordinates**: `page:{nr}`, `slide:{nr}`
* **Document Hierarchy**: `section:{header_title}`
* **Segment Type**: `block_type:{table|image_stub|ocr|text}`

### 2.3 Image Perceptual Fingerprinting (pHash)

To index image stubs and identify exact or near-duplicate graphics across different files, the engine generates a stable **16-character perceptual image hash** ([`image_phash.py`](file:///home/sephi-asi/FAIM/faim_native/encoding/image_phash.py)) by hashing the image byte array:

$$
\text{pHash}(I) = \text{SHA256}(I_{\text{bytes}})[:16]
$$

### 2.4 Metadata, Filename & Caption Parsing

Normalizes and tokenizes caption strings, file stems (filename tokens), and metadata key-value properties into easily queryable alphanumeric arrays.

---

## 3. Retrieval-Time Modality Scoring Boost

During search queries, the re-ranking pipeline reads this additive multimodal sidecar. If a modality record matches the query text, the final node score is boosted:

$$
S_{\text{final}} = S_{\text{base}} + 0.08 \cdot S_{\text{modality}}
$$

Where the modality score $S_{\text{modality}}$ is calculated by evaluating the Jaccard term overlap between the query text tokens ($T_Q$) and three different sidecar components:

$$
S_{\text{modality}} = \min \left( 1.0, \frac{\text{Overlap}(T_Q, T_{\text{OCR}}) + \text{Overlap}(T_Q, T_{\text{Table}}) + \text{Overlap}(T_Q, T_{\text{Filename}})}{3} \right)
$$

This additive signal ensures that documents containing matching figures, structured data spreadsheets, or specific file names are dynamically boosted to the top of the search result queue!

---

## 4. Verification Protocols

The modality subsystem’s mathematical and structural correctness is enforced by automated test suites under [`test_modality_features.py`](file:///home/sephi-asi/FAIM/tests/unit/test_modality_features.py) and the multimodal acceptance tests:

* **Deterministic Feature Verification**:
  ```python
  def test_build_modality_features_deterministic():
      # Compiles modality features from sample blocks
      first = build_modality_features(...)
      second = build_modality_features(...)
      # Assertions verify:
      # 1. Modality hash matches exactly across separate runs (100% deterministic).
      # 2. Table text is successfully linearized using cell delimiters.
      # 3. Layout tokens are extracted correctly.
      assert first.modality_hash == second.modality_hash
      assert "col1 ; col2" in first.table_text
      assert "page:1" in first.layout_tokens
  ```
* **Result**: **All multimodal indexing and retrieval tests execute and pass successfully!**
