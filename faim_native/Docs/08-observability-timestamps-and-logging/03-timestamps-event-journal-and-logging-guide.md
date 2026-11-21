# Timestamps, Append-Only Event Journal & Structured Logging Guide

## 1. Scope
Documents the timezone-aware timestamp model across PostgreSQL, cryptographic event journal guarantees, structured application logging, frontend timestamp surfaces, and verified technical gaps across:
- **ORM Schema**: `faim_native/store/pg/models_faim.py`
- **Event Journal Repository & Router**: `faim_native/store/pg/repos/event_repo.py`, `faim_native/api/routers/events.py`
- **Structured Runtime Logger**: `faim_native/runtime/logging.py`, `faim_native/api/app.py`, `faim_native/orchestration/jobs/worker.py`
- **Frontend Consumers**: `frontend/src/app/(admin)/dashboard/evolution/page.tsx`, `frontend/src/components/evolution/EvolutionPhysicsChart.tsx`, `frontend/src/components/evolution/EvolutionVersionHistory.tsx`, `frontend/src/components/evolution/InventionFlowCanvas.tsx`
- **Pytest Harness**: `tests/conftest.py`

---

## 2. Database Timestamp Schema (`models_faim.py`)
All core persistence tables store UTC `DateTime(timezone=True)` timestamps:
- **`EventModel` (`events`)**: `ts` (domain event timestamp), `created_at` (DB insertion timestamp), monotonic `seq`, `kind`, `payload` (`JSONB`), and SHA-256 `checksum` computed over `(ts, graph_id, kind, payload)` inside `EventRepo.append` / `EventRepo.emit`. Append-only guarantees raise `AppendOnlyViolation` on mutation attempts.
- **`NodeModel` (`nodes`)**: `created_at`, `updated_at`, `last_access`, plus bitemporal columns `valid_from` and `valid_to`.
- **`RawRefModel`, `StorageFileModel`, `MemoryWriteRequestModel`**: `created_at`, `uploaded_at`, `ingested_at`, `updated_at`, `delete_requested_at`, `completed_at`.
- **`JobModel` (`jobs`) & `JobEventModel` (`job_events`)**: `created_at`, `updated_at`, `started_at`, `completed_at`, and per-step `JobEventModel.ts` (`step_start`, `step_progress`, `log`).
- **Evolution & Learning Models**: `GraphVersionModel.updated_at`, `GraphDiagnosticsCacheModel.computed_at`, `SelfInventionStateModel.last_cycle_at` / `updated_at`, `SelfEvolutionStateModel.last_evolved_at` / `control_updated_at` / `updated_at`, `EvolutionBackupModel.created_at`, `EvolutionOutcomeModel.cycle_ts` / `created_at`, `EvolutionMetaMetricModel.ts`, `GraphTheoryModel.created_at`.

---

## 3. Structured Logging (`logging.py` & `app.py`)
- `faim-api` (`faim_native/api/app.py`) initializes `setup_logging()` from `faim_native/runtime/logging.py`.
- `JSONFormatter` emits structured single-line JSON logs with ISO-8601 UTC `ts`, `level`, `msg`, `module`, and optional correlation fields (`request_id`, `tenant_id`, `graph_id`, `latency_ms`, `job_id`, `raw_id`, `op`, `status`, `endpoint`), filtered by regex secret redaction (`RedactingFilter`).

---

## 4. Known Technical Gaps Tracked from Audit (Next Backlog)
The end-to-end engineering audit verified the following remaining gaps to close next:
1. **`EvolutionPhysicsChart` Frame Table Time Column**: `Live Telemetry Frames` renders `f.label` (`v138`) under the `Time` header instead of localized `f.ts`, and the hover tooltip slices `pt.ts.slice(11, 19)` in raw UTC.
2. **`InventionFlowCanvas` Timestamp Exposure**: `InventionFlowNode` and `InventionFlowTheoryItem` (`evolve.py`) do not yet return `created_at` / `updated_at` / `last_access` / `computed_at` for display in canvas cards or the Inspector Drawer.
3. **Bitemporal Node Fields (`last_access`, `valid_from`, `valid_to`)**: Present in `NodeModel` and `NodeRepo.touch_node`, but retrieval/evolution flows do not systematically populate validity intervals or render `last_access` across Evolution surfaces.
4. **Evolution `Timeline & Logs` Power Features**: Currently capped in memory at `MAX_TIMELINE_EVENTS = 260` (`100` initial tail fetch) without older-event pagination, date/kind multi-filtering, raw JSON payload/checksum drawer, export, or `job_events` / `learningOutcomes.cycle_ts` integration.
5. **Worker Structured Logging Parity**: `faim_native/orchestration/jobs/worker.py` does not call `setup_logging()`, emitting unstructured plaintext logs without timestamps; `app.py` also contains a legacy `SecureLogFilter` substring rule on `"tenant_id"`.
6. **Backend `ev.ts` vs `ev.created_at` Consistency**: `_build_evolve_metrics` and `_build_invention_versions` (`evolve.py`) read `ev.created_at` while `/events` and `_build_physics_stream` use `ev.ts`.
7. **Test Harness Database Isolation (`tests/conftest.py`)**: `_configure_isolated_test_database()` exits early when `DATABASE_URL` is present and `FAIM_PYTEST_ISOLATE_DB=1` is unset, causing fixtures that run `drop_all_tables` / `table.delete()` to target the live DB unless isolation is explicitly enabled. Always pass `FAIM_PYTEST_ISOLATE_DB=1` (until `conftest.py` enforces safe isolation by default).
