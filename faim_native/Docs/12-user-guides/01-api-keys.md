# API keys user guide

## Dashboard

Open `/dashboard/api-keys` in the frontend. API keys are tenant-scoped,
revealed once at creation, and revocable.

## API

The management surface is mounted under `/api/v1/api-keys`. Protected routes
accept:

```http
X-Tenant-Id: <tenant-id>
X-Api-Key: <api-key>
```

Store the returned secret outside the repository. FAIM stores a verifier/hash,
not the plaintext key, and production authentication is database-primary.

## Safe operations

1. Create a narrowly scoped key for the intended tenant.
2. Store it in the deployment secret manager.
3. Verify one protected request.
4. Rotate by creating a replacement key.
5. Revoke the old key and confirm access is denied.

Do not use `default`, `test-key`, or `admin` credentials in production.
