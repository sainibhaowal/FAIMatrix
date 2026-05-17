# 71 - FAIM FIG View: Cognitive Overlays & Neural Pulse Trace

## 1. The FIG View (Federated Intelligence Graph)
The FIG View is the 3D visual engine of FAIM. It doesn't just show "data"; it visualizes the **live thinking process** of the Cortex.

## 2. Neural Pulse Trace
As the 24-Hop Engine digs through memories, it generates a **Neural Pulse Trace**.
- **Real-Time Coupling**: Each "hop" in the reasoning process triggers a visual pulse in the 3D graph.
- **Path Highlighting**: The specific nodes involved in the current reasoning path are highlighted in **Amber/Emerald** to show the "ground truth" of the answer.
- **Diffusion Visualization**: Users can see the "Reasoning Ripple" as the system moves from the initial query node to the final 24th node.

## 3. Cognitive Overlays
The FIG View includes 6 specialized "Overlay" modes that change the visual coloring of the graph based on the cognitive lens:
- **None**: Standard structure.
- **Cognitive**: Highlights nodes based on their 1M+ Semantic Registry classification.
- **Retrieval**: Shows nodes currently being read into the `MemoryRefSet`.
- **Evolution**: Visualizes nodes that have changed or evolved over time (State Delta).
- **Temporal**: Colors the graph based on the `createdAt` timestamp (Past to Present).
- **Causality**: Highlights the `CAUSES`, `BLOCKS`, and `ENABLES` edges.

## 4. UI Discoverability
- **The Intelligence Sidebar**: Found on the right side of the Memory Query page.
- **Overlay Selector**: A floating control at the bottom of the FIG View allows one-click switching between these cognitive perspectives.
- **Node Inspector**: Clicking a node during a Neural Pulse shows exactly why that node was selected for the current "Hop".

## 5. Technical Implementation
- **Visual Engine**: Three.js / React Three Fiber.
- **Pulse Trigger**: Event-driven from `ChatContext.tsx` whenever a `activeReasoningPath` is received.
- **Overlay Math**: Applied via custom shaders in the `FigNodeMaterial`.

---
*Status: Integrated*
*Modes: 6 Cognitive Layers*


## Detailed Explanations & Scenario Analysis

### Why is this feature here?
Humans struggle to comprehend complex, non-linear data structures. The FIG View and its Neural Pulse Trace exist to translate the AI's internal, invisible graph traversals into an intuitive, 3D visual language. It proves the AI is actually doing work, rather than just generating text.

### How it works in any scenario
Scenario: Auditing a complex causal chain.
A user selects the `Causality` overlay. The graph instantly recolors to highlight only `CAUSES`, `BLOCKS`, and `ENABLES` edges. As the user asks a question, the `Neural Pulse Trace` fires, sending an Amber visual pulse jumping from node to node, tracing the exact path the AI is searching in real-time. 

### Comparisons & Differences
Most chat interfaces are simple "text-in, text-out". Even advanced ones might show a static 2D flowchart. The FIG View is a living, breathing 3D environment. The "Neural Pulse" isn't a pre-rendered animation; it is physically coupled to the backend's real-time JSON response stream of active reasoning paths.

### Why it is unique and useful
It builds unprecedented trust. When users can literally *watch* the AI search through their data, verifying each connection visually, the fear of "hallucination" vanishes. The cognitive overlays allow users to instantly switch their context from "Time-based" (Temporal) to "Logic-based" (Causality).

### Future Scenarios
The FIG view will expand to support VR/Spatial computing, allowing enterprise architects to physically "walk through" the federated intelligence graph, manipulating nodes and observing neural pulses with their hands.
