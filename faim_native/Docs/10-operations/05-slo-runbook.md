# SLO And On-Call Runbook

This runbook defines the minimum operational contract for a production FAIM
deployment.

## Suggested SLOs

- Availability: 99.9 percent for `/health` and core API routes.
- Readiness: 99.9 percent success for `/ready`.
- Latency: p95 under 500 ms for common read paths.
- Ingest failures: below 1 percent over a rolling 24 hour window.
- Queue lag: below an agreed backend-specific threshold for durable jobs.

## Alerting Principles

- Alert on user-visible symptoms, not just host metrics.
- Use burn-rate alerts for sustained failures.
- Separate infrastructure alerts from application contract alerts.

## Alert Examples

- `/ready` failures for 5 minutes.
- Elevated 5xx rate on the API.
- p95 latency above target for 10 minutes.
- Migration mismatch or schema drift.
- Auth failures spiking above normal baseline.

## On-Call Response

1. Confirm the alert is real.
2. Check `/health` and `/ready`.
3. Verify recent deploys and migrations.
4. Check tenant auth, rate-limit, and database connectivity.
5. If the issue is deployment-related, roll back to the last known-good image.
6. If the issue is data-related, stop writes before attempting repair.

## Post-Incident Outputs

- Root cause.
- Timeline.
- User impact.
- Fix plan.
- Follow-up test or alert added to prevent recurrence.
