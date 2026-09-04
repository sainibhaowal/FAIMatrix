"use client";

import React from "react";
import {
  ManualShell,
  SectionHeading,
  SubHeading,
  type TocItem,
} from "@/components/manuals/ManualShell";

const TOC: TocItem[] = [
  { id: "overview", label: "1. Inline Approval Flow" },
  { id: "architecture", label: "2. Architecture Overview" },
  { id: "modal", label: "3. Inline Approval Modal" },
  { id: "history-panel", label: "4. Approval History Panel" },
  { id: "integration", label: "5. CortexChat Integration" },
  { id: "responsive", label: "6. Responsive Design" },
  { id: "heartbeat", label: "7. WebSocket Heartbeat" },
  { id: "use-cases", label: "8. Use Cases & User Flows" },
  { id: "activity-flows", label: "9. Activity Flow" },
  { id: "sequence", label: "10. Sequence Diagrams" },
  { id: "configuration", label: "11. Configuration" },
  { id: "troubleshooting", label: "12. Troubleshooting" },
  { id: "workflow", label: "13. End-to-End Workflow" },
];

export function CortexManual({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <ManualShell
      open={open}
      onClose={onClose}
      title="FAIM Cortex Manual"
      subtitle="Inline approvals · WebSocket chat · audit history"
      toc={TOC}
      accent="#22d3ee"
    >
      <SectionHeading id="overview" kicker="Chapter 7b" title="7b. Inline Approval Flow & History Panel">
        <p>
          This chapter documents the inline approval system in Cortex Chat, enabling users to approve or deny
          tool proposals directly in the chat stream without leaving the conversation. It covers the complete
          approval lifecycle from tool proposal to audit log, including inline modals, toggleable history panels,
          WebSocket heartbeat mechanics, use cases, and end-to-end workflows.
        </p>
      </SectionHeading>

      <SectionHeading id="architecture" kicker="7b.1" title="7b.1 Architecture Overview">
        <p>
          The approval system integrates three core components: the CortexChat stream for inline approvals,
          the ApprovalHistoryPanel sidebar for viewing all approval records, and the persistent
          /approval-queue dashboard as the source of truth for audit and compliance.
        </p>
        <ul className="list-disc list-inside text-slate-400 space-y-2 mb-4">
          <li>Inline Approval Modal: React Portal overlay appearing in chat stream when a tool requires approval</li>
          <li>Approval History Panel: Toggleable sidebar panel (like HistoryPanel) showing all approval records</li>
          <li>Approval Queue Dashboard: Persistent /dashboard/approval-queue page as source of truth/history</li>
          <li>WebSocket: Real-time messaging for approval events (approve_tool, reject_tool, ping, pong)</li>
          <li>Backend: REST API endpoints at /cortex/tool-approvals for propose/list/approve/reject</li>
        </ul>
      </SectionHeading>

      <SectionHeading id="modal" kicker="7b.2" title="7b.2 Inline Approval Modal Component">
        <p>
          The InlineApprovalModal component renders a React Portal overlay in the chat stream when a tool
          requires user approval. It displays the tool name, arguments (expandable), reason, and a note field,
          with Approve (Cmd+Enter) and Deny buttons.
        </p>
      </SectionHeading>

      <SectionHeading id="history-panel" kicker="7b.3" title="7b.3 Approval History Panel">
        <p>
          The ApprovalHistoryPanel is a toggleable sidebar panel (like HistoryPanel) showing all approval records
          with status badges, timestamps, notes, and a filter toggle for pending vs all approvals.
        </p>
      </SectionHeading>

      <SectionHeading id="integration" kicker="7b.4" title="7b.4 CortexChat Integration">
        <p>
          Integration of the inline approval modal into CortexChat, replacing the bottom banner with a
          streamlined modal system. Includes ping/pong heartbeat filtering, visual emphasis on triggering messages,
          and responsive design.
        </p>
      </SectionHeading>

      <SectionHeading id="responsive" kicker="7b.5" title="7b.5 Responsive Design & Sidebar Toggle">
        <p>
          The approval history panel and chat interface adapt to all screen sizes. The sidebar toggle button in
          the header provides consistent access across all device sizes.
        </p>
        <ul className="list-disc list-inside text-slate-400 space-y-1 mt-2">
          <li>xl+ screens (1280px+): Sidebar always visible by default, toggle hides/shows</li>
          <li>lg screens (1024-1279px): Sidebar hidden by default, toggle shows</li>
          <li>md/sm screens (&lt;1024px): Sidebar hidden, toggle shows as overlay panel</li>
          <li>Chat area: Flex-1 expands to fill available space when sidebar hidden</li>
          <li>Padding: sm:px-6 sm:py-6 on container, sm:px-6 sm:py-4 on messages area</li>
          <li>Touch targets: Minimum 44px for all interactive elements on mobile</li>
        </ul>
      </SectionHeading>

      <SectionHeading id="heartbeat" kicker="7b.6" title="7b.6 Backend Ping/Pong Heartbeat">
        <p>
          The backend implements a bidirectional heartbeat mechanism to ensure WebSocket connection health and
          detect stale connections.
        </p>
        <ul className="list-disc list-inside text-slate-400 space-y-1 mt-2">
          <li>Client Ping: Frontend sends ping every 30 seconds via setInterval</li>
          <li>Server Pong: Backend responds with pong immediately</li>
          <li>Server Ping: Backend sends ping every 15 seconds (server-initiated)</li>
          <li>Client Pong: Frontend auto-responds with pong</li>
          <li>Connection Timeout: 90 seconds without pong triggers reconnection logic</li>
          <li>Reconnection: Exponential backoff, max 5 attempts</li>
          <li>Filtered: Both ping and pong messages filtered from chat stream</li>
        </ul>
      </SectionHeading>

      <SectionHeading id="use-cases" kicker="7b.7" title="7b.7 Use Case Diagrams & User Flows">
        <p>Below are the primary use cases:</p>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <p className="text-xs font-bold text-cyan-300 mb-2">Use Case 1: Standard Tool Approval (Operator)</p>
          <p className="text-slate-400 text-xs overflow-x-auto whitespace-pre-wrap">
Actor: System Operator
Trigger: Cortex proposes storage_delete tool
Flow:
  1. CortexChat receives tool_call WS event (approval_id: 42)
  2. InlineApprovalModal opens in chat stream (portal)
  3. Operator reviews: tool=storage_delete, args=&#123;path:"/data/old.pdf"&#125;, reason="Cleanup"
  4. Operator enters note: "Approved per retention policy"
  5. Operator clicks Approve (Cmd+Enter)
  6. Frontend sends: &#123;"type":"approve_tool","payload":&#123;"approval_id":42,"note":"Approved per retention policy"&#125;&#125;
  7. Backend: updates tool_approvals status="approved", executes tool
  8. Backend emits tool_approved WS event
  9. CortexChat: shows "✅ Tool approved and executed", removes from pending
  9. ApprovalHistoryPanel: adds row with status=Approved, green badge
 10. Dashboard /approval-queue: new row in persistent log
Result: Tool executed, audit trail complete
          </p>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <p className="text-xs font-bold text-rose-300 mb-2">Use Case 2: Tool Denial with Reason (Security Officer)</p>
          <p className="text-slate-400 text-xs overflow-x-auto whitespace-pre-wrap">
Actor: Security Officer
Trigger: Cortex proposes storage_ingest with suspicious path
Flow:
  1. CortexChat receives tool_call WS event (approval_id: 43)
  2. InlineApprovalModal opens: tool=storage_ingest, args=&#123;path:"/etc/passwd"&#125;
  3. Officer reviews: reason="Ingest system file", suspicious path
  3. Officer enters note: "Denied - path traversal attempt detected"
  4. Officer clicks Deny
  4. Frontend sends: &#123;"type":"reject_tool","payload":&#123;"approval_id":43,"note":"Denied - path traversal attempt detected"&#125;&#125;
  5. Backend: updates tool_approvals status="rejected", logs rejection
  6. Backend emits tool_rejected WS event
  7. CortexChat: shows "❌ Tool rejected", removes from pending
  8. ApprovalHistoryPanel: adds row with status=Rejected, rose badge, note visible
  9. Dashboard /approval-queue: rejected entry with red badge
Result: Malicious action blocked, audit trail preserved
          </p>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <p className="text-xs font-bold text-cyan-300 mb-2">Use Case 3: Audit Review (Compliance Auditor)</p>
          <p className="text-slate-400 text-xs overflow-x-auto whitespace-pre-wrap">
Actor: Compliance Auditor
Trigger: Monthly audit review
Flow:
  1. Auditor opens /dashboard/approval-queue (persistent log)
  2. Filters: date range=last 30 days, status=all
  3. Reviews: 47 approvals (32 approved, 12 rejected, 3 pending)
  4. Clicks rejected row: sees note "path traversal attempt detected"
  4. Clicks approved row: sees note "Approved per retention policy"
  5. Clicks "Export CSV" downloads SHA-256 verified report
  6. Verifies: all rejections have notes, all approvals traceable to operator
Result: Compliance verified, audit trail complete
          </p>
        </div>
      </SectionHeading>

      <SectionHeading id="activity-flows" kicker="7b.8" title="7b.8 Activity Flow Diagrams">
        <p>Activity diagrams showing the complete flow from tool proposal to resolution:</p>
        <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap">
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                    APPROVAL ACTIVITY FLOW                                            │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ┌─────────┐     ┌──────────┐     ┌───────────┐     ┌────────────┐     ┌─────────┐   │
│  │ User    │     │ Cortex   │     │ Cortex    │     │ WebSocket  │     │ Backend │   │
│  │ Query   │────►│ Reasoning│────►│ Tool Call │────►│ tool_call  │────►│ Propose │   │
│  └─────────┘     └──────────┘     └───────────┘     └────────────┘     └─────────┘   │
│        │                                               │                    │           │
│        │         ┌─────────────────────────────────────▼────────────────┐   │           │
│        │         │            INLINE MODAL OPENS (Portal)               │   │           │
│        │         │  ┌─────────────────────────────────────────────────┐ │   │           │
│        │         │  │ Tool: storage_delete  ID: #42  Status: PENDING │ │   │           │
│        │         │  │ Args: &#123;path: "/data/old.pdf"&#125;                    │ │   │           │
│        │         │  │ Reason: Cleanup old backup files                 │ │   │           │
│        │         │  │ [Expand Args ▼]  [Note: ________________]       │ │   │           │
│        │         │  │ [Deny]                    [Approve ⌘+Enter]    │ │   │           │
│        │         │  └─────────────────────────────────────────────────┘ │   │           │
│        │         └─────────────────────────────────────────────────────┘   │           │
│        │                                               │                    │           │
│        │         ┌─────────────────┐          ┌──────────────────────────▼─────┐    │
│        │         │  OPERATOR       │          │        BACKEND PROCESSING        │    │
│        │         │  DECISION       │          │                                  │    │
│        │         │                 │          │  1. Update tool_approvals        │    │
│        │         │  [Approve]      │          │     status="approved"            │    │
│        │         │        │        │          │  2. Execute tool                 │    │
│        │         │        ▼        │          │  3. Write to pulse_v2 ledger     │    │
│        │         │   "Approved"    │          │  4. Emit tool_approved WS event  │    │
│        │         └───────┬─────────┘          └──────────────────────────────────┘    │
│        │                  │                                                 │           │
│        │                  ▼                                                 │           │
│        │         ┌─────────────────────────────────────────────────────────▼─────┐   │
│        │         │              FRONTEND HANDLES tool_approved                   │   │
│        │         │  1. Show "✅ Tool approved and executed" in chat             │   │
│        │         │  2. Remove from pendingApprovals state                       │   │
│        │         │  3. Highlight triggering message (amber left-border)        │   │
│        │         │  4. Update ApprovalHistoryPanel (add approved row)          │   │
│        │         │  4. Dashboard /approval-queue updates (persistent log)      │   │
│        │         └───────────────────────────────────────────────────────────────┘   │
│        │                                                                             │
└──────────────────────────────────────────────────────────────────────────────────────┘
        </pre>
      </SectionHeading>

      <SectionHeading id="sequence" kicker="7b.9" title="7b.9 Sequence Diagrams">
        <p>Detailed sequence diagrams for the approval lifecycle:</p>
        <div className="p-2 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap">
SEQUENCE: Tool Approval (Happy Path)

User          CortexChat        WebSocket         Backend API         Database
  │              │                 │                   │                   │
  │──Query─────►│                 │                   │                   │
  │             │──Reasoning─────►│                   │                   │
  │             │◄──tool_call─────│                   │                   │
  │             │                 │                   │                   │
  │             │  [Modal Opens]  │                   │                   │
  │             │                 │                   │                   │
  │             │◄──User Approve──│                   │                   │
  │             │                 │                   │                   │
  │             │──approve_tool──►│                   │                   │
  │             │                 │                   │──POST /tool-      │
  │             │                 │   approvals/&#123;id&#125;  │
  │             │                 │                   │──UPDATE
  │             │                 │                   │  tool_approvals
│             │                 │                   │  SET status=
│             │                 │                   │  "approved"
│             │                 │                   │  INSERT INTO
│             │                 │                   │  pulse_v2_ledger
│             │                 │◄──tool_approved──│                   │
│             │◄──✅ Tool approved                │                   │
│             │                 │                   │                   │
│             │                 │◄──ApprovalHist──│                   │
│             │                 │   Panel Update  │                   │
│             │                 │                   │                   │
</pre>
        </div>
        <div className="p-2 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap">
SEQUENCE: Tool Rejection (Security Denial)

Security      CortexChat        WebSocket         Backend API         Database
Officer       │                 │                   │                   │
  │              │                 │                   │                   │
  │             │◄──tool_call─────│                   │                   │
  │             │                 │                   │                   │
  │             │  [Modal Opens]  │                   │                   │
  │             │                 │                   │                   │
  │             │◄──User Deny─────│                   │                   │
  │             │  (with note)    │                   │                   │
  │             │                 │                   │                   │
  │             │──reject_tool────►│                   │                   │
  │             │   (with note)   │                   │                   │
  │             │                 │                   │──POST /tool-      │
  │             │                 │   approvals/&#123;id&#125;  │
  │             │                 │                   │──UPDATE
  │             │                 │                   │  tool_approvals
│             │                 │                   │  SET status=
│             │                 │                   │  "rejected"
│             │                 │◄──tool_rejected──│                   │
│             │◄──❌ Tool rejected                │                   │
│             │                 │                   │                   │
│             │                 │◄──ApprovalHist──│                   │
│             │                 │   Panel Update  │                   │
│             │                 │                   │                   │
</pre>
        </div>
        <div className="p-2 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap">
SEQUENCE: WebSocket Reconnection (Network Failure)

Client                              Server
  │                                    │
  │───ping (30s)────────────────────►│
  │                                    │
  │◄──pong (immediate)────────────────│
  │                                    │
  │ (network partition)                │
  │                                    │
  │ (90s timeout)                      │
  │                                    │
  │──reconnect (exponential backoff)─►│
  │                                    │
  │◄──connected (new session)─────────│
  │                                    │
  │───resume (after_seq=42)──────────►│
  │                                    │
  │◄──missed events (42-45)───────────│
  │                                    │
  │◄──latest state (sync)─────────────│
</pre>
        </div>
      </SectionHeading>

      <SectionHeading id="configuration" kicker="7b.10" title="7b.10 Configuration & Customization">
        <p>
          The approval system can be customized via environment variables and tenant policies:
        </p>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <p className="text-xs font-bold text-cyan-300 mb-2">Environment Variables:</p>
          <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto">
FAIM_APPROVAL_TIMEOUT_SECONDS=300
FAIM_APPROVAL_REQUIRE_NOTE=false
FAIM_APPROVAL_AUTO_APPROVE_LOW_RISK=true
FAIM_APPROVAL_WS_TIMEOUT=90000
FAIM_APPROVAL_WS_INTERVAL=30000
FAIM_APPROVAL_MAX_RECONNECTS=5
          </pre>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <p className="text-xs font-bold text-cyan-300 mb-2">Tenant Policy Configuration (JSON):</p>
          <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto">
&#123;
  "approval_policy": &#123;
    "default_action": "pending_review",
    "auto_approve_tools": ["storage_ingest", "search"],
    "require_note_on_reject": true,
    "require_note_on_approve": false,
    "auto_expire_hours": 24,
    "notify_on_pending": true,
    "escalation": &#123;
      "enabled": true,
      "after_hours": 4,
      "escalate_to": ["security@company.com", "admin@company.com"]
    &#125;
  &#125;
&#125;
          </pre>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-slate-700/50">
          <p className="text-xs font-bold text-cyan-300 mb-2">Frontend Customization (React Props):</p>
          <pre className="text-[9px] font-mono text-slate-400 overflow-x">
InlineApprovalModal props:
  approval=&#123;approvalObject&#125;
  onApprove=&#123;(id, note) =&gt; handleApprove(id, note)&#125;
  onReject=&#123;(id, note) =&gt; handleReject(id, note)&#125;
  onClose=&#123;() =&gt; setIsModalOpen(false)&#125;
  isLoading=&#123;false&#125;
  showArgsDefaultExpanded=&#123;true&#125;
  requireNote=&#123;false&#125;
  customActionLabels=&#123;&#123; approve: "Confirm", reject: "Decline", cancel: "Dismiss" &#125;&#125;

ApprovalHistoryPanel props:
  threadId=&#123;currentThreadId&#125;
  showFilter=&#123;true&#125;
  pageSize=&#123;20&#125;
  onRowClick=&#123;(approval) =&gt; &#123;&#125;&#125;
          </pre>
        </div>
      </SectionHeading>

      <SectionHeading id="troubleshooting" kicker="7b.11" title="7b.11 Troubleshooting & Best Practices">
        <p>Common issues and recommended practices:</p>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-rose-500/30">
          <p className="text-xs font-bold text-rose-300 mb-2">Issue: Modal doesn't appear when tool needs approval</p>
          <ul className="list-disc list-inside text-xs text-slate-400 space-y-1 ml-4">
            <li>Check WebSocket connection status in CortexChat header (should show "🟢 Live")</li>
            <li>Verify onToolCall callback is registered in useCortexWS</li>
            <li>Check browser console for JS errors</li>
            <li>Verify InlineApprovalModal is imported and rendered in CortexChat</li>
          </ul>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-amber-500/30">
          <p className="text-xs font-bold text-amber-300 mb-2">Issue: Approve/Deny buttons don't work</p>
          <ul className="list-disc list-inside text-xs text-slate-400 space-y-1 ml-4">
            <li>Check WS connection: approve_tool/reject_tool message sent</li>
            <li>Verify backend endpoint returns 200</li>
            <li>Check network tab for failed requests</li>
            <li>Verify approveTool/rejectTool from useCortexWS called correctly</li>
          </ul>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-emerald-500/30">
          <p className="text-xs font-bold text-emerald-300 mb-2">Best Practice: Always Add Context Notes</p>
          <ul className="list-disc list-inside text-xs text-slate-400 space-y-1 ml-4">
            <li>Require notes on rejection (audit trail for security)</li>
            <li>Encourage notes on approval (future auditors need context)</li>
            <li>Use structured notes: "Approved per policy X.Y.Z - ticket #1234"</li>
            <li>Enable FAIM_APPROVAL_REQUIRE_NOTE=true for compliance environments</li>
          </ul>
        </div>
        <div className="p-3 bg-slate-900/50 rounded-lg border border-cyan-500/30">
          <p className="text-xs font-bold text-cyan-300 mb-2">Best Practice: Sidebar Management</p>
          <ul className="list-disc list-inside text-xs text-slate-400 space-y-1 ml-4">
            <li>Keep sidebar closed on mobile (&lt;1024px) for maximum chat space</li>
            <li>Use localStorage to persist sidebarOpen preference</li>
            <li>Test on actual mobile devices</li>
            <li>Verify touch targets &gt;= 44px</li>
          </ul>
        </div>
      </SectionHeading>

      <SectionHeading id="workflow" kicker="7b.12" title="7b.12 Complete End-to-End Workflow">
        <p>
          The complete end-to-end workflow from user query to approval resolution:
        </p>
        <pre className="text-[9px] font-mono text-slate-400 overflow-x-auto whitespace-pre-wrap">
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE END-TO-END APPROVAL WORKFLOW                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  1. USER QUERY                                                                           │
│     ├─ User sends message in CortexChat (WebSocket or HTTP)                             │
│     └─ Cortex reasoning engine processes query                                          │
│                                                                                          │
│  2. TOOL CALL DETECTION                                                                  │
│     ├─ Cortex identifies tool requiring approval (e.g., storage_delete)                 │
│     ├─ Backend creates approval record: INSERT INTO tool_approvals (status='pending')  │
│     ├─ Backend emits WS: &#123;type: "tool_call", payload: &#123;approval_id: 42, tool_name, args, reason&#125;&#125;│
│     └─ Frontend receives via WebSocket onToolCall callback                              │
│                                                                                          │
│  3. INLINE MODAL PRESENTATION                                                            │
│     ├─ CortexChat sets: currentApproval=approval, isModalOpen=true                      │
│     ├─ InlineApprovalModal renders via ReactDOM.createPortal(document.body)            │
│     ├─ Modal displays: Tool name, ID, args (expandable), reason, note field            │
│     ├─ Focus trap: Tab cycles within modal, ESC closes, ⌘+Enter approves              │
│     └─ Chat turn BLOCKED until modal resolved                                           │
│                                                                                          │
│  4. USER DECISION                                                                        │
│     ├─ APPROVE path:                                                                    │
│     │  ├─ User clicks Approve (or ⌘+Enter)                                             │
│     │  ├─ Frontend sends: WS.send(&#123;type:"approve_tool", payload:&#123;approval_id, note&#125;&#125;) │
│     │  ├─ Backend: UPDATE tool_approvals SET status='approved', note=?, executed_at=NOW│
│     │  ├─ Backend executes tool, writes result to pulse_v2 ledger                      │
│     │  └─ Backend emits WS: &#123;type: "tool_approved", payload: &#123;approval_id, result&#125;&#125;   │
│     │                                                                                   │
│     └─ REJECT path:                                                                     │
│        ├─ User clicks Deny (or Escape)                                                 │
│        ├─ Frontend sends: WS.send(&#123;type:"reject_tool", payload:&#123;approval_id, note&#125;&#125;)  │
│        ├─ Backend: UPDATE tool_approvals SET status='rejected', note=?, rejected_at=NOW│
│        └─ Backend emits WS: &#123;type: "tool_rejected", payload: &#123;approval_id, reason&#125;&#125;   │
│                                                                                          │
│  5. FRONTEND RESOLUTION                                                                  │
│     ├─ CortexChat receives tool_approved/tool_rejected WS event                        │
│     ├─ Adds system message: "✅ Tool approved and executed" / "❌ Tool rejected"        │
│     ├─ Removes from pendingApprovals state                                             │
│     ├─ Highlights triggering message: border-l-4 border-amber-500 (2s fade)           │
│     ├─ Updates ApprovalHistoryPanel: adds row with status badge, timestamp, note      │
│     └─ Dashboard /approval-queue: new row appended (persistent log)                    │
│                                                                                          │
│  6. AUDIT & COMPLIANCE                                                                   │
│     ├─ All actions logged in tool_approvals table (immutable, append-only)             │
│     ├─ pulse_v2 ledger records: who, what, when, why, result                          │
│     ├─ Dashboard /approval-queue: full history with filters, export (CSV + SHA-256)   │
│     ├─ Compliance: SHA-256 hash of export verified on download                         │
│     └─ Retention: Configurable (default 7 years, GDPR/CCPA compliant)                 │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
        </pre>
      </SectionHeading>
    </ManualShell>
  );
};

export default CortexManual;
