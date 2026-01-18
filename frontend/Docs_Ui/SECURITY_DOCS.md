# Security Hardening (10/10)

The FAIM UI is built on a "Hardened Architecture" designed to meet enterprise security standards.

## 1. Authentication (OTP-Only)

- **No Passwords**: Authentication is handled purely via cryptographically secure One-Time Passwords (OTP).
- **Entropy**: OTPs are generated using the Python `secrets` module (high entropy).
- **Rate Limiting**: Requests are limited to 3 per 15 minutes per email to prevent flooding.
- **Brute Force Protection**: Automatic 30-minute lockout after 5 failed verification attempts.

## 2. Session Integrity

- **JWT Signing**: All session tokens are HS256 signed.
- **Strict Secrets**: Production deployment **requires** `NEXTAUTH_SECRET`. Fallbacks are forbidden in production environments.
- **HttpOnly Cookies**: Session data is stored in secure, HttpOnly, SameSite cookies to prevent XSS-based hijacking.

## 3. Data Isolation (The Tenant Model)

- **Strict IDs**: All API requests must include a validated `X-Tenant-Id`.
- **Backend Enforcement**: The database enforces a `tenant_id NOT NULL` constraint on all core tables (Nodes, Edges, Events).
- **IDOR Prevention**: Cross-tenant data access is mathematically impossible due to hard-coded scoping in the data access layer.

## 4. API Security Middleware

- **HSTS**: Forces browsers to use HTTPS for all connections (1-year policy).
- **CSP**: Strict Content Security Policy limiting scripts to trusted origins.
- **X-XSS-Protection**: Browser-level XSS blocking enabled.
- **Nosniff**: Prevents MIME-type sniffing of served assets.

## 5. Generic Error Handling

The UI and API use generic error messages for sensitive operations (e.g., "Invalid or expired code") to prevent account enumeration by attackers.
