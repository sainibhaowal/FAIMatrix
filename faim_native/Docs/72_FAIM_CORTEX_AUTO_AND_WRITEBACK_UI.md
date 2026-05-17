# 72 - FAIM Cortex: Auto Mode & Writeback Approval UI

## 1. Cortex Auto (The "One-Click Intelligence" Button)
The **Cortex Auto** mode is the culmination of FAIM's adaptive intelligence. 
- **Auto-Classification**: Instead of manually selecting TIMELINE or CONTRADICTION, the 1M+ Semantic Registry automatically classifies the user's intent.
- **Dynamic Reasoning**: It determines if the query needs 1 hop or 24 hops.
- **User Experience**: The button features a shimmering gradient to indicate that the "Deterministic Engine" is active.

## 2. Cortex Writeback Approval UI
One of the most powerful features of FAIM is the **Writeback Approval** logic. The AI never writes to the long-term memory (Postgres/Graph) without explicit human consent.
- **Proposal Phase**: When the system identifies a new fact or a resolved contradiction, it generates a "Writeback Proposal."
- **Discovery Interface**: These proposals appear in the UI with a "Review" badge.
- **Approval Logic**: Users can click "Commit to Memory" to officially update the Federated Intelligence Graph. This ensures that the graph remains a source of "Ground Truth" rather than AI hallucinations.

## 3. UI Discoverability & Accessibility
- **Cortex Composer**: The `ChatComposer` contains the primary `AnswerMode` selector, featuring "Cortex Auto" as the default.
- **Task Type Badges**: Every response from the AI is labeled with its detected Task Type (e.g., `INVESTIGATE`, `PROVENANCE`), showing the user exactly which brain circuit was used.
- **Proposal Sidebar**: A dedicated tab in the Intelligence Sidebar lists all pending Writeback Proposals.

## 4. Implementation Proof
- **State Handling**: `frontend/src/contexts/ChatContext.tsx` manages the `answerMode` persistence via `localStorage`.
- **UI Component**: `frontend/src/components/memoryquery/ChatComposer.tsx` implements the shimmering "Auto" button and mode selector.
- **Backend Bridge**: `POST /api/v1/cortex/turn` returns the `proposals` array for the UI to render.

---
*Status: Production Ready*
*Safety: Human-in-the-Loop Writeback*


## Detailed Explanations & Scenario Analysis

### Why is this feature here?
"Cortex Auto" removes cognitive load from the user by automatically choosing the best reasoning mode. "Writeback Approval" exists as a strict safety mechanism. It ensures that an AI cannot silently corrupt the enterprise knowledge graph with false information.

### How it works in any scenario
Scenario: A user asks, "Update the server IP to 192.168.1.100".
Cortex Auto detects the `UPDATE` intent. The AI processes the request and updates the state. However, the database is NOT modified. Instead, a `Writeback Proposal` appears in the UI. The graph remains unchanged until the human user explicitly reviews the proposed IP change and clicks "Commit to Memory."

### Comparisons & Differences
Standard AI agents (like AutoGPT) often take autonomous, invisible actions that can be destructive. FAIM separates "Reasoning" from "Action". Reasoning is autonomous (Cortex Auto), but Action is strictly gated (Writeback Approval).

### Why it is unique and useful
It provides "Safe Autonomy". Users get the speed of an AI assistant with the safety of a manual database transaction. The shimmering UI of the Cortex Auto button also provides critical psychological feedback, letting the user know the deterministic engine is active.

### Future Scenarios
As trust in the system grows, enterprise admins can configure "Auto-Approve" policies for specific, low-risk domains (e.g., automatically updating documentation typos), while keeping the strict Writeback Approval UI for high-risk domains like financial ledgers or infrastructure configs.
