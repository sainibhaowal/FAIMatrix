# 78 - FAIM ConceptNet and Semantic Registry Runtime Guide

## 1. Executive Summary
FAIM now uses **three distinct semantic layers** that should not be confused:

1. **ConceptNet archive**
   - large lexical broadener
2. **Semantic registry runtime**
   - combined query-time semantic lookup layer
3. **Deterministic Cortex router**
   - small task classifier for reasoning mode selection

The older description of a single `1M+ semantic registry` acting as the router
was inaccurate. The new architecture is clearer and stronger.

## 2. Real components and file paths
- **ConceptNet broadener**
  - [synonym_expander.py](/home/sephi-asi/FAIM/faim_native/lexical/synonym_expander.py)
  - [conceptnet_synonyms.json.gz](/home/sephi-asi/FAIM/faim_native/lexical/data/conceptnet_synonyms.json.gz)
- **Semantic registry runtime**
  - [semantic_registry.py](/home/sephi-asi/FAIM/faim_native/lexical/semantic_registry.py)
  - live query integration in [query_flow.py](/home/sephi-asi/FAIM/faim_native/orchestration/query_flow.py)
- **Deterministic Cortex router**
  - [semantics.py](/home/sephi-asi/FAIM/faim_native/core/cortex/semantics.py)

## 3. What each layer does

### ConceptNet
Purpose:
- global lexical broadening
- synonym and phrase expansion
- better fuzzy recall before scoring

Real shipped size:
- `2,172,991` synonym keys
- `3,504,828` synonym edges

### Semantic registry runtime
Purpose:
- combine ConceptNet, static multilingual lexicon surfaces, and graph-local
  canonical / multilingual / domain-memory lexicons into one deterministic
  runtime lookup layer

Real shipped base:
- `2,172,991` ConceptNet terms
- about `146,598` static multilingual lexicon surfaces
- about `2,319,589` shipped semantic registry terms before graph-local growth

### Deterministic Cortex router
Purpose:
- classify the turn into a small number of reasoning task types such as
  contradiction, timeline, compare, provenance, predict, and investigate

This router is compact, not multi-million.

## 4. Example flow
Scenario:
`Locate discrepancies in the residing server logs`

1. **ConceptNet broadening**
   - broadens `residing` toward nearby lexical variants
2. **Semantic registry runtime**
   - merges canonical, multilingual, and domain-memory surfaces with the same
     query so recall improves across alias and graph-learned vocabulary
3. **Cortex router**
   - maps contradiction-style language toward the contradiction task mode
4. **Retrieval + hops**
   - FAIM recalls, reranks, and traverses bounded graph paths

## 5. Comparisons
| Layer | Real size | Purpose | Phase |
|---|---:|---|---|
| ConceptNet archive | 2,172,991 terms | lexical broadening | pre-retrieval |
| Semantic registry runtime | 2.31M+ shipped base, plus graph-local rows | combined semantic lookup and expansion | query expansion |
| Cortex router | small seeded alias map | task routing | Cortex mode selection |

## 6. Truthful claims
You can truthfully say:
- FAIM uses a **2.31M+ shipped semantic registry term base**
- FAIM uses a **ConceptNet-scale lexical broadener**
- FAIM uses a **small deterministic Cortex router**

Do not say:
- `the router itself is 1M+ concepts`
- `the registry is only en_de_lexicon.tsv`
- `the registry is a fixed 1,048,576-node ontology`

---
*Status: Implemented and clarified*
*Architecture: ConceptNet broadener + semantic registry runtime + Cortex router*
