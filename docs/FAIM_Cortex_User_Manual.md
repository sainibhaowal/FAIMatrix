# FAIM Cortex User Manual

## Overview
FAIM Cortex is the real-time conversational agent that connects to your knowledge graph via WebSocket. This manual explains how to use Cortex for questions, research, and memory operations.

## Accessing Cortex
### 1. WebSocket Connection
- **Endpoint:** `ws://<host>:8000/api/v1/cortex/ws/chat`
- **Required Query Params:**
  - `graph_id`: Your knowledge graph identifier
  - `session_id` (optional): Your session identifier
  - `tenant_id` (optional): Your tenant identifier
- **Authentication:** `X-Tenant-Id` + `X-Api-Key` headers (or query params)

### 2. Frontend Access
- **Location:** Sidebar → "Cortex Chat" button
- **Or:** Direct URL with WS parameters
- **No installation** — runs in browser

## 2. Starting a Cortex Session

### 2.1 Connection Steps
1. Click "Cortex Chat" in the frontend sidebar
2. Enter **Graph ID** (select from your graphs or use "default")
3. (Optional) Enter **Session ID** (or let system generate)
4. Click **Connect**
5. Wait for **"Session created"** event
6. Start asking questions

### 2.2 Connection Parameters
| Parameter | Required? | Description |
|---|---|---|
| `graph_id` | ✅ Yes | Your knowledge graph identifier |
| `session_id` | No | Your session identifier (generated if omitted) |
| `tenant_id` | No | Your tenant identifier (default works) |

### 2.3 Connection Events
Upon connection, you'll receive:
- **`session_created`**: Confirmation with your session ID and graph ID
- **System status:** Ready to receive messages

## 3. Sending Messages

### 3.1 Message Types
- **`user_message`**: Your question/content (most common)
- **`ping`**: Keep-alive signal
- **`feedback`**: Rate a previous response (with optional correction)

### 3.2 Sending a Message
1. Type your question in the input field
2. Press **Enter** or click the send button
3. System processes via Cortex agent
4. Response streams sentence-by-sentence

### 3.3 Message Example
```json
{
  "type": "user_message",
  "content": "What is the production readiness status of this graph?"
}
```

### 3.3 Message Example with Session
```json
{
  "type": "user_message",
  "content": "Summarize the current production readiness",
  "session_id": "my-session-123",
  "graph_id": "my-graph-456"
}
```

## 4. Response Types

### 4.1 Agent Response
- **What you'll see:** Streaming text with the answer
- **Fields:** `turn_id`, `session_id`, `answer_mode`, `brain_state`
- **Example:** `{"type": "agent_response", "content": "The production readiness is 85%..."}`

### 4.2 Thinking Indicator
- **What you'll see:** "Cortex is thinking..."
- **Purpose:** Indicates system is processing
- **Duration:** Typically 1-3 seconds

### 4.3 Tool Calls
- **What they are:** Cortex proposes to use storage tools
- **Types:** File upload, delete, re-ingest, etc.
- **Approval required:** Yes (see Approval Queue)
- **Your action:** Click "Approve" or "Reject" in the interface

### 4.4 Error Responses
- **What you'll see:** Error type + message
- **Handling:** System may retry or surface error in UI
- **Example:** `{"type": "error", "content": "Unable to process request"}`

## 5. Feedback & Learning

### 5.1 Rating Responses
1. After Cortex answers, rate the response
2. Use thumbs up/down or 1-5 scale
3. **Optional:** Add a **correction** note
4. **Submit** — stats are persisted durably

### 5.2 Feedback Payload
```json
{
  "turn_id": "<turn-id-from-response>",
  "user_rating": 0.8,   // 0.0–1.0
  "session_id": "<your-session>",
  "graph_id": "<your-graph>",
  "correction": "Optional: What was wrong, what should have been said"
}
```

### 5.3 Learning Impact
- **After 3 ratings:** Stats are persisted to database
- **Reliability score:** 0.0–1.0 (high rating + few corrections = high)
- **Adaptive strategy:** System may adjust confidence thresholds
- **Persistence:** Stats survive restarts (durable reinforcement learning)

## 6. Cortex Features

### 6.1 Answer Modes
- **`direct`:** Straightforward answer
- **`ask_follow_up`:** Asks clarifying question
- **`ask_suggestion`:** Suggests related topics
- **`confirmation`:** Asks for confirmation before acting

### 6.2 Answer Modes (Deep Detail)
- **`direct`:** Straightforward factual answer
- **`ask_follow_up`:** "Do you want me to elaborate on X?"
- **`ask_suggestion`:** "You might also look at Y"
- **`confirmation`:** "Should I proceed with Z?"

### 6.2 Answer Modes (Deep Detail continued)
- **`comparative`:** Compare two things
- **`analytical`:** Analyze a complex topic
- **`chronological`:** Present information in time order
- **`summarization`:** Condense long content

### 6.3 Brain State
The Cortex maintains a `brain_state` object in each response that includes:
- **`t`**: Current thought/thinking path
- **`h`**: Hypothesis being tested
- **`n`**: New information noticed
- **`s`**: Summary being built
- **`a`**: Actions considered
- **`o`**: Outcome predicted

This is primarily for debugging/research purposes but shows the Cortex's internal reasoning process.

## 6. Cortex Tools (with Approval)

### 6.1 Tool Call Workflow
1. Cortex proposes a tool call during conversation
2. **Approval card appears** in the interface
3. **You decide:** Approve or Reject
4. **If approved:** Action executes automatically
5. **If rejected:** Action cancelled, conversation continues

### 6.2 Tool Call Types
| Tool Type | Purpose | Approval Required |
|---|---|---|
| File upload | Ingest new document | ✅ Yes |
| Hard delete | Remove artifacts | ✅ Yes |
| Re-ingest | Retry failed ingestion | ✅ Yes |
| Query graph | Read-only info | ❌ No |
| Tool approval | Review pending actions | ✅ Yes (in UI) |

### 6.2 Tool Call Details
When a tool call is proposed, the interface shows:
- **Tool name:** What action will be taken
- **Arguments:** Technical details (file path, graph changes, etc.)
- **Urgency:** How urgently Cortex wants this
- **Approval buttons:** "Approve" / "Reject"

### 6.2 Approving a Tool Call
1. Review the tool call details
2. Verify it's what you want
3. Click **"Approve"** 
4. System executes the action
5. Result streams back to chat
6. Ledger entry created (if storage mutation)

### 6.2 Rejecting a Tool Call
1. Review the tool call details
2. Decide you don't want this action
3. Click **"Reject"** 
4. Action cancelled, conversation continues
5. No ledger entry created (or "rejected" entry)

## 7. Cortex Features

### 7.1 Memory Sessions
- **Session management:** Switch between past conversations
- **Session deletion:** Delete specific sessions (DB + local)
- **Purge all local sessions:** Clear all local session data
- **Session ID:** Visible in UI, used for tracking

### 7.2 Session Management
- **Switch sessions:** Browse past conversations
- **Delete session:** Remove specific session (DB + local)
- **Purge all:** Clear all local session data
- **Session ID:** Used for tracking and feedback

### 7.3 Storage Operations (with Approval)
- **Upload:** Cortex proposes → Operator approves → File ingested
- **Delete:** Cortex proposes → Operator approves → Artifacts purged
- **Re-ingest:** Cortex proposes → Operator approves → Retry ingestion
- **All require** operator approval in the approval queue

### 7.4 Cryptographic Audit & Provenance
- **Provenance mode:** Select via answer mode
- **What you get:** Full evidence trail with:
  - Raw file IDs
  - Section headers
  - Block types
  - SHA-256 hashes
  - Commit logs and timestamps
- **Use cases:** Compliance, debugging, transparency

### 7.5 Managing Memory Sessions
- **Switch between past conversations** via session selector
- **Delete sessions** (DB + local)
- **Purge all local sessions**
- **Ask Cortex:** "What's the storage health?" → Real-time summary

## 8. Answer Modes (Selector)

### 8.1 Selecting Answer Mode
Before asking a question, select an answer mode:
- **`direct`** (default): Straightforward answer
- **`ask_follow_up`**: Asks clarifying question
- **`ask_suggestion`**: Suggests related topics
- **`confirmation`**: Asks for confirmation before acting
- **`comparative`**: Compare two things
- **`analytical`**: Analyze a complex topic
- **`chronological`**: Present in time order
- **`summarization`**: Condense long content

### 8.2 When to Use Each Mode
- **`direct`**: Most questions, quick answers
- **`ask_follow_up`**: When you need more info
- **`ask_suggestion`**: When you want related topics
- **`confirmation`**: Before system actions
- **`comparative`**: Comparing two items/concepts
- **`analytical`**: Complex topics, analysis
- **`chronological`**: Timelines, history
- **`summarization`**: Long documents, reports

## 9. Cortex & Storage Integration

### 9.1 Storage Tools
Cortex can propose these storage operations:
- **File upload:** New document ingestion
- **Hard delete:** Artifact removal
- **Re-ingest:** Failed/stale file retry
- **All require** operator approval in the approval queue

### 9.2 Example Workflows
- **"Upload this PDF"** → Proposal → Approve → Ingested
- **"Delete old artifacts"** → Propose → Approve → Purged
- **"Re-run ingestion"** → Propose → Approve → Retried
- **All** appear in Approval Queue for your decision

### 9.2 Example Workflows (Detailed)
1. **Upload Session:**
   - User: "Upload this PDF about climate change"
   - Cortex: Proposes upload to approval queue
   - Operator: Reviews → Approves
   - System: Ingests file, adds to graph
   - Chat: "File ingested successfully"

2. **Delete Session:**
   - User: "Delete stale artifacts from 2023"
   - Cortex: Proposes hard delete to approval queue
   - Operator: Reviews → Approves
   - System: Purges artifacts, detects orphans
   - Chat: "Artifacts purged, orphan scan recommended"

3. **Re-ingest Session:**
   - User: "Re-run ingestion for that failed file"
   - Cortex: Proposes re-ingest to approval queue
   - Operator: Reviews → Approves
   - System: Retries ingestion
   - Chat: "Re-ingestion complete" or "Still failing"

## 10. Cortex & WebSocket Details

### 10.1 Connection Lifecycle
1. **Connect:** `ws://host/api/v1/cortex/ws/chat?graph_id=...`
2. **Handshake:** `session_created` event
3. **Message exchange:** `user_message` → `agent_response`
4. **Feedback:** `feedback` event (rating + optional correction)
5. **Disconnect:** Client or network terminates

### 10.2 WebSocket Events
| Event | Direction | Description |
|---|---|---|
| `session_created` | Server → Client | Connection established |
| `agent_response` | Server → Client | Streaming answer |
| `user_message_echo` | Server → Client | Echo of sent message |
| `thinking` | Server → Client | System is processing |
| `error` | Server → Client | Error condition |
| `complete` | Server → Client | Session complete |
| `session_closed` | Server → Client | Connection ending |

### 10.3 WebSocket Authentication
- **Headers:** `X-Tenant-Id` + `X-Api-Key`
- **Query params:** `tenant_id`, `graph_id`, `session_id`, `api_key`
- **Default:** If no headers/params, defaults to `tenant_id: "default"`
- **Required:** For production use, always provide proper auth

### 10.3 WebSocket Error Handling
- **`1006`:** Abnormal closure (network issue, send too early)
- **`1000`:** Normal closure
- **Handling:** Auto-reconnect attempted (configurable, max 5 attempts)
- **User action:** Refresh page or reconnect manually

## 11. Cortex & Memory Sessions

### 11.1 Session Switching
- **View past conversations:** Select from session history
- **Delete specific session:** Removes from DB and local storage
- **Purge all local sessions:** Clears all local session data
- **Session ID:** Used for feedback tracking

### 11.2 Session Deletion
1. Go to session selector
2. Select session to delete
3. Confirm deletion
4. System removes from DB + local storage
5. Session no longer appears in history

### 11.3 Purge All Local Sessions
1. Go to session selector
2. Click "Purge all local sessions"
3. All local session data cleared
4. DB sessions may remain (configurable)
5. Useful for: Privacy, storage cleanup, fresh start

## 12. Cortex & Cryptographic Audit

### 12.1 Provenance Mode
- **Select via:** Answer mode selector → "Provenance"
- **What you receive:** Full evidence proof for data retention policy
- **Includes:**
  - Raw file IDs
  - Section headers
  - Block types
  - SHA-256 hashes
  - Commit logs and timestamps
- **Use cases:** Compliance, debugging, transparency

### 12.2 When to Use Provenance
- Regulatory compliance requirements
- Debugging data issues
- Transparency for auditors
- Tracking data provenance over time

### 12.3 Provenance Output Format
```json
{
  "evidence": [
    {
      "file_id": "...",
      "section": "...",
      "block_type": "...",
      "sha256": "...",
      "committed_at": "...",
      "commit_log": "..."
    }
  ],
  "policy": "data retention policy description",
  "generated_at": "..."
}
```

## 13. Cortex Tips & Best Practices

### 13.1 Getting Better Answers
- **Be specific** in your questions
- **Use answer modes** appropriately
- **Provide context** (graph ID, session ID)
- **Rate responses** to help the system learn
- **Use corrections** for poor answers

### 13.2 Managing Sessions
- **Switch sessions** to compare different conversations
- **Delete irrelevant sessions** to keep UI clean
- **Purge all** if starting fresh
- **Note session IDs** for feedback tracking

### 13.2 Managing Sessions (continued)
- **Cortex remembers** across sessions if session ID is consistent
- **Feedback persists** durably (survives restarts)
- **Theories and macros** persist across sessions
- **Graph state** evolves as you interact

### 13.3 Security & Tenant Isolation
- **Always use proper tenant ID**
- **Never share session IDs** publicly
- **API keys** protect WS connections
- **Cortex is tenant-isolated** — your data doesn't mix with others

### 13.4 Performance Tips
- **Stable internet** for streaming responses
- **Modern browser** recommended
- **Graph size** affects response time (larger = slightly slower)
- **Feedback** helps system learn faster

### 13.5 Troubleshooting
| Issue | Cause | Fix |
|---|---|---|
| `Cannot connect` | Wrong graph_id or no graph | Verify graph_id, check graphs list |
| `No response` | Network timeout | Refresh, reconnect |
| `Answers too generic` | Not enough graph data | Add more content to graph |
| `Too many errors` | Auth headers missing | Add X-Tenant-Id + X-Api-Key |
| `Session lost` | Timeout or network issue | Reconnect, session persists |
| `Provenance not available` | Wrong answer mode | Select "Provenance" mode |

## 14. Quick Start

### First Time Use:
1. Log in to FAIM frontend
2. Click "Cortex Chat" in sidebar
3. Select your graph ID
4. Click **Connect**
5. Type: `"What is this graph about?"`
6. Receive streaming answer
7. **Rate the response** (thumbs up/down)
8. **Optional:** Add correction if needed
9. **Check Learning State** → See stats persist
10. **Explore** other features (theories, invention, etc.)

### Daily Use:
1. Log in
2. Click Cortex Chat
3. Select graph
4. Connect
5. Ask questions
6. Rate responses
7. Check Learning State periodically
8. Explore theories/invention if graph has sufficient data

## 15. Quick Reference Commands

| Action | How to Do It |
|---|---|
| Connect to Cortex | Click "Cortex Chat" → Select graph → Connect |
| Send question | Type in input field → Press Enter |
| Rate response | Thumbs up/down or 1-5 scale + optional correction |
| Switch sessions | Session selector in UI |
| Delete session | Session selector → Delete |
| Provenance mode | Answer mode selector → "Provenance" |
| Check learning state | `/admin/reasoning/learning/state` endpoint |
| View theories | `/evolve/theories?graph_id=<id>` |
| View approval queue | `/approval-queue?graph_id=<id>` |

## 16. Quick Reference Key Commands (WebSocket)

| WebSocket Action | Payload Example |
|---|---|
| Connect | `ws://host/api/v1/cortex/ws/chat?graph_id=default` |
| Send question | `{"type": "user_message", "content": "Your question"}` |
| Receive answer | `{"type": "agent_response", "content": "Answer text..."}` |
| Send feedback | `{"type": "feedback", "turn_id": "id", "user_rating": 0.8}` |
| Send correction | `{"type": "feedback", "turn_id": "id", "user_rating": 0.3, "correction": "..."}` |
| Keep alive | `{"type": "ping"}` |

