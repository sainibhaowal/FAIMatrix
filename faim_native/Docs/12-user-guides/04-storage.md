# Storage user guide

## Dashboard

Open `/dashboard/storage` to inspect files, uploads, graphs, and storage
health. The current frontend does not provide an approval-queue page or a
Cortex chat page.

## API families

The storage router is mounted under `/api/v1/storage` and includes file
upload/status/download/provenance operations, graph listing and summary,
backend health, maintenance metrics, retention, raw-store re-encryption, and
crypto rotation operations. The ingest router also exposes:

- `POST /api/v1/ingest`
- `POST /api/v1/ingest/upload`

Use `faim_native/api/routers/storage.py` for exact request and response
schemas.

## Durability model

PostgreSQL is the canonical metadata and graph store. The raw store preserves
source bytes; Redis and Qdrant are optional acceleration/coordination
services. Back up both the database and raw-store volume before a release.

Uploads and maintenance operations are tenant-scoped and require the normal
authentication headers. A successful upload request means the request was
accepted; inspect its returned job/status data before declaring ingestion
complete.
