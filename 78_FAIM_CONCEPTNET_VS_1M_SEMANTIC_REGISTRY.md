# 78 - FAIM: ConceptNet 8M+ Omni-Lexicon vs. 1M+ Semantic Registry

## 1. Executive Summary
FAIM utilizes two distinct lexical systems at unprecedented enterprise scales to achieve deterministic intelligence: **ConceptNet Omni-Lexicon Expansion** (2.1M+ unique words, sourced from 8M+ edges) and the **1M+ Semantic Registry** (~1.02M concepts). While they sound similar, they serve entirely different architectural purposes. ConceptNet acts as a **Global Query Broadener**, while the 1M+ Registry acts as a **Cognitive Router**.

## 2. Core Components & File Paths
- **ConceptNet Expansion**: `faim_native/lexical/synonym_expander.py` (Powered by embedded `conceptnet_synonyms.json.gz`).
- **1M+ Registry**: `faim_native/lexical/data/en_de_lexicon.tsv` (Powered by the Cortex intent mapping system).

## Detailed Explanations & Scenario Analysis

### Why are these features here?
- **ConceptNet (8M+ Edges)** is here to solve the "Global Vocabulary Gap". We outgrew WordNet (119k words) because it lacked scale. By upgrading to ConceptNet, if a user searches for "automobile" or even a slang/foreign term, the query is expanded globally so we never miss a graph edge.
- **1M+ Registry** is here to solve the "Intent Routing Gap". It maps a complex phrase to a fixed mathematical concept (like `CONTRADICTION` or `CAUSALITY`) so the Cortex Engine knows which 24-hop branch to execute.

### How it works in any scenario
**Scenario: A user asks, "Locate the discrepancies in the residing server logs."**

1. **Step 1: ConceptNet Omni-Lexicon Expansion (The Broadener)**
   - The engine sees the word "residing".
   - `synonym_expander.py` checks the massive 11.9MB compressed dictionary and expands it: `"residing" -> ["dwelling", "living", "existing"]`. 
   - *Result*: The query is enriched across potentially millions of linguistic variations so the search engine won't miss a memory just because it used a different adjective.

2. **Step 2: 1M+ Semantic Registry (The Router)**
   - The expanded query is hashed against the 1.02M concept registry.
   - The registry detects the cluster for "discrepancies/conflicts" and maps the *entire intent* to the mathematical concept of `CONTRADICTION`.
   - *Result*: The `Cortex Auto` mode instantly switches to the **Contradiction Branch** and begins a 24-hop traceback to find the conflicting server logs.

### Comparisons & Differences
| Feature | Size | Purpose | Execution Phase | What it does |
| :--- | :--- | :--- | :--- | :--- |
| **ConceptNet Lexicon** | 2.1M+ words (from 8M+ edges) | Global Lexical Flexibility | Pre-Processing | Changes "car" to "car OR automobile OR auto" |
| **1M+ Registry** | 1,048,576 concepts | Cognitive Routing | Intent Classification | Changes "Why did it crash?" to `CAUSALITY` |

### Why it is unique and useful
By splitting these two tasks and scaling them to the millions, FAIM achieves something standard AI models cannot. Standard LLMs mash vocabulary and intent together into a giant, slow neural network. FAIM handles vocabulary bridging via a highly compressed $O(1)$ JSON dictionary (ConceptNet), and handles intent routing via a massive $O(1)$ Hash table (1M+ Registry). This separation of concerns is what gives FAIM its sub-10ms response times while retaining a massive global vocabulary.

### Future Scenarios
In the future, the ConceptNet dictionary will be dynamically updated with internal enterprise jargon (e.g., expanding "K8s" to "Kubernetes"). Meanwhile, the 1M+ Registry will be expanded to support physical robot intent classification, where a command like "clean up" maps directly to a 3D spatial concept, triggering a spatial reasoning branch rather than a text branch.

---
*Status: Production Stable (Upgraded from WordNet)*
*Architecture: Dual-Layer Massive Lexical Resolution*
