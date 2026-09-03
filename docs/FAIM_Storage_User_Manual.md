# FAIM Storage User Manual

## Overview
FAIM storage manages knowledge graph data, file uploads, OCR processing, and graph operations. This manual explains how to use the storage features.

## Accessing Storage
Navigate to: `/storage?graph_id=<your-graph-id>

## 1. File Upload

### 1.1 Upload via Cortex Chat
- **Method:** Attach file in chat → Cortex proposes upload → operator approves → file ingested
- **Process:**
  1. User attaches file in chat
  2. Cortex proposes upload with profile/persist settings
  3. Operator reviews and **approves** or **rejects**
  4. Approved files are ingested and added to knowledge graph
  5. Rejected files are discarded

### 1.2 Upload via Dashboard
- **Location:** Storage page → "Upload File" button
- **Process:**
  1. Select file(s) to upload
  2. Choose profile (affects extraction pipeline)
  3. Choose persist mode (relaxed/strict)
  4. Submit — file goes to approval queue
  5. Admin/operator approves → file ingested

### 1.3 Upload Profiles
- **Profiles:** Different extraction configurations
- **Selection:** Choose based on file type and content
- **Example:** Academic papers vs. technical docs vs. manuals

### 1.4 Persist Modes
- **Strict:** Only store if validation passes completely
- **Relaxed:** Store with warnings allowed
- **Default:** Configured in runtime settings

## 2. Storage Status & Health

### 2.1 Live Storage Summary
- **Endpoint:** `GET /api/v1/cortex/storage/status`
- **Shows:**
  - Graph node/edge counts
  - Ingest status (pending/approved/rejected)
  - Orphan artifact health check
  - Real-time progress during upload

### 2.2 Orphan Artifact Scan
- **Endpoint:** `GET /api/v1/cortex/storage/orphan-scan`
- **Purpose:** Detects artifacts without owning files
- **Action:** Results show orphans that can be cleaned up

### 2.3 Storage Health Metrics
- Total nodes per graph
- Total edges per graph
- Ingest queue status
- Last successful ingest timestamp
- Orphan count

## 3. Graph Operations

### 3.1 Approval Queue
- **Location:** `/approval-queue?graph_id=<id>`
- **Purpose:** Human-in-the-loop for storage mutations
- **Operations:**
  - **Propose:** Cortex suggests a storage action
  - **Approve:** Operator approves → action executes
  - **Reject:** Operator rejects → action cancelled
  - **Ledger:** All decisions recorded with operator ID and timestamp

### 3.2 Tool Approval Workflow
1. **Cortex proposes** a storage mutation (e.g., delete file, re-ingest)
2. **Operator reviews** the proposal details
3. **Operator decides:**
   - **Approve:** Action executes, ledger entry created
   - **Reject:** Action cancelled, ledger entry created
4. **Execution:** If approved, action runs automatically
5. **Notification:** Operator notified of completion

### 3.3 Storage Tools with Human-in-the-Loop
| Tool | Purpose | Requires Approval |
|---|---|---|
| File upload | Ingest new documents | ✅ Yes |
| Hard delete | Purge graph artifacts | ✅ Yes |
| Re-ingest/Retry | Fix failed/stale files | ✅ Yes |
| Query graph | Read-only, no approval needed | ❌ No |
| Orphan scan | Health check | ❌ No |

## 4. OCR (Optical Character Recognition)

### 4.1 OCR UI Polish
- **Location:** Storage page → OCR tab or `?tab=ocr`
- **Features:**
  - **Capability hints:** What files are supported
  - **Policy visibility:** OCR rules and limitations
  - **Supported file messaging:** What file types are accepted
  - **Marketing alignment:** UI feels intentionally shipped

### 4.2 OCR Configuration
- **Engine:** `FAIM_OCR_ENGINE` (default: `paddleocr_v6`)
- **Enabled:** `FAIM_OCR_ENABLED` (default: `true`)
- **Fail-closed:** `FAIM_OCR_FAIL_CLOSED` (default: `false`)
- **Languages:** `FAIM_OCR_LANGS` (default: `eng`)

### 4.2 OCR Supported Files
- **Text formats:** `.txt`, `.md`, `.pdf`, `.docx`
- **Image formats:** `.png`, `.jpg`, `.jpeg`, `.tiff`
- **Maximum size:** Configurable per deployment
- **Quality:** OCR engine accuracy varies by document type

## 5. Storage API Endpoints

### 5.1 Graph Operations
| Endpoint | Description |
|---|---|
| `GET /api/v1/cortex/storage/status` | Live storage summary (read-only) |
| `GET /api/v1/cortex/storage/orphan-scan` | Orphan artifact health check (read-only) |
| `GET /api/v1/storage/graphs` | List tenant graphs with node/edge counts |

### 5.2 Approval Queue Endpoints
| Endpoint | Description |
|---|---|
| `POST /api/v1/cortex/tool-approvals/propose` | Agent proposes mutating storage action |
| `GET /api/v1/cortex/tool-approvals` | List pending/approved/rejected approvals (tenant-scoped) |
| `POST /api/v1/cortex/tool-approvals/{id}/approve` | Approve and execute action |
| `POST /api/v1/cortex/tool-approvals/{id}/reject` | Reject without execution |

## 5. User Workflows

### 5.1 Upload New Document
1. Go to Storage page
2. Click "Upload File"
3. Select file → Choose profile/persist mode
4. Submit → File goes to approval queue
5. Operator reviews → Approves/Rejects
6. If approved: file ingested, graph updated
7. If rejected: file discarded, can re-submit

### 5.2 Check Storage Health
1. Go to Storage page
2. View "Live Storage Summary"
3. Check "Orphan Scan" results
4. Review node/edge counts
5. Review ingest status

### 5.2 Approve/Reject Tool Action
1. Go to Approval Queue page
2. View pending proposals
3. Select proposal → Review details
4. Click "Approve" or "Reject"
5. System executes/cancels action
6. Ledger entry created with operator ID

## 6. Permissions & Tenant Isolation

### 5.1 Tenant Scoping
- All storage tools are **tenant-scoped**: queries filtered by `tenant_id` + `graph_id`
- Approval ledger (`cortex_tool_approvals`) is tenant-isolated
- Human-in-the-loop required for all mutating storage actions

### 5.2 Admin Requirements
- Admin key or elevated permissions required for approval actions
- All actions logged with `operator decision trail`
- Admin can view all tenants' approval queues (if permitted)

## 7. Troubleshooting

### Common Issues
| Problem | Cause | Fix |
|---|---|---|
| `Upload fails: 403` | Missing admin key | Use admin key or get approval |
| `Orphan count high` | Previous failed uploads | Run orphan scan → clean up |
| `Graph not updating` | Approval not given | Approve the pending action |
| `OCR not available` | `FAIM_OCR_ENABLED=false` | Enable in runtime config |
| `File type not supported` | Unsupported extension | Convert to supported format |

### Debug Checklist
1. ✅ Check Live Storage Summary
2. ✅ Run Orphan Scan if needed
3. ✅ Verify approval queue has no pending issues
4. ✅ Confirm OCR settings in runtime config
5. ✅ Verify file type and size limits

## 7. System Integration

### Backend Services
- **Storage router** — Handles uploads, approvals, ingest
- **OCR service** — `faim_native/perception/extract/ocr_service.py`
- **Knowledge graph** — Node/edge management
- **Approval ledger** — `cortex_tool_approvals` table
- **Storage router** — `faim_native/api/routers/storage.py`

### Frontend Integration
- **Storage dashboard** — Management UI
- **OCR polish** — UI polish layer
- **Approval queue** — Human decision interface
- **Profile selection** — Pipeline configuration

## 8. Production Considerations

### 8.1 Performance
- Large files: Increase Qdrant timeout (120s recommended)
- Orphan scans: Run periodically (not real-time)
- Ingest progress: Real-time 0-100% tracking

### 8.2 Security
- All mutations require human approval
- Tenant isolation enforced at query level
- Admin keys for approval actions
- Fail-closed behavior for OCR

### 8.3 Reliability
- OCR fail-closed behavior configurable
- Orphan scan detects issues early
- Ingest queue provides visibility
- Ledger provides audit trail

## 9. Frequently Asked Questions

### Q: Can I upload any file type?
A: No — supported types are listed in the OCR section. Unsupported types are rejected.

### Q: How long does ingest take?
A: Depends on file size and complexity. Progress is shown in real-time.

### Q: What happens if I approve a deletion?
A: The graph artifacts are purged and orphans are detected by the next scan.

### Q: Can I recover after a hard delete?
A: No — hard delete removes artifacts. Use re-ingest if you need to recover the data.

### Q: Can I see who approved/rejected actions?
A: Yes — the approval ledger shows operator ID, timestamp, and decision for every action.

## 10. Quick Start Checklist

### For New Users:
1. ✅ Log in with admin/tenant key
2. ✅ Go to Storage page
3. ✅ Click "Upload File" → Select first file
4. ✅ Choose profile → Submit
5. ✅ Go to Approval Queue → Review proposal
6. ✅ Click "Approve" → Wait for ingest
7. ✅ View graph updates in real-time
8. ✅ Check "Live Storage Summary" for metrics

### For Admins:
1. ✅ Monitor orphan scan periodically
2. ✅ Review approval queue daily
3. ✅ Update OCR config if needed
4. ✅ Rotate API keys regularly
5. ✅ Review ledger for audit trail

