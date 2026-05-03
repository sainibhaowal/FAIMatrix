# Local Production

This is the end-to-end local production path for FAIM.

It uses the same backend, worker, frontend, and database containers as the
default compose stack, but places Caddy in front of the app and stores data on
host-backed local production directories.

## Files Involved

- [docker-compose.localprod.yml](/home/sephi-asi/FAIM/docker-compose.localprod.yml)
- [deploy/Caddyfile.localprod](/home/sephi-asi/FAIM/deploy/Caddyfile.localprod)
- [deploy/env.localprod.example](/home/sephi-asi/FAIM/deploy/env.localprod.example)
- [scripts/localprod_up.sh](/home/sephi-asi/FAIM/scripts/localprod_up.sh)
- [scripts/localprod_down.sh](/home/sephi-asi/FAIM/scripts/localprod_down.sh)
- [scripts/localprod_smoke.sh](/home/sephi-asi/FAIM/scripts/localprod_smoke.sh)
- [scripts/localprod_backup.sh](/home/sephi-asi/FAIM/scripts/localprod_backup.sh)
- [scripts/localprod_restore.sh](/home/sephi-asi/FAIM/scripts/localprod_restore.sh)
- [scripts/localprod_ssl.sh](/home/sephi-asi/FAIM/scripts/localprod_ssl.sh)

## Behavior

- Caddy terminates TLS on `https://faimatrix.localhost:8443`.
- TLS certs are generated locally with `mkcert` when available; otherwise the
  repo falls back to an OpenSSL SAN certificate.
- Browser API traffic still goes through the frontend so NextAuth middleware
  and rewrites keep working.
- The restricted admin section lives at `/dashboard/admin` and uses the same
  signed-in session plus a server-side admin key bridge.
- The admin section includes an alerts inbox at `/dashboard/admin#alerts` and
  can send the same operational alerts to email through `RESEND_API_KEY`.
- Backend health endpoints are exposed through Caddy for readiness and smoke
  checks.
- Postgres, Redis, Qdrant, raw blobs, and backups are persisted under
  `Runtime/localprod/`.

## Start

```bash
cp deploy/env.localprod.example .env
npm run faim:localprod:up
```

## Smoke Test

```bash
npm run faim:localprod:smoke
```

If you want the explicit smoke URL:

```bash
npm run faim:localprod:smoke -- https://faimatrix.localhost:8443
```

## Backup

```bash
npm run faim:localprod:backup
```

## Restore

```bash
npm run faim:localprod:restore
```

## Validation Rules

- Do not bypass the frontend for `/api/*` browser traffic.
- Do not enable wildcard CORS in local production.
- Do not enable `unsafe-eval` in production CSP.
- Keep `FAIM_AUTO_MIGRATE=false` and run migrations explicitly.
- Keep the backup directory and raw data directory persisted on the host.
- Keep `FAIM_ADMIN_KEY` and the admin email allowlist out of the browser.
- Keep `RESEND_API_KEY` server-side only; it is used for OTP and admin alert
  email delivery.
