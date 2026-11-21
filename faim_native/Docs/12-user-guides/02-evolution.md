# Evolution user guide

## Dashboard

Open `/dashboard/evolution` to inspect the evolution status and controls.

## API

The current evolution routes are mounted under `/api/v1`:

- `POST /api/v1/evolve` starts an evolution operation.
- `GET /api/v1/evolve/status` reads the current status.
- `PATCH /api/v1/evolve/control` updates supported controls.
- `GET /api/v1/evolve/metrics` returns the scrapeable metrics snapshot.
- `GET /api/v1/evolve/invention/flow` and `/versions` expose invention state.
- `GET /api/v1/evolve/backups` and `POST /api/v1/evolve/backups/restore` expose backup operations.

Evolution is bounded by runtime configuration and durable job state. It is not
an autonomous guarantee of correctness or semantic truth. Review the returned
status, events, and metrics before treating a cycle as successful.
