# Documentation audit

Audit date: 2026-11-20

The active documentation set was compared with the current FastAPI router
mounts, frontend route tree, docker-compose.yml, runtime configuration, and
the canonical benchmark artifact. The disposition is conservative: uncertain
or historical material was archived instead of being presented as current
implementation guidance.

## Retained and moved into `faim_native/Docs`

| Original document | Canonical destination | Reason |
| --- | --- | --- |
| docs/END_TO_END_ARCHITECTURE.md | 01-architecture/01-end-to-end-architecture.md | Current implementation-oriented architecture; links corrected after move |
| docs/TECHNICAL_MEMORY_CONTRACT.md | 01-architecture/02-technical-memory-contract.md | Current query and temporal contract |
| docs/PRODUCTION_HARDENING.md | 11-security/02-production-hardening.md | Current auth, bootstrap, and hardening behavior; unsupported OCR flags corrected |
| docs/FAIM_API_Keys_User_Manual.md | 12-user-guides/01-api-keys.md | Rewritten for current dashboard and /api/v1/api-keys surface |
| docs/FAIM_Evolution_User_Manual.md | 12-user-guides/02-evolution.md | Rewritten for current evolution routes and dashboard |
| docs/FAIM_Providers_User_Manual.md | 12-user-guides/03-providers.md | Rewritten for current provider pages and router families |
| docs/FAIM_Storage_User_Manual.md | 12-user-guides/04-storage.md | Rewritten for current storage/ingest routes; Cortex and approval claims removed |
| docs/2) BackEnd/Deployment_Ops/DEPLOYMENT.md | 10-operations/01-deployment.md | Rewritten against the current Compose services and .env.example |
| docs/2) BackEnd/Deployment_Ops/RUNBOOK.md | 10-operations/03-runbook.md | Rewritten with current migration, health, metrics, and recovery guidance |
| docs/2) BackEnd/Security/DATA_CLASSIFICATION.md | 11-security/01-data-classification.md | Current data-handling policy |
| docs/2) BackEnd/Security/DEPLOYMENT_TLS.md | 11-security/05-tls.md | Rewritten as deployment-neutral edge guidance |
| docs/2) BackEnd/Security/SECURITY_GUIDE.md | 11-security/03-security-guide.md | Rewritten as a control checklist, without unsupported certification claims |
| docs/2) BackEnd/Security/THREAT_MODEL.md | 11-security/04-threat-model.md | Rewritten with evidence requirements instead of unconditional checkmarks |
| docs/Operations/github-branch-protection.md | 10-operations/02-github-branch-protection.md | Current repository policy |
| docs/Operations/security-hardening.md | 10-operations/04-security-hardening.md | Current security baseline policy |
| docs/Operations/slo-runbook.md | 10-operations/05-slo-runbook.md | Operational targets and incident workflow |

The new 02-api/01-api-documentation.md, 13-benchmarks/01-benchmark-evidence.md,
09-implementation/01-current-code-map.md, and this audit manifest are canonical
documents created from the current source and evidence artifacts rather than
copied from historical phase reports.

## Archived as historical, speculative, external, or mismatched

The following groups were not suitable as current implementation references:

- docs/2) BackEnd/Reports/**: historical stage/test reports with superseded
  counts, paths, or readiness claims.
- docs/2) BackEnd/Architecture/** except the selected implementation material
  above: stale absolute paths, missing modules, or proposal-level master
  specification/completion claims.
- docs/2) BackEnd/API_Reference/** except the selected material above: legacy
  imports and schemas that do not match the current package layout.
- docs/2) BackEnd/Deployment_Ops/** except DEPLOYMENT.md and RUNBOOK.md:
  historical delivery logs or outdated checks.
- docs/2) BackEnd/Security/** except the selected material above: obsolete
  auth variables, unsupported guarantees, or duplicate policy copies.
- docs/3) FrontEnd/**: research concepts and static mock images, not current
  route documentation.
- docs/External Engineering Pattern/**: external research PDFs, retained for
  reference but not product documentation.
- docs/Files/**: roadmaps, proposals, and implementation plans outside the
  current source-of-truth contract.
- docs/Operations/** except the selected policy files: stale host-specific
  paths or duplicate deployment guidance.
- Root agent cortex.md, architecture_overview.md, check code.md,
  design_notes.md, IMPLEMENTATION_REPORT.md, now work.md, Plan.md,
  Pridction.md, FAIM_Cortex_User_Manual.md, and
  FAIM_Approval_Queue_User_Manual.md: historical, speculative, generic, or
  documentation for surfaces absent from the current code.
- Root FAIM_API_Keys_User_Manual.md, FAIM_Evolution_User_Manual.md,
  FAIM_Providers_User_Manual.md, FAIM_Storage_User_Manual.md, and
  PRODUCTION_HARDENING.md: retained only after the rewrites listed above.

Historical source documents and superseded `faim_native/Docs` drafts were removed from the active tree and remain preserved in Git history outside the canonical documentation surface.

## Validation performed

- Confirmed router mounting and /api/v1 prefix in faim_native/api/app.py.
- Confirmed absence of faim_native/api/routers/cortex.py and an approval-queue
  frontend page.
- Confirmed current dashboard route files under frontend/src/app.
- Confirmed Compose service names and production auth defaults.
- Removed stale absolute paths and unsupported Cortex/approval references from
  retained documents.
- Checked the canonical Markdown links and ran git diff --check after edits.

## Current categorization rules

- `03-storage-and-ingestion/`, `04-graph-and-figview/`,
  `05-self-invention-and-evolution/`, `06-physics-and-realtime-sse/`,
  `07-control-plane-ui-and-auth/`, and
  `08-observability-timestamps-and-logging/` contain subsystem implementation
  guides.
- `02-api/` contains public API contracts and route documentation.
- `01-architecture/` contains system-wide runtime and data contracts.
- `13-benchmarks/` contains benchmark evidence interpretation and publication
  controls; executable harness code and result artifacts remain under
  `faim-benchmarks/`.
- `09-implementation/` contains code maps and documentation governance.
- `10-operations/` contains deployment, runbook, SLO, and repository operations.
- `14-research/` contains analysis, benchmark interpretation, and planned work.
- `11-security/` contains security policy, threat, TLS, and data-classification
  documents.
- `12-user-guides/` contains operator and developer-facing product guides.

The former `README copy.md` was an obsolete duplicate index whose links
pointed to the removed `Completed/` tree. It contained no unique engineering
content and was removed from the canonical tree.
