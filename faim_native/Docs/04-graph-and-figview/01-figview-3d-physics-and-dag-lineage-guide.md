# FigView 3D Force Physics & Lineage DAG Cycle Guard Guide

## 1. Scope
Documents how 3D interactive stretching and Lineage DAG rendering stay geometrically stable and crash-free in:
- **Canvas Component**: `frontend/src/components/graph/FigCanvas.tsx`
- **Physics & Layout Helpers**: `frontend/src/lib/figViewLayout.ts`

---

## 2. Deterministic Bounded 3D Layout Physics (`figViewLayout.ts` & `FigCanvas.tsx`)
### Failure mode addressed
Standard D3-force 3D uses a global centroid `center` force (`d3Force("center")`). When a user drags and stretches a single node far from the cloud, D3 shifts all unpinned nodes opposite the dragged node to keep the combined center of mass fixed, making the rest of the atom cluster fly away off-screen.

### Implemented Physics Architecture
1. **Per-Node Elastic Gravity (`createElasticGravityForce`)**:
   - `applyLayout(...)` disables D3's global centroid-shifting `center` force via `fg.d3Force("center", null)` and replaces it with `fg.d3Force("gravity", createElasticGravityForce(config.centerStrength, 180))`.
   - `createElasticGravityForce` pulls each unpinned node (`n.fx == null && n.fy == null && n.fz == null`) independently toward the origin `(0, 0, 0)` proportional to `centerStrength * 0.12 * alpha`, and clamps any unpinned drift beyond `maxRadius = 180` while damping velocity (`vx *= 0.5`).
   - Because each node's tether references the fixed origin rather than the ensemble centroid, dragging one node never shifts other atoms.
2. **Bounded Drag Clamping (`clampDraggedNode`)**:
   - During node drag, `clampDraggedNode(node, maxRadius = 160)` keeps the dragged node's `x/y/z` and pinned `fx/fy/fz` coordinates inside a `160`-unit sphere so extreme pointer pulls cannot explode connected edge springs.
3. **Isolated Drag Pinning & Charge Distance Cap**:
   - `charge.distanceMax(160)` bounds long-range Coulomb repulsion.
   - `onNodeDrag` pins only the active node (`fx/fy/fz`); releasing or resetting clears pins cleanly so the graph relaxes without oscillation.

---

## 3. Lineage DAG Cycle & Self-Loop Sanitizer (`filterAcyclicEdges`)
### Failure mode addressed
In `lineage` mode (`topMode === "lineage"` → `dagMode="td"`), semantic graphs legitimately contain bidirectional associations, evolution echoes, or self-referential provenance links. Passing cyclic edges to `react-force-graph-3d` triggers a fatal runtime exception:
> `Uncaught Invalid DAG structure! Found cycle in node path: <uuid> -> <uuid>`

### Implemented Graph Sanitizer (`FigCanvas.tsx`)
`filterAcyclicEdges(edges: FigEdge[])` enforces strict DAG invariants before calling `toGraphData(...)` whenever `isDagMode` (`topMode === "lineage" || config.dagMode !== null`) is active:
1. **Priority Sorting**: Sorts candidate edges deterministically with `inheritance` highest priority (`0`), `hypernym` second (`1`), all other kinds (`2`), descending `weight`, then ascending `edge_id`.
2. **Self-Loop Elimination**: Drops any edge where `e.src_node_id === e.dst_node_id`.
3. **Pairwise Deduplication**: Tracks `${src_node_id}\0${dst_node_id}` in `seenPairs` so parallel edges between the same endpoints are skipped.
4. **Reachability Cycle Guard (`isNodeReachable`)**: Before adding `src -> dst` to the kept DAG adjacency map `adj`, runs BFS/DFS reachability `isNodeReachable(adj, e.dst_node_id, e.src_node_id)`. If `src` is already reachable from `dst`, keeping `src -> dst` would close a cycle, so the back-edge is safely omitted from DAG layout rendering while higher-priority structural inheritance links are preserved.
