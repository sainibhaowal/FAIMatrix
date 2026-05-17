# 84. FAIM Canonical Semantics Pipeline

This document provides the formal architectural and mathematical specification for the **Canonical Semantics Pipeline** inside the **Fractal Antisymmetric Inheritance Memory (FAIM)**. It outlines the deterministic algorithms used to map varied textual expressions onto stable semantic structures, resolve abbreviation gaps, and construct high-fidelity graph edges without using stochastic neural network models.

---

## 1. Architectural Overview & Design Tenets

In unstructured corpora, identical concepts are represented using highly diverse textual variants (e.g., synonyms, acronyms, and grammatical inflections). Traditional retrieval systems try to bridge this gap using heavy, learned, deep cross-encoders or embeddings models, which introduces:
* High computational latency and VRAM footprint.
* Stochastic drift (non-deterministic results).
* Lack of auditability.

**FAIM Canonical Semantics** resolves this by separating semantic mapping into two highly optimized, deterministic layers:
1. **The Broadener Layer (Pre-Processing)**: Extends individual word tokens using pre-compiled synonym and abbreviation mappings (ConceptNet 8M+ and the local Entity Alias table).
2. **The Mining Layer (Self-Evolution)**: Analyzes co-occurrence counts across the active database to mathematically derive new, domain-specific synonym and phrase mappings, materializing them directly as structured graph edges.

```
       [ Input Text ] -> [ NFC Norm & Whitespace Collapse ]
                                     |
                                     v
                       [ Entity Alias Expansion ]
                                     |
                                     v
                       [ ConceptNet Broadener ]
                                     |
                                     v
                       [ Rule-Based Porter Stemmer ]
                                     |
                                     v
                      [ Canonical Document Format ]
                                     |
                  +------------------+------------------+
                  |                                     |
                  v                                     v
       [ PMI & Context Mining ]              [ Phrase Pattern Mapping ]
                  |                                     |
                  +------------------+------------------+
                                     |
                                     v
                    [ Edge Materialization in Graph ]
                    (distributional_synonym & paraphrase)
```

---

## 2. Pre-Processing & Normalization

The normalization pipeline guarantees that textual input is completely standardized before hashing or graphing.

### 2.1 Unicode and Whitespace Standardization
Every input string is subjected to strict **Unicode NFC Normalization** and white-space collapsing:
$$\text{normalize}(T) = \text{RegExReplace}(\text{NFC}(T), \text{pattern}=\text{whitespace}, \text{repl}=\text{" "})$$

### 2.2 Acronym & Alias Mapping
To bridge abbreviation gaps, a static hash lookup table expands domain acronyms to their full-text expressions before further processing:
```python
_ENTITY_ALIASES = {
    "llm": "large language model",
    "rag": "retrieval augmented generation",
    "nyc": "new york city",
    "ai": "artificial intelligence",
}
```
If token $t \in \text{Keys}(\_ENTITY\_ALIASES)$, it is replaced by its associated string value.

### 2.3 Rule-Based Lemmatization (Porter Stemming)
Words are reduced to their base morphological stems using the fully deterministic, rule-based **Porter Stemmer** ([`porter_stemmer.py`](file:///home/sephi-asi/FAIM/faim_native/encoding/porter_stemmer.py)). This maps suffixes and plurals (e.g., `"connections"`, `"connecting"`, `"connected"` $\to$ `"connect"`) completely algorithmically, executing in microseconds with **$100\%$ consistency** across executions.

---

## 3. ConceptNet 8M+ Omni-Lexicon Expansion

To address global vocabulary mismatches, FAIM incorporates an embedded, highly optimized lexical database built from **ConceptNet 5.7.0** containing over **$8\text{,000,000}+$ semantic edges** across **$2\text{,172,991}$ unique words**.

### 3.1 Gzip Lexicon Compression
To prevent packaging gigabytes of database files, the builder ([`conceptnet_builder.py`](file:///home/sephi-asi/FAIM/faim_native/lexical/conceptnet_builder.py)) streams the assertions from S3, filters bi-directional links of type `/r/Synonym`, `/r/FormOf`, and `/r/RelatedTo`, and serializes the result into a compressed gzip JSON file ([`conceptnet_synonyms.json.gz`](file:///home/sephi-asi/FAIM/faim_native/lexical/data/conceptnet_synonyms.json.gz)).

### 3.2 Thread-Safe $O(1)$ Lookup
During query-time tokenization, the expander ([`synonym_expander.py`](file:///home/sephi-asi/FAIM/faim_native/lexical/synonym_expander.py)) loads the dictionary into a thread-safe singleton. For each token in the query:
1. The token is looked up in the hash map.
2. If synonyms exist, they are sorted **alphabetically** to guarantee absolute sorting determinism and prevent ties.
3. The top $N$ synonyms (capped at 5 to prevent over-expansion) are appended directly behind the original token in the text stream:
   $$T_{\text{expanded}} = [t_1, s_{1,1}, s_{1,2}, \dots, t_2, s_{2,1}, \dots]$$

---

## 4. Corpus-Derived PMI & Context Overlap Mining

During background self-evolution turns, FAIM extracts **domain-specific and contextual synonyms** from the active document corpus. This operates purely on mathematical metrics derived from document frequencies.

### 4.1 Pointwise Mutual Information (PMI)
For any pair of terms $(a, b)$ that co-occur in the corpus, the Pointwise Mutual Information measures their associative strength:
$$\text{PMI}(a, b) = \log \left( \frac{(C(a, b) + \epsilon) \cdot N}{(C(a) + \epsilon) \cdot (C(b) + \epsilon)} \right)$$
Where:
* $C(a, b)$ is the document support count (number of documents containing both terms).
* $C(a)$ and $C(b)$ are individual document frequencies (DF).
* $N$ is the total document count in the corpus.
* $\epsilon = 10^{-9}$ is the numerical stabilizer.

To qualify as a synonym candidate, the pair must meet a strict threshold:
$$\text{PMI}(a, b) \ge \text{MIN\_PMI} \quad (0.10)$$

### 4.2 Context Overlap (Jaccard Similarity)
In addition to co-occurrence, the context environments surrounding each term must be highly similar. The top 24 context terms (excluding stopwords) for each word are gathered into sets $S_a$ and $S_b$. Their overlap is evaluated using Jaccard Similarity:
$$\text{Overlap}(a, b) = \frac{|S_a \cap S_b|}{|S_a \cup S_b|}$$
The pair is rejected if the overlap falls below the threshold:
$$\text{Overlap}(a, b) \ge \text{MIN\_CONTEXT\_OVERLAP} \quad (0.35)$$

### 4.3 Deterministic Canonical Selection
To merge synonym variants under a unified form, one term is selected as the **Canonical Form** and the other as the **Surface Form** based on their corpus prevalence:
$$\text{Canonical}(a, b) = \begin{cases} 
a & \text{if } C(a) > C(b) \\
b & \text{if } C(b) > C(a) \\
\min(a, b) & \text{if } C(a) = C(b) \quad (\text{lexicographical tie-breaker})
\end{cases}$$
The surface variant is mapped to this canonical term with a unified score:
$$\text{Score}(a, b) = \frac{\min(1.0, \text{PMI}/1.25) + \text{Overlap} + \min(1.0, C(a,b)/C(\text{surface}))}{3}$$

---

## 5. Dynamic Graph Semantic Edge Materialization

Once synonyms and phrases are mined, they are turned into structured relationship links within the database.

```
       [ Document A ]                      [ Document B ]
    "Atlas resides in Berlin"          "Atlas lives in Berlin"
           |                                     |
           +-----------------+-------------------+
                             |
                   [ Mined Paraphrase ]
             "resides in" <-> "rel:located_in"
                             |
                             v
           [ Materialized SQL Semantic Edge ]
            (kind = "paraphrase", weight = 0.72)
```

### 5.1 Edge Construction
Two documents containing different lexical variants of a canonical synonym are linked with an edge:
* **`distributional_synonym`**: Linked if they share a mined contextual synonym relationship. The semantic edge weight scales deterministically with evidence support:
  $$\text{Weight} = \min(0.85, 0.60 + 0.08 \cdot C(a, b))$$
* **`paraphrase`**: Linked if they share a mapped phrase pattern (e.g., `"resides in"` and `"lives in"` both mapping to the canonical `"rel:located_in"`). The weight is computed as:
  $$\text{Weight} = \min(0.82, 0.62 + 0.10 \cdot C(a, b))$$

These materialized edges are written directly to the `edges` table, allowing them to be loaded instantly into active VRAM during retrieval queries.

---

## 6. Execution Flow & Verification

The lexical pipeline’s robustness is verified through direct, deterministic unit tests under [`test_canonical_semantics.py`](file:///home/sephi-asi/FAIM/tests/unit/test_canonical_semantics.py):

```python
def test_build_canonical_semantics_mines_distributional_and_paraphrase_edges():
    docs = [
        _doc("Atlas resides in Berlin. Revenue growth improved this quarter."),
        _doc("Atlas lives in Berlin. Sales growth improved this quarter."),
        _doc("Revenue sales margin improved this quarter."),
    ]
    build = build_canonical_semantics(docs)
    
    # Assertions verify co-occurrence maps are derived deterministically
    assert ("sale", "revenue", "distributional_synonym") in lexicon_keys
    assert ("resides in", "rel:located_in", "phrase_pattern") in lexicon_keys
```

Because these components operate on pure, discrete, mathematical equations and discrete lookups, they are completely immune to neural network hallucinations, consume a tiny fraction of the system memory, and return identical results every single time.
