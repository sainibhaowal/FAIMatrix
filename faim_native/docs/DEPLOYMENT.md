# FAIM-Native Deployment Guide

## Production Environment Requirements

- **PostgreSQL 14+**: Primary transactional store.
- **Redis 6+**: Coordination and acceleration cache.
- **Python 3.10+**: Runtime environment.

## Hardening Checklist

- [ ] Disable `DEBUG` log level (`FAIM_LOG_LEVEL=INFO`).
- [ ] Set `FAIM_DATABASE_URL` with SSL enabled.
- [ ] Set `FAIM_AUTO_MIGRATE=false` (Default). Prevent application instances from racing migrations.
- [ ] rotate `TENANT_KEYS_JSON` and `ADMIN_KEYS_JSON` periodically.
- [ ] Enable firewall for internal components (Redis, Postgres).
- [ ] Configure volume backups for the database.

## Deployment Steps

1. Provision infrastructure.
2. Set environment variables.
3. Apply migrations manually: `python3 -m store.pg.migrate up`.
   > [!NOTE]
   > In multi-instance deployments, run migrations as a separate CI/CD step or a K8s Job before starting the API.
4. Start API: `uvicorn api.app:create_app --host 0.0.0.0 --port 8000`.
5. Start Worker: `python3 -m orchestration.jobs.worker`.
