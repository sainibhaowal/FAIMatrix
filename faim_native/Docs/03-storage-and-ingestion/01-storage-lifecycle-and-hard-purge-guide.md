# Storage Lifecycle, Queue Controls & Transactional Hard Purge Guide

## 1. Scope
Documents the live storage upload queue, rate-limit resilience, job cancellation controls, and cross-store hard purge semantics implemented across:
- **Frontend UI**: `frontend/src/app/(admin)/dashboard/storage/page.tsx`
- **Backend Storage Router**: `faim_native/api/routers/storage.py`
- **Rate Limiter**: `faim_native/api/middleware/ratelimit.py`
- **Relational Cleanup Helpers**: `faim_native/store/pg/graph_cleanup.py` (`purge_graph_artifacts_for_raw_ids`)
- **Vector Index Cleanup**: `faim_native/index/qdrant_index.py` (`FAIMIndex.remove`, `FAIMIndex.delete_graph`, `_ensured_collections`)

---

## 2. Upload Queue and Monotonic Progress Reporting
### Failure mode addressed
Previously, concurrent uploads triggered parallel per-job `/api/v1/storage/uploads/{job_id}` and `/events` polling loops, leading to `429 Too Many Requests` errors and progress bars jumping backward or flickering when transient responses lagged behind client XHR byte counts.

### Live Behavior
- **Monotonic Progress Clamping**: Upload item state transitions clamp progress with `Math.max(item.progress, ...)`:
  - Queue start (`5%`), XHR upload transfer (`5%..35%` → `40%` on transfer completion), worker ingest (`Math.max(40, queueProgress(nextStatus))`), and terminal completion (`100%`).
  - Progress bars never jump backward on delayed polls or retry backoffs.
- **429 Backoff & Polling Consolidation**:
  - `ApiError` with `status === 429` sets a non-destructive UI backoff indicator instead of resetting card progress or spamming immediate retries.
  - Real-time SSE events (`connectSse` on `/api/v1/stream`) advance `lastEventSeq` monotonically and trigger coordinated status refreshes.
- **Per-Item Cancellation & Queue Clearing**:
  - **Cancel Active Upload / Job**: Calls `POST /api/v1/storage/uploads/{job_id}/cancel` (`cancel_upload_job`), marking `jobs.cancel_requested` so running workers stop safely at phase checkpoints (`_job_cancel_requested`).
  - **Remove / Clear Queue Items**: Allows removing finished, failed, or cancelled items from the UI queue without altering persisted records unless Delete is requested.

---

## 3. Transactional Physical Hard Purge (`hard_delete=True`)
### API Surface
- **Single File Delete**: `DELETE /api/v1/storage/files/{raw_id}?graph_id=...&hard_delete=true` (`request_delete_storage_file`)
- **Batch Delete**: `POST /api/v1/storage/files/bulk-delete` (`bulk_delete_storage_files`, up to `500` `raw_id` entries)

### Cross-Store Cleanup Order (`request_delete_storage_file` & `_reconcile_graph_after_file_cleanup`)
1. **Job Cancellation**: If `row.last_job_id` exists, `JobStore.request_cancel(...)` aborts any in-flight worker activity for the raw file.
2. **Encrypted Raw Blob Removal**: Resolves `_resolve_raw_store(ctx)` and deletes the physical encrypted blob on disk (`/var/lib/faim/raw/blobs`) plus the `RawRefModel` metadata row.
3. **Atomic Relational Graph Purge (`purge_graph_artifacts_for_raw_ids`)**:
   - Resolves all `node_id` values belonging to `(tenant_id, graph_id, raw_id)`.
   - Deletes all touching `edges` (`src_node_id IN ids OR dst_node_id IN ids`) so zero dangling edges remain.
   - Removes `coactivations` referencing any deleted `node_id`.
   - Removes `node_repr_v2` (`NodeRepresentationV2Model`) rows and `nodes` rows.
   - Removes the `storage_files` (`StorageFileModel`) catalog record.
4. **Orphan Sweep & Empty-Graph Reconciliation (`_reconcile_graph_after_file_cleanup`)**:
   - Sweeps any remaining `nodes` whose `raw_id` no longer exists in `storage_files`.
   - When `remaining_files == 0` or `remaining_nodes == 0`, clears residual `EdgeModel`, `CoactivationModel`, `NodeRepresentationV2Model`, `NodeModel`, `GraphDomainLexiconModel`, and `GraphKBSourceModel` rows.
   - Refreshes `GraphDiagnosticsCacheModel` immediately when `remaining_nodes <= 500`, or invalidates stale cached diagnostics on larger graphs.
5. **Audit Trail**: Commits cleanly and emits `STORAGE_DELETE_EXECUTED` to the append-only `events` journal (preserving provenance of the deletion action itself without retaining deleted content).

---

## 4. Qdrant Vector Cleanup & Collection Cache Safety
In `faim_native/index/qdrant_index.py`:
- `FAIMIndex.remove(graph_id, node_id)` and `FAIMIndex.delete_graph(graph_id)` synchronize both the in-memory `BruteForceIndex` fallback and Qdrant point deletion (`client.delete(collection_name=self._collection, ...)`).
- `delete_collection()` evicts `self._collection` from the process-local `_ensured_collections` cache (`_ensured_collections.discard(self._collection)`), and `reset_qdrant_connection()` clears `_ensured_collections` so subsequent writes automatically re-create collections if deleted externally.
