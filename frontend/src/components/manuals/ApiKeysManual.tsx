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
  { id: "auth", label: "2. Authentication Headers", children: [{ id: "auth-headers", label: "Header Format" }] },
  { id: "lifecycle", label: "3. Key Lifecycle", children: [{ id: "lc-create", label: "Create" }, { id: "lc-use", label: "Use" }, { id: "lc-rotate", label: "Rotate" }, { id: "lc-revoke", label: "Revoke" }] },
  { id: "scopes", label: "4. Scopes & Permissions" },
  { id: "ui", label: "5. UI Guide", children: [{ id: "ui-matrix", label: "Key Matrix" }, { id: "ui-audit", label: "Audit Trail" }] },
  { id: "security", label: "6. Security & Tenant Isolation" },
  { id: "troubleshoot", label: "7. Troubleshooting" },
];

export function ApiKeysManual({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <ManualShell
      open={open}
      onClose={onClose}
      title="FAIM API Keys — User Manual"
      subtitle="Secure Access Matrix · Tenant-Scoped Lifecycle"
      toc={TOC}
    >
      <SectionHeading id="overview" kicker="Chapter 01" title="Introduction">
        <p>
          FAIM API keys protect every programmatic access to the platform. Each
          key belongs to exactly one tenant, carries explicit scopes, and is
          rotated and revoked through a clean lifecycle — so access is always
          auditable and always revocable.
        </p>
        <Callout tone="info" title="One-time reveal">
          The plaintext key is shown exactly once, at creation time. Store it
          immediately — it can never be displayed again.
        </Callout>
      </SectionHeading>

      <SectionHeading id="auth" kicker="Chapter 02" title="Authentication Headers">
        <SubHeading id="auth-headers">Header Format</SubHeading>
        <p>Every API request carries two headers:</p>
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Header", "Value", "Purpose"]}
          rows={[
            { cells: [<span key="api-key" className="font-mono text-cyan-300">X-Api-Key</span>, "the plaintext key", "Proves possession of the credential"] },
            { cells: [<span key="tenant-id" className="font-mono text-cyan-300">X-Tenant-Id</span>, "tenant id (e.g. default)", "Selects the tenant namespace"] },
          ]}
        />
        <Callout tone="warn" title="Tenant isolation">
          A key minted for tenant A will never authenticate as tenant B — the
          tenant id is bound to the key at creation.
        </Callout>
      </SectionHeading>

      <SectionHeading id="lifecycle" kicker="Chapter 03" title="Key Lifecycle">
        <SubHeading id="lc-create">Create</SubHeading>
        <p>
          Click <span className="font-mono text-cyan-300">Create Key</span>,
          pick the tenant, and select scopes. The system mints a key id
          (shown as a short prefix in the matrix) plus a plaintext secret
          shown once.
        </p>
        <SubHeading id="lc-use">Use</SubHeading>
        <p>
          Send the secret in <span className="font-mono text-cyan-300">X-Api-Key</span>{" "}
          on every request. The matrix records the last-used timestamp so you
          can see which keys are actively in production.
        </p>
        <SubHeading id="lc-rotate">Rotate</SubHeading>
        <p>
          Rotation mints a successor key while the old key stays valid for a
          grace window — letting you swap credentials without an outage. The
          rotated-from relationship is stored on both records.
        </p>
        <SubHeading id="lc-revoke">Revoke</SubHeading>
        <p>
          Revocation immediately invalidates the key. A revoked key appears in
          the matrix with its reason and timestamp, so the full history is
          preserved.
        </p>
      </SectionHeading>

      <SectionHeading id="scopes" kicker="Chapter 04" title="Scopes & Permissions">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Scope", "Allows"]}
          rows={[
            { cells: [<span key="storage-read" className="font-mono">storage.read</span>, "List and inspect stored files and provenance"] },
            { cells: [<span key="storage-write" className="font-mono">storage.write</span>, "Upload and ingest new files"] },
            { cells: [<span key="storage-approve" className="font-mono">storage.approve</span>, "Approve or reject pending storage actions"] },
            { cells: [<span key="graph-read" className="font-mono">graph.read</span>, "Read knowledge graph state"] },
            { cells: [<span key="graph-write" className="font-mono">graph.write</span>, "Mutate the knowledge graph"] },
            { cells: [<span key="keys-manage" className="font-mono">keys.manage</span>, "Create, rotate and revoke API keys"] },
            { cells: [<span key="cortex-chat" className="font-mono">cortex.chat</span>, "Use the Cortex reasoning/chat engine"] },
          ]}
        />
      </SectionHeading>

      <SectionHeading id="ui" kicker="Chapter 05" title="UI Guide">
        <SubHeading id="ui-matrix">Key Matrix</SubHeading>
        <p>
          The matrix shows total, active, and revoked counts, then lists each
          key with prefix, scopes, status, created/expires/revoked dates and
          last-used. The refresh button reloads the live list.
        </p>
        <SubHeading id="ui-audit">Audit Trail</SubHeading>
        <p>
          Every lifecycle event — create, rotate, revoke — is appended to an
          audit log with a timestamp and actor. This trail is read-only and
          cannot be edited by users.
        </p>
      </SectionHeading>

      <SectionHeading id="security" kicker="Chapter 06" title="Security & Tenant Isolation">
        <ul className="list-disc space-y-1 pl-5">
          <li>Secrets are stored hashed server-side; only the prefix is ever returned.</li>
          <li>Keys are bound to a single tenant and cannot cross tenants.</li>
          <li>Revoked keys are rejected immediately.</li>
          <li>Rotation preserves continuity while tightening exposure.</li>
          <li>Audit trail is append-only for accountability.</li>
        </ul>
      </SectionHeading>

      <SectionHeading id="troubleshoot" kicker="Chapter 07" title="Troubleshooting">
{/* eslint-disable-next-line react/jsx-key */}
        <DTable
          head={["Problem", "Cause", "Fix"]}
          rows={[
            { cells: ["401 Unauthorized", "Wrong or revoked key", "Re-check header, rotate or recreate"] },
            { cells: ["403 Forbidden", "Scope missing", "Issue a key with the required scope"] },
            { cells: ["Key not visible", "Filtered by include_revoked", "Toggle revoked visibility"] },
            { cells: ["Can't create key", "No keys.manage scope on your key", "Ask a key manager"] },
          ]}
        />
      </SectionHeading>
    </ManualShell>
  );
}
