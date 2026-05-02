# TOTP Authenticator Login Implementation

## Scope

Adds optional authenticator-app login for users who enable it from the Profile page.
Email OTP remains the default login path.

## Backend

- `faim_native/api/routers/auth.py`
  - Adds TOTP setup, confirm, status, recovery-code regeneration, and disable endpoints.
  - Extends `/api/v1/auth/otp/verify` with `factor_type`.
  - Stores TOTP secrets encrypted with the existing `NEXTAUTH_SECRET`-derived key.
  - Stores recovery codes only as Argon2id hashes.
- `faim_native/store/pg/models_auth.py`
  - Adds `totp_enabled`, `totp_secret_encrypted`, `totp_confirmed_at`, and `recovery_code_hashes`.
- `faim_native/store/pg/repos/user_repo.py`
  - Adds TOTP state update helpers.
- `faim_native/store/pg/migrations/0022_user_totp_2fa.sql`
  - Adds the production migration.

## Frontend

- `frontend/src/app/(app)/dashboard/profile/page.tsx`
  - Adds the Authenticator Login panel before Danger Zone.
  - Supports QR setup, confirmation, recovery-code display, regeneration, and disable.
- `frontend/src/app/auth/login/page.tsx`
  - Keeps email OTP as the default login.
  - Offers authenticator-code login when TOTP is enabled.
- `frontend/src/lib/auth.ts`
  - Passes `factor_type` to the backend credentials verifier.

## Safety

- TOTP secrets are not logged and are not stored in plaintext.
- Recovery codes are shown once and stored hashed.
- Disable/regenerate requires a current authenticator code.
- Existing email OTP, NextAuth JWT sessions, tenant identity, and API key auth remain unchanged.
