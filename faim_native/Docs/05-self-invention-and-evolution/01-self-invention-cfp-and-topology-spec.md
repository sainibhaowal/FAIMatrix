# Self-Invention CFP Mathematics, Lineage Topology & Symbolic Theory Spec

## 1. Scope
Documents the autonomous self-invention engine, Coefficient of Fractional Parentage (CFP) synthesis weights, symbolic theory DAG conduits, and 2.5D UI topology across:
- **Invention Core**: `faim_native/core/dynamics/invention_native.py`
- **Evolution Dynamics**: `faim_native/core/dynamics/evolution_native.py`
- **Evolution Orchestrator**: `faim_native/orchestration/evolve_flow.py`
- **Node & Theory Persistence**: `faim_native/store/pg/repos/node_repo.py`, `faim_native/store/pg/repos/theory_repo.py`
- **API Surface**: `faim_native/api/routers/evolve.py` (`GET /api/v1/evolve/invention/flow`, `POST /api/v1/evolve`)
- **2.5D UI Canvas**: `frontend/src/components/evolution/InventionFlowCanvas.tsx`, `frontend/src/app/(admin)/dashboard/evolution/page.tsx`

---

## 2. Coefficient of Fractional Parentage (CFP) Macro Synthesis

### Activation Gating (`should_invent` & `self_invent_requested`)
Macro creation runs deterministically inside `invent_macro(...)` and `run_invention_cycle(...)` / `run_synthesis_invention_cycle(...)`:
- Explicit user triggers (`Synthesize & Evolve`, `self_invent_requested=True`) and policy-enabled evolution cycles evaluate coactivation sets (`find_coactivation_sets`), semantic clusters, and emergent theories.
- Conditions check minimum evolution pressure ($\hat{\lambda} \ge \lambda_{\text{threshold}}$), minimum coactivation count ($c \ge c_{\min}$), and cosine redundancy reduction ($\Delta R \ge \Delta R_{\min}$), with bounded cycle creation.

### Vector Composition, Residuals & CFP Weights (`invent_macro`)
Given $K \ge 2$ constituent member nodes $\{n_1, \dots, n_K\}$ with vectors $\mathbf{v}_i$ and touch counts $m_i = \max(1, \text{touch\_count}(n_i))$:
1. **Macro Vector**: $\bar{\mathbf{v}} = \text{normalize}\!\left(\frac{1}{K}\sum_{i=1}^K \mathbf{v}_i\right)$.
2. **Cosine Similarity & Residual**:
   $$s_i = \cos(\bar{\mathbf{v}}, \mathbf{v}_i), \qquad r_{\text{macro}} = \operatorname{clamp}\!\left(1 - \frac{1}{K}\sum_{i=1}^K s_i,\; 0.08,\; 0.85\right)$$
3. **Normalized CFP Weights**:
   $$w_i^{\text{raw}} = m_i \cdot \max(0.05, s_i), \qquad w_i = \frac{w_i^{\text{raw}}}{\sum_{j=1}^K w_j^{\text{raw}}}$$
   Stored inside `opp_signature["weights"]` keyed by `str(node_id)` so every macro retains an exact normalized partition of unity over its constituents.
4. **Human-Readable Metadata & Representation Sidecar**:
   - `_derive_member_labels` constructs concise `Macro: A ⊗ B ⊗ C` titles (`opp_signature["title"]`) and `summary` strings including level $L = 1 + \max_i \text{level}(n_i)$ and CFP weight previews.
   - Persists a `NodeRepresentationV2Model` sidecar row for search and UI display.
   - `NodeRepo.list_macros(graph_id, limit)` queries `level >= 1` (`macro_count` via `NodeRepo.count_macros`), ensuring L1, L2, and higher-order abstractions are surfaced reliably.

---

## 3. Three-Stage Invention Topology (`/api/v1/evolve/invention/flow`)

`_build_invention_flow` (`evolve.py`) returns `InventionFlowResponse`:
- **`stages.atoms` (Stage 1)**: Active base knowledge atoms (`level == 0`) with `cognitive_type`, text snippet, and status.
- **`stages.macros` (Stage 2A)**: Synthesized macro abstractions (`level >= 1`) with `children_details` (parent `id`, `label`, `type`, `similarity`), `weights` (CFP map), `residual`, `synthesis_origin`, `summary`, and `level`.
- **`theories` (Stage 2B)**: Active rows from `TheoryRepo` (`InventionFlowTheoryItem`) carrying `theory_id`, `theory_type`, `title`, `description`, `confidence`, `graph_version`, and `evidence_node_ids`.
- **`stages.merges` (Stage 3)**: Antisymmetric opposition merges (`EdgeRepo.list_opposition_edges`) with full `MergeDecision` verdicts (`selector`, `score_winner`, `score_loser`, `tie_break`, `components_winner`) and winner/pruned status.
- **`edges` (`InventionFlowEdgeItem[]`)**: Explicit directed lineage conduits connecting the 3 stages:
  - `atom_to_macro` (weighted by CFP contribution)
  - `atom_to_theory` (linking evidence atoms to symbolic theories)
  - `macro_to_merge` & `atom_to_merge` (linking winning/merged nodes into Stage 3 opposition verdicts)
- **`eval_metrics`**: Live `d_hat`, `h_hat`, `lambda_hat`, `redundancy_r`, `novelty_n`, `energy_e`, `compression_ratio_cr`, `macro_absorption_rate`, `merge_consensus_score`, `theory_confidence_mean`, `connected_edge_count`, and `last_event_seq`.

---

## 4. 2.5D Invention Topology Canvas (`InventionFlowCanvas.tsx`)
- **Evaluation Telemetry Ribbon**: Displays live `SSE LIVE` indicator, topological metrics ($\hat{D}, \hat{H}, \hat{\lambda}, R, N, CR$), Macro Absorption, Merge Consensus, and Mean Theory Confidence.
- **Direct Synthesis Trigger**: `Synthesize & Evolve` button triggers `POST /api/v1/evolve` (`triggerSynthesizeEvolve`) and streams updated nodes/edges automatically.
- **DOM-Measured Cubic Bezier SVG Overlay**: Dynamically measures Stage 1 → Stage 2 → Stage 3 card anchors to draw smooth gradient Bezier curves with CFP weight badges, plus full upstream/downstream lineage path highlighting on hover or selection.
- **Slide-Over Inspector Drawer**: Displays constituent parent breakdown, CFP percentages, `MergeDecision` score vectors, and theory evidence links.
