# 90. FAIM Long-Tail Knowledge and Domain Adaptation

This document provides the formal architectural and mathematical specification for the **Long-Tail Knowledge and Domain Adaptation** engine inside the **Fractal Antisymmetric Inheritance Memory (FAIM)**. It outlines the deterministic entity linking, domain graph traversal, and edge weight scaling algorithms used to achieve high recall on specialized terminology without neural model fine-tuning.

---

## 1. Architectural Intent: Corpus Adaptation vs. Fine-Tuning

In specialized corporate domains (e.g., aerospace manufacturing, medical research, or proprietary financial trading), query retrieval frequently encounters **long-tail terminology**—highly specific jargon, internal product codes, and acronyms that do not exist in general-purpose models.

Traditional semantic search resolves this by **Fine-Tuning** embedding models or large language models on the target corpus. However, fine-tuning:
* **Is High-Risk & Expensive**: Requires massive GPU training runtimes and constant data preparation.
* **Introduces Hallucination Risk**: Finetuned models can stochastically associate terms, leading to incorrect retrieval links.
* **Suffers from Data Drift**: As internal vocabularies evolve daily, models must be constantly retrained, which is highly impractical.

**FAIM Long-Tail Knowledge & Domain Adaptation** replaces model fine-tuning with **deterministic graph ingestion and traversal**. Curated Knowledge Base (KB) dumps are loaded directly into the active graph as distinct nodes. The query engine then performs an algebraic traversal from text inputs to terms, resolving connections in microseconds:

$$\text{Query Input Text} \longrightarrow \text{Lexical Alias} \longrightarrow \text{Entity Node} \longrightarrow \text{Fact Assertions}$$

---

## 2. The Entity Linking & Traversal Pipeline

When a query is received, the engine performs a deterministic three-step entity linking and domain walk ([`entity_linking.py`](file:///home/sephi-asi/FAIM/faim_native/core/operators/entity_linking.py)):

```
                 [ Raw Query Text ]
                         |
                         v
       [ Step 1: Lexical Entity Resolution ]
                         |
                         v
       [ Step 2: Seed Node Identification ]
                         |
                         v
       [ Step 3: Multi-Relational Graph Walk ]
             |           |           |
             v           v           v
          (alias)    (relation)   (value/time)
```

### Step 1: Lexical Entity Resolution
The engine splits and normalizes the input query and matches it against the stored graph lexicon.
* Performs exact substring matches for multi-word phrases and word-level matches for single terms.
* Resolves matching records deterministically, sorting entries descending by weight to eliminate tie-breaking instabilities:
  $$\text{SortKey} = \left( -S_{\text{score}}, \text{str}(\text{kind}), \text{str}(\text{surface\_form}), \text{str}(\text{node\_id}) \right)$$

### Step 2: Seed Node Identification
For each matched lexicon record, the engine extracts the target UUID seed node linked within the database metadata payload.

### Step 3: Multi-Relational Graph Traversal
Starting from identified seed nodes, the engine executes a local neighborhood traversal up to $K$ hops (default limit = 24 neighbors) across six specialized structural edge kinds:
* `"entity_alias"`: Maps surface acronyms to canonical entity concepts.
* `"entity_relation"`: Links distinct entity nodes together.
* `"fact_value"` & `"fact_time"`: Anchors entities to specific facts, values, and times.
* `"domain_term"`: Registers localized vocabulary and specialized definitions.
* `"kb_source"`: Tracks original source document linkages.

---

## 3. Mathematical Edge-Scaling and Scoring

As the graph walk progresses, adjacent nodes are assigned relevance scores derived from edge weights (normalized from 64-bit database integers) and specific multiplier factors:

$$W(e) = \text{clamp} \left( \frac{\text{weight}_{\text{db}}}{10^9} \right)$$

### 3.1 Direct Seed Node Scoring
Seed nodes linked directly to query tokens receive an initial score based on their lexical match class:
* **Entity Alias Matches**:
  $$S_{\text{entity\_link}} = \min \left( 1.0, 0.7 + 0.3 \cdot S_{\text{lexical}} \right)$$
* **Relation Alias Matches**:
  $$S_{\text{fact\_support}} = \min \left( 1.0, 0.5 + 0.3 \cdot S_{\text{lexical}} \right)$$
* **General Domain Terms**:
  $$S_{\text{domain\_term}} = S_{\text{lexical}}$$

### 3.2 Traversal Multiplier Boosts
Nodes activated via neighbor links receive scores scaled by the relative importance of the connecting edge:
* **Relation Edges (`entity_relation`)**:
  $$S_{\text{fact\_support}} \longleftarrow \max \left( S_{\text{fact\_support}}, 0.65 \cdot W(e) \right)$$
* **Value & Time Anchors (`fact_value`/`fact_time`)**:
  $$S_{\text{fact\_support}} \longleftarrow \max \left( S_{\text{fact\_support}}, 0.55 \cdot W(e) \right)$$
* **Jargon Defs (`domain_term`)**:
  $$S_{\text{domain\_term}} \longleftarrow \max \left( S_{\text{domain\_term}}, 0.50 \cdot W(e) \right)$$
* **KB Citations (`kb_source`)**:
  $$S_{\text{fact\_support}} \longleftarrow \max \left( S_{\text{fact\_support}}, 0.45 \cdot W(e) \right)$$

This mathematical scaling boosts the final score of candidates located within dense, highly active knowledge clusters, ensuring that **long-tail domain facts are retrieved with high precision and absolute speed**.

---

## 4. Verification Protocols

The system’s correctness is verified under [`test_entity_linking.py`](file:///home/sephi-asi/FAIM/tests/unit/test_entity_linking.py):

* **Lexical Resolution & Traversal Verification**:
  ```python
  def test_resolve_query_links_matches_surface_forms():
      # Indexes sample lexicon rows
      # Resolves query "Acme Co revenue"
      # Assertions verify correct linked terms are extracted and sorted.
  ```
  ```python
  def test_build_domain_candidate_scores_adds_fact_support():
      # Creates seed terms and configures mocked edge repository
      # Executes neighborhood traversal score compilation
      # Assertions verify scores are correctly assigned using multiplier boosts.
  ```
* **Result**: **All long-tail domain adaptation tests execute and pass successfully!**
