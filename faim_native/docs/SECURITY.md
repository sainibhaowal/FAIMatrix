# FAIM-Native Security Model

This document outlines the security architecture and operational practices for the production-grade FAIM-Native appliance.

## 1. Tenant Isolation Model

FAIM-Native implements a **shared database, logical isolation** model.

- **Row-Level Enforcement**: Every table in the schema includes a `tenant_id` column which is `NOT NULL`.
- **Database Triggers**: A Postgres trigger `reject_empty_tenant` prevents insertion or update of any row missing a `tenant_id`.
- **Repository Layer**: All internal repositories (`NodeRepo`, `EdgeRepo`, etc.) are initialized with a `tenant_id` and automatically filter all queries by this ID.
- **API Middleware**: `TenantAuthMiddleware` extracts the API key from the `X-Tenant-Key` header, resolves it to a `tenant_id`, and injects it into the request state for use by routers and orchestration flows.

## 2. API Key Management

### Authentication

- Authentication is handled via `X-Tenant-Key` header.
- Keys are mapped to tenants via the `TENANT_KEYS_JSON` environment variable.
- Comparison uses `secrets.compare_digest` to prevent timing attacks.

### Key Rotation

To rotate a tenant key:

1. Update the `TENANT_KEYS_JSON` environment variable to include the new key alongside the old one.
2. Restart the FAIM-Native services.
3. Update the client applications to use the new key.
4. Remove the old key from `TENANT_KEYS_JSON` and restart services again.

## 3. Rate Limiting Strategy

FAIM-Native uses a **sliding window / token bucket** algorithm for per-tenant rate limiting.

- **Middleware**: `RateLimitMiddleware` tracks request counts in memory (with Redis support for multi-instance deployments).
- **Configuration**: Limits are defined via `FAIM_RATE_LIMITS_JSON`.
- **Headers**: Clients receive standard rate limit headers:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## 4. Data Integrity & Privacy

### Payload Bounds

- Event payloads are truncated to `FAIM_EVENT_PAYLOAD_MAX_BYTES` (default 4096) to prevent exhaustion attacks and large data leaks in logs.
- Truncation is performed before persisting to the `EventJournal`.

### Audit Trail

- The `events` table is **append-only**.
- Database triggers prevent any `UPDATE` or `DELETE` on the `events` table.
- Every event record includes a SHA256 checksum of its contents to ensure integrity.

## 5. Administrative Access

### Admin Key

- Access to administrative endpoints (like `/ready`, `/health`) can be restricted via `ADMIN_KEYS_JSON`.
- Currently, `/ready` and `/health` are public by default but should be firewalled or protected by a proxy in high-security environments.

### Database Credentials

- FAIM-Native should always be run with the minimum required Postgres permissions.
- Encryption at rest for the Postgres data volume is highly recommended.
