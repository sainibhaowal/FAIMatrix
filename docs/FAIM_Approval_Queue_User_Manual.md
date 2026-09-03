# FAIM Approval Queue User Manual

## Overview
The Approval Queue provides a human-in-the-loop interface for managing storage mutations and Cortex-proposed actions. This manual explains how to use the approval queue system.

## Accessing Approval Queue
Navigate to: `/approval-queue?graph_id=<your-graph-id>

## 1. Interface Overview

### 1.1 Dashboard Layout
- **Header:** Shows connection status and graph ID
- **Pending Section:** Actions awaiting operator decision
- **Approved Section:** Actions that have been executed
- **Rejected Section:** Actions that were declined
- **Refresh Button:** Manual refresh of status
- **Search/Filters:** Filter by tool type, status, date

### 1.2 Action Cards
Each pending action displays:
- **Action Type:** What kind of mutation (upload, delete, re-ingest)
- **Proposed By:** Cortex agent or system
- **Description:** Human-readable description
- **Arguments:** Technical details of the action
- **Timestamps:** When proposed, when viewed
- **Operator Decision:** Buttons for Approve/Reject

## 2. Managing Pending Actions

### 2.1 Viewing Pending Actions
1. Navigate to `/approval-queue?graph_id=<id>`
2. View "Pending" section
3. Each card shows:
   - Action type and description
   - Proposed by (system/agent)
   - Technical arguments
   - Proposal timestamp
   - Time since proposal

### 2.2 Approving an Action
1. Click on a pending action card to expand
2. Review the details and arguments
3. Click **"Approve"** button
4. System executes the action
5. Ledger entry created with:
   - Operator ID (your session)
   - Timestamp
   - Decision: "approved"
6. Action moves to "Approved" section
7. Graph state updates automatically

### 2.3 Rejecting an Action
1. Click on a pending action card to expand
2. Review the details
3. Click **"Reject"** button
4. System cancels the action
5. Prompt may appear for rejection note
6. Ledger entry created with:
   - Operator ID (your session)
   - Timestamp
   - Decision: "rejected"
7. Action moves to "Rejected" section
8. Graph state unchanged

## 2.3 Action Types

### 2.1 File Upload Proposal
- **What:** Cortex proposes to ingest a new document
- **Details:** 
  - File name and type
  - Profile configuration
  - Persist mode (strict/relaxed)
  - Expected graph changes
- **Approve:** File is ingested, added to knowledge graph
- **Reject:** File is discarded, not added

### 2.2 Hard Delete Proposal
- **What:** Cortex proposes to hard-delete files/artifacts
- **Details:**
  - Which files/artifacts to remove
  - Graph nodes/edges to remove
  - Orphan detection
- **Approve:** Artifacts purged, orphans detected
- **Reject:** Artifacts retained, graph unchanged

### 2.3 Re-ingest/Retry Proposal
- **What:** Cortex proposes to re-run ingestion for failed/stale files
- **Details:**
  - Which files to retry
  - Previous failure reasons
  - New profile/configuration if different
- **Approve:** Re-ingestion runs, graph updates
- **Reject:** Previous state retained, no changes

## 3. Approval Workflow

### 3.1 Step-by-Step
1. **Cortex proposes** a storage mutation
2. **Action appears** in Pending section
3. **Operator reviews** the proposal card
4. **Operator decides:**
   - Click "Approve" → action executes
   - Click "Reject" → action cancelled
5. **Ledger entry** created automatically
6. **Graph state** updates (if approved)
7. **Notification** sent to operator (if configured)

### 3.2 Approval Ledger
Every action creates a ledger entry with:
- **Operator ID:** Your user session ID
- **Timestamp:** When decision was made
- **Decision:** "approved" or "rejected"
- **Action ID:** Unique identifier
- **Action Type:** What was decided
- **Graph ID:** Which graph was affected
- **Additional Notes:** Optional rejection reason

## 4. Permissions & Security

### 4.1 Tenant Isolation
- All actions are **tenant-scoped**: filtered by `tenant_id` + `graph_id`
- You can only approve/reject actions for your tenant's graphs
- Cross-tenant actions are blocked

### 4.2 Admin Requirements
- **Normal users:** Can approve/reject their tenant's actions
- **Admins:** Can view all tenants' queues (if permitted)
- **Key required:** API key or session authentication
- **All actions logged** with decision trail

### 4.2 Security Rules
- ✅ Human-in-the-loop for all mutating storage actions
- ✅ Tenant isolation at query level
- ✅ Admin key required for certain operations
- ✅ All decisions logged with trail
- ✅ No actions execute without explicit approval

## 5. User Workflows

### 5.1 Typical Day as Operator
1. **Morning:** Log in, check Approval Queue
2. **Review:** See 3-5 pending actions from overnight
3. **Approve/Reject:** Process each action
4. **Review Graph:** Check graph state after actions
5. **Report:** Summary of actions taken
6. **End of day:** Orphan scan if needed

### 5.2 Common Scenarios

#### Scenario A: New Document Upload
1. User uploads file in Cortex Chat
2. Cortex proposes upload to approval queue
3. Operator reviews proposal card
4. **Clicks "Approve"** → File ingested
5. Graph updates with new nodes/edges
6. Summary shows: "1 file ingested"

#### Scenario B: Failed File Re-ingest
1. Previous upload failed (corrupt, timeout, etc.)
2. Cortex proposes re-ingest
3. Operator reviews failure reasons
4. **Clicks "Approve"** → Re-ingestion runs
5. If successful: file added to graph
6. If still fails: Operator may reject or try again

#### Scenario C: Hard Delete Request
1. Cortex proposes to delete stale artifacts
2. Operator reviews which files/artifacts
3. **Clicks "Approve"** → Artifacts purged
4. Orphan scan recommended
5. **Clicks "Reject"** → Nothing changes
6. Graph retains all existing artifacts

## 5. troubleshooting

### Common Issues
| Problem | Cause | Fix |
|---|---|---|
| `No pending actions` | No recent activity | Wait for Cortex to propose actions |
| `Can't approve` | Not tenant owner | Verify tenant access |
| `Approval expired` | Too much time elapsed | Re-propose action in Cortex |
| `Graph not updating` | Action still processing | Wait a moment, refresh page |
| `Ledger not updating` | Page needs refresh | Refresh the approval-queue page |

### Debug Checklist
1. ✅ Verify you're in correct tenant/graph
2. ✅ Check pending actions have recent timestamps
3. ✅ Ensure you have approval permissions
4. ✅ Refresh the page if changes don't appear
5. ✅ Check Cortex Chat for new proposals

## 6. Integration with Cortex Chat

### 5.1 Cortex-Proposed Actions
When Cortex needs to mutate storage, it:
1. **Proposes** the action to the approval queue
2. **Displays** approval card in chat interface
3. **Waits** for operator decision
4. **Executes** if approved
5. **Streams** results back to chat

### 2. Chat Integration Examples
- **"Upload this file"** → Proposal appears in approval queue
- **"Delete these artifacts"** → Proposal appears with details
- **"Re-ingest this file"** → Proposal with retry configuration
- **Always** requires operator approval before execution

## 6. Integration with Storage

### 6.1 Storage Mutations
The approval queue covers these storage mutations:
- ✅ File uploads and re-ingests
- ✅ Hard deletes of artifacts
- ❌ Read-only queries (no approval needed)
- ❌ Theory generation (no approval needed)
- ❌ Feedback recording (no approval needed)

### 6.2 Non-Applicable Actions
- Theory generation → No approval needed
- Feedback recording → No approval needed  
- Graph viewing → No approval needed
- API key management → No approval needed

## 7. Production Considerations

### 7.1 Performance
- Approval decisions are instant (ledger write)
- Graph updates depend on action type
- Orphan scans run periodically (not real-time)
- Ledger provides audit trail without performance impact

### 7.2 Security
- Human-in-the-loop is **required** for all mutations
- No bypass mechanisms exist
- Tenant isolation strictly enforced
- All decisions auditable

### 7.3 Reliability
- Ledger provides audit trail
- Orphan scans detect issues
- Decisions are final (no undo from ledger)
- System queues actions if operator offline

### 7.4 Workflow Tips
- Check approval queue at start of each shift
- Process actions in chronological order
- Review graph state after batch processing
- Keep ledger for audit/compliance requirements

## 8. Quick Start

### First Time Use:
1. Log in to FAIM frontend
2. Navigate to `/approval-queue?graph_id=<your-graph>`
3. Review pending actions (if any)
4. Click "Approve" or "Reject" on each
5. Watch graph state update
6. Check "Live Storage Summary" for results

### Daily Operations:
1. Check approval queue each morning
2. Process pending actions
3. Review graph state changes
4. Note any patterns in Cortex proposals
5. Report any issues to system administrator

## 8. Frequently Asked Questions

### Q: Can I approve multiple actions at once?
A: Currently, actions must be approved/rejected individually for audit trail purposes.

### Q: What if I accidentally reject an important action?
A: Cortex can re-propose the action. Review the rejection reason and decide if re-proposal is needed.

### Q: How long do pending actions stay in the queue?
A: Until acted upon or until Cortex proposes new actions (then oldest may be cleared).

### Q: Can I see the full technical arguments for an action?
A: Yes — expand the action card to see full details including all arguments and technical specifications.

### Q: Do I need admin privileges to approve/reject?
A: Normal users can approve/reject their tenant's actions. Admin key required for cross-tenant or special operations.

### Q: Is there a timeout on pending actions?
A: Pending actions remain until acted upon or until Cortex proposes new actions (system-dependent cleanup).

### Q: Can I add a note to my approval/rejection?
A: The ledger automatically records operator ID and timestamp. Optional rejection notes can be added via the UI.

## 9. Quick Reference Key Terms

| Term | Definition |
|---|---|
| **Proposal** | Cortex's suggestion for a storage mutation |
| **Operator** | Human who approves/rejects proposals |
| **Ledger** | Immutable record of all approval decisions |
| **Tenant** | Isolation group (multi-tenant FAIM) |
| **Graph** | Knowledge graph being managed |
| **Approve** | Green button → action executes |
| **Reject** | Red button → action cancelled |
| **Card** | UI element showing one pending action |
| **Audit Trail** | Immutable record of all decisions |

## 9. Quick Reference Commands

| Action | API Endpoint | UI Location |
|---|---|---|
| List pending actions | `GET /api/v1/cortex/tool-approvals` | Approval Queue page |
| Approve action | `POST /api/v1/cortex/tool-approvals/{id}/approve` | Action card → "Approve" |
| Reject action | `POST /api/v1/cortex/tool-approvals/{id}/reject` | Action card → "Reject" |
| List all actions | `GET /api/v1/cortex/tool-approvals` | Approval Queue page |

## 9. Quick Reference Key Combinations

| Key Combination | Effect |
|---|---|
| `F5` or `Refresh` | Refresh approval queue |
| `Ctrl` + `S` | (Not assigned) |
| `Esc` | Close expanded action card |
| `Arrow Keys` | Navigate between cards (if focused) |

