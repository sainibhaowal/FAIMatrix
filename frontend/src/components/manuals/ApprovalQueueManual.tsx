"use client";

import React from "react";
import {
  ManualShell,
  SectionHeading,
  SubHeading,
  Callout,
  DTable,
  type TocItem,
} from "@/components/manuals/ManualShell";

const TOC: TocItem[] = [
  { id: "overview", label: "1. Introduction" },
  { id: "stats", label: "2. Stats Scorecard" },
  { id: "filters", label: "3. Filters & Limit" },
  { id: "table", label: "4. Approvals Table", children: [{ id: "table-cols", label: "Columns" }, { id: "table-status", label: "Status & Execution" }] },
  { id: "decide", label: "5. Approve / Reject", children: [{ id: "decide-approve", label: "Approve" }, { id: "decide-reject", label: "Reject" }] },
  { id: "flow", label: "6. End-to-End Flow" },
  { id: "security", label: "7. Security & Audit" },
  { id: "troubleshoot", label: "8. Troubleshooting" },
];

export function ApprovalQueueManual({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <ManualShell
      open={open}
      onClose={onClose}
      title="FAIM Approval Queue — User Manual"
      subtitle="Human-in-the-Loop Tool Approval Management"
      toc={TOC}
    >
      <SectionHeading id="overview" kicker="Chapter 01" title="Introduction">
        <p>
          The Approval Queue is FAIM's human-in-the-loop safety gate. When the
          Cortex agent wants to run a privileged tool (for example, a storage
          delete or a graph mutation), the request is <em>proposed</em> instead
          of executed. An authorized reviewer approves or rejects it here —
          nothing destructive ever happens without a human decision.
        </p>
        <Callout tone="success" title="Safety by default">
          Every tool call is recorded with its arguments, proposer, and full
          decision trail. Approve, reject, or leave pending — the ledger never
          forgets.
        </Callout>
      </SectionHeading>

      <SectionHeading id="stats" kicker="Chapter 02" title="Stats Scorecard">
        <p>
          Four cards summarize the queue at a glance:
        </p>
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Card", "Color", "Meaning"]}
          rows={[
            { cells: ["Total", <span key="total" className="text-slate-300">neutral</span>, "All approval records in the queue"] },
            { cells: ["Pending", <span key="pending" className="text-amber-300">amber</span>, "Awaiting a human decision"] },
            { cells: ["Approved", <span key="approved" className="text-emerald-300">emerald</span>, "Granted and (normally) executed"] },
            { cells: ["Rejected", <span key="rejected" className="text-rose-300">rose</span>, "Denied with a recorded reason"] },
          ]}
        />
      </SectionHeading>

      <SectionHeading id="filters" kicker="Chapter 03" title="Filters & Limit">
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Status</strong> — filter by pending, approved, or rejected.</li>
          <li><strong>Tool</strong> — filter to a specific tool (e.g. a storage or graph tool).</li>
          <li><strong>Limit</strong> — cap how many records load (1–200, default 50).</li>
        </ul>
        <Callout tone="info" title="Filters are client-side">
          Filtering narrows the already-loaded page. Use Refresh to pull the
          latest records from the backend.
        </Callout>
      </SectionHeading>

      <SectionHeading id="table" kicker="Chapter 04" title="Approvals Table">
        <SubHeading id="table-cols">Columns</SubHeading>
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Column", "Shows"]}
          rows={[
            { cells: ["ID", "Numeric record id"] },
            { cells: ["Tool", "Which tool the agent wanted to invoke"] },
            { cells: ["Status", "pending / approved / rejected"] },
            { cells: ["Tenant / Graph", "Tenant id and graph the action targets"] },
            { cells: ["Args Preview", "First 60 chars of the serialized arguments"] },
            { cells: ["Created", "Timestamp the request was proposed"] },
            { cells: ["Actions", "View / Approve / Reject controls"] },
          ]}
        />
        <SubHeading id="table-status">Status & Execution</SubHeading>
        <p>
          Beyond the decision status, each record carries an{" "}
          <span className="font-mono text-cyan-300">execution_status</span>:
        </p>
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Execution", "Icon", "Meaning"]}
          rows={[
            { cells: ["executed", <span key="executed" className="text-emerald-300">✓ Executed</span>, "The approved action ran successfully"] },
            { cells: ["failed", <span key="failed" className="text-rose-300">✗ Failed</span>, "Approved but execution errored"] },
            { cells: ["skipped", <span key="skipped" className="text-amber-300">⊘ Skipped</span>, "Approved but not run (e.g. superseded)"] },
            { cells: ["pending", <span key="execution-pending" className="text-slate-400">—</span>, "Not yet executed"] },
          ]}
        />
      </SectionHeading>

      <SectionHeading id="decide" kicker="Chapter 05" title="Approve / Reject">
        <p>Only pending records expose decision buttons.</p>
        <SubHeading id="decide-approve">Approve</SubHeading>
        <p>
          Click <span className="font-mono text-emerald-300">Approve</span> to
          authorize the action. The system records a note
          ("Approved via admin UI") and, if the tool supports it, executes the
          action — the row then reflects its execution status.
        </p>
        <SubHeading id="decide-reject">Reject</SubHeading>
        <p>
          Click <span className="font-mono text-rose-300">Reject</span> to deny
          the action. You are prompted for a reason; the default is
          "Rejected via admin UI". The rejection reason is stored for audit.
        </p>
        <Callout tone="warn" title="Decisions are final">
          Once a record is approved or rejected it can no longer be decided
          again. Re-run the agent if you need a fresh attempt.
        </Callout>
      </SectionHeading>

      <SectionHeading id="flow" kicker="Chapter 06" title="End-to-End Flow">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Step", "Who", "What happens"]}
          rows={[
            { cells: ["1 · Propose", "Agent", "Cortex invokes a privileged tool; request is queued as pending instead of running"] },
            { cells: ["2 · Review", "Human", "Reviewer reads the args, tenant, graph and reason in the table"] },
            { cells: ["3 · Decide", "Human", "Approve (execute) or Reject (deny with note)"] },
            { cells: ["4 · Execute", "System", "Approved actions run; execution status is recorded"] },
            { cells: ["5 · Audit", "System", "Full trail persisted: proposer, decision_by, note, timestamps, receipt"] },
          ]}
        />
      </SectionHeading>

      <SectionHeading id="security" kicker="Chapter 07" title="Security & Audit">
        <ul className="list-disc space-y-1 pl-5">
          <li>Every record tracks <span className="font-mono">proposed_by</span> and <span className="font-mono">decision_by</span>.</li>
          <li>Decision notes are stored verbatim for compliance.</li>
          <li>Approvals are tenant-scoped — reviewers only see their tenant.</li>
          <li>A <span className="font-mono">receipt</span> JSON captures execution outcome.</li>
        </ul>
      </SectionHeading>

      <SectionHeading id="troubleshoot" kicker="Chapter 08" title="Troubleshooting">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Problem", "Cause", "Fix"]}
          rows={[
            { cells: ["Empty queue", "No pending/other records or filters active", "Clear status/tool filters, Refresh"] },
            { cells: ["Approve fails", "Action no longer executable or expired", "Check error alert; ask agent to re-propose"] },
            { cells: ["Wrong tenant data", "Tenant id filter scoped elsewhere", "Confirm the tenant id in use"] },
            { cells: ["Slow load", "Large limit with many records", "Lower the limit (e.g. 25)"] },
          ]}
        />
      </SectionHeading>
    </ManualShell>
  );
}
