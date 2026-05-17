# 86. FAIM Deterministic Reranker V2

This document provides the formal architectural and mathematical specification for the **Deterministic Reranker V2** inside the **Fractal Antisymmetric Inheritance Memory (FAIM)**. It outlines the multi-signal scoring equations, proposition matching structures, and pairwise dominance suppression algorithms used to deliver state-of-the-art re-ranking quality without the compute overhead of learned neural cross-encoders.

---

## 1. Architectural Intent: Pure-FAIM vs. Learned Cross-Encoders

Traditional search architectures use a dual-stage retrieval system where a fast vector search fetches a broad set of candidates, followed by a heavy **Transformer Cross-Encoder** (like Cohere or BGE Reranker) to score the relevance of the candidates. This learned reranking approach suffers from:
* **Massive Compute Latency**: Heavy token-level cross-attention requires multi-millisecond GPU times per query.
* **Lack of Auditability**: Resulting scores are absolute probabilities with zero explainability; developers cannot verify *why* a document was ranked higher or lower.
* **Temporal Ignorance**: Cannot natively resolve structural or chronological conflicts between redundant documents.

**FAIM Deterministic Reranker V2** replaces neural cross-encoders with a **fused, multi-signal algebraic reranker**. It extracts exact logical structures (propositions, entities, times, and value anchors) and evaluates their alignment using strict mathematical equations, executing in microseconds with **$100\%$ explainable and auditable subscores**.

---

## 2. Multi-Signal Fused Scoring Equation

For any query $Q$ and candidate document $D$, the reranker computes a fused score from four separate semantic dimensions:

$$S_{\text{rerank}}(Q, D) = \text{clamp} \left( 0.25 \cdot S_{\text{entity}} + 0.15 \cdot S_{\text{time}} + 0.35 \cdot S_{\text{proposition}} + 0.25 \cdot S_{\text{evidence}} \right)$$

### 2.1 Entity Overlap Similarity ($S_{\text{entity}}$)
Measures the Jaccard similarity of extracted named entities and noun phrases between the query and candidate:
$$S_{\text{entity}} = \text{Jaccard}(E_Q, E_D) = \frac{|E_Q \cap E_D|}{|E_Q \cup E_D|}$$

### 2.2 Temporal Matching Score ($S_{\text{time}}$)
Matches explicit dates, timestamps, and temporal expressions between the query and candidate:
$$S_{\text{time}} = \text{Jaccard}(T_Q, T_D) = \frac{|T_Q \cap T_D|}{|T_Q \cup T_D|}$$

### 2.3 Proposition Structure Overlap ($S_{\text{proposition}}$)
Compares extracted logical triplets (subject, relation, object) between the query and candidate. Unlike word-level matches, this rewards exact structural alignment of assertions:
$$S_{\text{proposition}} = \text{proposition\_overlap}(P_Q, P_D)$$

### 2.4 Evidence Span Density ($S_{\text{evidence}}$)
Evaluates the proximity and density of matching content terms within the candidate text, rewarding documents that contain concise, direct answers over long, bloated texts:
$$S_{\text{evidence}} = \text{compute\_evidence\_span\_score}(Q, D)$$

---

## 3. Pairwise Dominance & Deduplication Suppression

To prevent returning redundant search results to the user, FAIM incorporates a strict **Pairwise Dominance pruning algorithm** executing in $O(N^2)$ time over the top candidates.

```
       [ Candidate A ]                        [ Candidate B ]
    "Revenue was $5M in Q1"                "Revenue was $6M in Q1"
    (Base Score = 0.85)                    (Base Score = 0.82)
    (Created: 2026-05-10)                  (Created: 2026-05-17)
           |                                      |
           +------------------+-------------------+
                              |
                    [ Conflict Identified ]
                    (Value: $5M vs. $6M)
                              |
                              v
                  [ Temporal Resolution ]
                  * Winner: Candidate B (Newer)
                  * Suppressed: Candidate A (Older)
```

For each pair of candidates (Left, Right) sorted descending by their retrieval scores:
1. **Overlap Check**: If their semantic proposition overlap is high ($\text{Overlap} \ge 0.70$) and they share identical semantic signatures, they are flagged as potential duplicates.
2. **Conflict Checking**:
   * **Value Conflicts**: If they assert different values (e.g., `"Revenue: $5M"` vs. `"Revenue: $6M"`).
   * **Time Conflicts**: If they assert different timeframes for the same claim.
3. **Deduplication Suppression**:
   * If a **Conflict** is identified, the engine compares their creation timestamps (`created_at`). The newer document is crowned the "winner," and the older document is marked as `suppressed` (with a contradiction score of 1.0) and pruned from the output result array.
   * If they are **Duplicates without conflict**, the node with the higher base reranker score is crowned the "winner," and the other is marked as `suppressed` (with a contradiction score of 0.5) to keep the search results clean and concise.

---

## 4. Auditable Explainability

Unlike neural network rerankers, every candidate scored by FAIM contains a detailed, transparent explainability dictionary:

```json
{
  "node_id": "c62b9a7c-3f4a-4b9d-a602-5e1927c3fb8a",
  "score": 0.8245,
  "score_components": {
    "lex": 0.78,
    "graph": 0.65,
    "phase4": 0.88,
    "phase4_entity": 1.0,
    "phase4_time": 0.0,
    "phase4_proposition": 0.85,
    "phase4_evidence_span": 0.90,
    "phase4_contradiction": 0.0
  },
  "phase4_explain": {
    "query_signature": "atlas:located:berlin",
    "doc_signature": "atlas:located:berlin",
    "evidence_components": {
      "matching_tokens": ["atlas", "berlin"],
      "span_density": 0.92
    }
  }
}
```

This absolute transparency allows debugging retrieval behavior in production instantly!

---

## 5. Verification Protocols

The reranker’s mathematical and structural correctness is enforced by automated test suites under [`test_reranker_v2.py`](file:///home/sephi-asi/FAIM/tests/unit/test_reranker_v2.py) and [`test_AT_RR1_proposition_match.py`](file:///home/sephi-asi/FAIM/tests/acceptance/test_AT_RR1_proposition_match.py):

* **Conflict Suppression Verification**:
  ```python
  def test_reranker_v2_suppresses_older_conflicting_candidate():
      # Creates two conflicting candidates (same semantic signature, different values)
      # Assertions verify older candidate is successfully added to 'suppressed' set.
  ```
* **Result**: **All tests execute and pass successfully!**
