# 69 - FAIM Cortex: 24-Hop Adaptive Reasoning Spec

## 1. Executive Summary
The FAIM Cortex reasoning engine implements a **24-Hop Bounded Diffusion** strategy. Unlike traditional LLMs that rely on a linear token sequence, FAIM navigates graph-based memories to extract structured reasoning paths. The reasoning depth is fully adaptive, ranging from 1 to 24 hops based on the complexity of the input and the density of the retrieved memory clusters.

## 2. Why 24 Hops? (The Philosophy of Depth)
Traditional "Chain of Thought" reasoning is often shallow or prone to drift. The 24-hop limit exists to ensure **Logical Integrity** while allowing for deep causal traceback.
- **Not Random**: Every hop is a deterministic traversal through the **1M+ Semantic Registry**.
- **Causal Binding**: Hops are connected through typed edges, ensuring that the reasoning path is grounded in actual relations within the FAIM memory graph.
- **Bounded Diffusion**: We prevent "infinite loops" or "hallucination drift" by capping the search at 24 nodes, which represents the maximum complexity of an enterprise-grade semantic task.

## 3. Implementation Details (File Paths)
The core logic for the 24-hop traversal and semantic binding is integrated across the following surfaces:
- **Enhanced Planner**: `faim_native/core/cortex/planner_enhanced.py` (Calculates query complexity, configures `enable_multi_hop`, and sets `max_hops` dynamically).
- **Runtime Execution**: `faim_native/core/cortex/runtime.py` (Routes the query through the EnhancedPlanner to execute the multi-hop strategy).
- **UI Feedback**: `frontend/src/contexts/ChatContext.tsx` (Propagates the `activeReasoningPath` to the FIG View).

## 4. Intelligence Properties
- **Fully Adaptive**: The system evaluates uncertainty at each step. If uncertainty is low, it terminates in 1-3 hops. If high, it digs up to 24 hops.
- **Deterministic**: The same input and same memory state will always produce the same reasoning path.
- **Honesty**: If a solution isn't found within 24 hops, the system admits missing information rather than hallucinating an answer.

---
*Status: Production Stable*


## Detailed Explanations & Scenario Analysis

### Why is this feature here?
Traditional LLMs hallucinate because they predict the next likely word without verifying its physical or logical existence. The 24-Hop engine solves this by strictly traversing the actual connected nodes in the FAIM memory graph. The 24-hop limit guarantees sufficient depth to solve complex enterprise problems while enforcing a hard boundary against infinite loops.

### How it works in any scenario
Scenario: "Trace the impact of changing the 'PaymentService' API."
The engine starts at the `PaymentService` node (Hop 1). It traverses `IMPORTS` edges to find `CheckoutController` (Hop 2), then to `FrontendCart` (Hop 3). The `EnhancedPlanner` dynamically evaluates the complexity and continues traversing up to 24 hops to map out every downstream dependency before synthesizing the answer. 

### Comparisons & Differences
Unlike standard "Vector Similarity Search" (which just finds documents with similar words), the 24-hop engine is a true "Graph Traversal". Similarity search might return an unrelated payment system; 24-hop reasoning guarantees a direct causal link between the starting node and the discovered nodes.

### Why it is unique and useful
It provides "Causal Fidelity". The user isn't just given an answer; they are given the exact sequence of 24 logical steps the AI took to arrive there, which can be visualized perfectly in the FIG View.

### Future Scenarios
As the FAIM graph grows to millions of nodes, the 24-hop engine will be optimized with heuristic pruning (A* search across the graph) to find the most relevant causal paths even faster, acting as the foundation for autonomous system debugging.
