# FAIM API Keys User Manual

## Overview
API keys manage tenant authentication and access control for the FAIM system. This manual explains how to create, use, and manage API keys.

## Accessing API Keys
Navigate to: `/api-keys?tenant_id=<your-tenant-id>

## Creating API Keys

### 1. Generate New Key
- **Location:** API Keys dashboard page
- **Process:** Click "Generate New Key"
- **Output:** 
  - **Key:** Secret string used for authentication
  - **Tenant ID:** Associated namespace
  - **Created At:** Timestamp
  - **Last Used:** Timestamp (updates on each API call)

### 2. Key Properties
- **Key Format:** Random UUID-like string
- **Tenant Scoping:** Each key is scoped to a specific tenant
- **One-Time Reveal:** Key is shown **once** after generation — store it securely
- **Revocation:** Keys can be revoked at any time
- **Rotation:** Generate new keys; old ones can be revoked

## Using API Keys

### 1. Authentication Header
- **Header:** `X-Api-Key: <your-key>`
- **Example:** `X-Api-Key: abc123-def456-ghi789`
- **Required:** All API requests must include this header

### 2. Tenant ID Header
- **Header:** `X-Tenant-Id: <tenant-name>`
- **Example:** `X-Tenant-Id: default`
- **Required:** Most endpoints require both headers

### 3. API Usage
- **Base URL:** `http://localhost:8000/api/v1/`
- **All endpoints** require both `X-Api-Key` and `X-Tenant-Id`
- **WS Chat:** Also requires `tenant_id` query param or `x-tenant-id` header

### 3. Endpoints Requiring API Key
| Endpoint | Description |
|---|---|
| `GET /api/v1/health` | System health |
| `WS /api/v1/cortex/ws/chat?tenant_id=...&graph_id=...` | WebSocket chat |
| `POST /api/v1/reasoning/feedback` | Record feedback |
| `GET /api/v1/reasoning/learning/state` | Learning state |
| `GET /evolve/theories?graph_id=...` | Theories listing |
| `GET /api/v1/storage/graphs` | List tenant graphs |

## Managing API Keys

### 1. Listing Keys
- **View:** API Keys dashboard
- **Shows:** All keys for your tenant, creation time, last used

### 2. Revoking Keys
- **Action:** Click "Revoke" next to any key
- **Effect:** Key immediately becomes invalid
- **Purpose:** Remove compromised or unused keys

### 3. Rotating Keys
- **Process:** 
  1. Generate new key
  2. Update client code/integration to use new key
  3. Revoke old key
- **Purpose:** Maintain security without service disruption

### 4. Key Security
- **Never share** API keys in client code or public repos
- **Store securely** — treat like passwords
- **Reveal only once** — after generation, the key is shown only one time
- **Revoke immediately** if compromised

## API Key Lifecycle

```
Generate → Store Securely → Use in Headers → Rotate when needed → Revoke if compromised
```

## API Key Constraints
- **Tenant-isolated:** Keys only work for their associated tenant
- **Rate limits:** Apply per-tenant (configurable via runtime)
- **Concurrent usage:** Multiple keys per tenant allowed
- **Key expiration:** Not time-based; active until revoked

## Troubleshooting

### Common Issues
| Problem | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Missing `X-Api-Key` header | Add `X-Api-Key: <key>` |
| `401 Unauthorized` | Missing `X-Tenant-Id` header | Add `X-Tenant-Id: <tenant>` |
| `403 Forbidden` | Key doesn't belong to tenant | Use key for correct tenant |
| `403 Forbidden` | Key revoked | Generate new key |
| `WS rejects connection` | Missing `tenant_id` query param | Add `?tenant_id=<your-tenant>` |

### Debug Checklist
1. ✅ Include `X-Api-Key` header
2. ✅ Include `X-Tenant-Id` header  
3. ✅ Key has not been revoked
4. ✅ Key was generated (one-time reveal)
5. ✅ Endpoint supports API key auth

## Integrated Systems

### Backend Services Using API Keys
- **Auth middleware** (`faim_native/api/middleware/auth.py`) — Validates all keys
- **WS chat** — Requires `tenant_id` param + `x-api-key` header
- **Reasoning feedback** — Validates key before recording
- **Theory generation** — Tenant-isolated queries
- **Storage operations** — Tenant-scoped tool calls

### Frontend Integration
- **API Keys dashboard** — Management interface
- **Auth flow** — Keys stored in memory, not persisted to client
- **Rotation workflow** — Dashboard-driven

## Notes
- API keys are **not** the same as JWT tokens or session cookies
- Keys are **managed per-tenant** — cross-tenant keys are rejected
- The system defaults to `FAIM_SELF_EVOLVE_ENABLED=true` and `FAIM_SELF_INVENT_ENABLED=true`
- Keys remain active until explicitly revoked — no automatic expiration

## Generated Key Example
```
Key:  f47ac10b-58cc-4372-a567-0e02b2c3d479
Tenant: default
Created: 2026-08-15T02:30:00Z
Last Used: 2026-08-15T03:15:22Z (updates on each API call)
```
