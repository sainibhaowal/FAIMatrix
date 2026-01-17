# FAIM-Native Data Classification

> Stage-11: Security Hardening

This document classifies the sensitivity of data in FAIM-Native.

## Sensitivity Levels

| Level            | Description                 | Handling           |
| ---------------- | --------------------------- | ------------------ |
| **PUBLIC**       | Can be exposed without harm | Normal handling    |
| **INTERNAL**     | Should not be public        | Access control     |
| **CONFIDENTIAL** | Business-sensitive          | Encryption at rest |
| **RESTRICTED**   | PII/Secrets                 | Encryption + audit |

## Data Classification

### Authentication & Authorization

| Data                 | Classification | Storage                 | Notes            |
| -------------------- | -------------- | ----------------------- | ---------------- |
| API Keys (plaintext) | **RESTRICTED** | Never stored            | Only hashed form |
| API Key Hashes       | CONFIDENTIAL   | `tenant_api_keys` table | Argon2id         |
| Admin Key Hashes     | CONFIDENTIAL   | `admin_api_keys` table  | Argon2id         |
| Session Tokens       | RESTRICTED     | Memory/cookies          | Short-lived      |
| Tenant IDs           | INTERNAL       | All tables              | Not secret       |

### User Content

| Data       | Classification | Storage           | Notes               |
| ---------- | -------------- | ----------------- | ------------------- |
| Raw Files  | CONFIDENTIAL   | Blob storage      | Consider encryption |
| Anchors    | INTERNAL       | `evidence_blocks` | Positional data     |
| Node Text  | CONFIDENTIAL   | `nodes` table     | Core FAIM content   |
| Query Text | INTERNAL       | Logs (redacted)   | Transient           |
| Embeddings | INTERNAL       | `nodes.embedding` | Derived data        |

### System Data

| Data           | Classification | Storage             | Notes             |
| -------------- | -------------- | ------------------- | ----------------- |
| Database URL   | RESTRICTED     | Environment vars    | Contains password |
| Redis Password | RESTRICTED     | Environment vars    | Never in code     |
| Event Journal  | INTERNAL       | `event_journal`     | Audit trail       |
| Metrics        | PUBLIC         | `/metrics` endpoint | If exposed        |
| Health Status  | PUBLIC         | `/ready` endpoint   | Boolean only      |

### Operational Data

| Data           | Classification | Storage       | Notes           |
| -------------- | -------------- | ------------- | --------------- |
| Log Messages   | INTERNAL       | stdout/files  | Auto-redacted   |
| Stack Traces   | INTERNAL       | Logs only     | Never to client |
| Request IDs    | PUBLIC         | Headers/logs  | Correlation     |
| Error Messages | PUBLIC         | API responses | Generic only    |

## Data Flow

```
┌─────────────────┐
│  Client Request │
│  (Query Text)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API Layer     │─────┐
│  (Validation)   │     │ Log (redacted)
└────────┬────────┘     │
         │              ▼
         ▼         ┌─────────────┐
┌─────────────────┐│    Logs     │
│  Query Engine   ││  (INTERNAL) │
│  (Processing)   │└─────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Postgres     │
│ (CONFIDENTIAL)  │
└─────────────────┘
```

## Encryption Requirements

### At Rest

| Data           | Encryption  | Method            |
| -------------- | ----------- | ----------------- |
| API Key Hashes | Inherent    | Argon2id          |
| Raw Files      | Recommended | AES-256-GCM       |
| Node Text      | Optional    | Field-level       |
| Database       | Recommended | Volume encryption |

### In Transit

| Connection     | Encryption  | Method   |
| -------------- | ----------- | -------- |
| Client → API   | Required    | TLS 1.2+ |
| API → Postgres | Required    | TLS/SSL  |
| API → Redis    | Recommended | TLS      |

## Access Control

### By Role

| Role     | Access                       |
| -------- | ---------------------------- |
| Tenant   | Own data only (by tenant_id) |
| Admin    | All tenants, admin endpoints |
| Operator | Infrastructure, backups      |

### By Endpoint

| Endpoint     | Auth Required | Data Returned |
| ------------ | ------------- | ------------- |
| `/ready`     | No            | Status only   |
| `/v1/ingest` | Yes (Tenant)  | Confirmation  |
| `/v1/query`  | Yes (Tenant)  | Nodes/edges   |
| `/admin/*`   | Yes (Admin)   | System info   |

## Retention

| Data          | Retention    | Notes              |
| ------------- | ------------ | ------------------ |
| Raw Files     | User-defined | Deleted on request |
| Nodes/Edges   | User-defined | Version history    |
| Event Journal | 90 days      | Audit purposes     |
| Logs          | 30 days      | Debugging          |
| Backups       | 7 days       | Recovery           |

## Compliance Notes

- **GDPR:** Raw files and node text may contain PII
- **SOC2:** Audit logging required (event_journal)
- **HIPAA:** If storing PHI, encryption at rest mandatory
