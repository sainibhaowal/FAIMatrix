"use client";

import React, { useState, useRef } from "react";
import { useSession } from "next-auth/react";
import { 
  GraphSummary, 
  API_BASE_URL, 
  DEFAULT_GRAPH_ID, 
  isRemoteApiBase, 
  buildFaimHeaders, 
} from "@/lib/api";
import { IconChevron } from "./IconChevron";
import { Dropdown } from "./Dropdown";
import { Shield, User, Network, Database, Copy, Check } from "lucide-react";

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function WorkspaceSelector({
  graphId,
  setGraphId,
  graphs,
  graphsLoaded,
  setGraphs,
  currentGraphName
}: {
  graphId: string;
  setGraphId: (v: string) => void;
  graphs: GraphSummary[];
  graphsLoaded: boolean;
  setGraphs: React.Dispatch<React.SetStateAction<GraphSummary[]>>;
  currentGraphName: string;
}) {
  const { data: session, status } = useSession();
  const [openWorkspace, setOpenWorkspace] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const wsRef = useRef<HTMLButtonElement>(null);

  // User identity info - use session if available, fallback to graphId prop
  const userId = (session?.user as any)?.id || "";
  const userEmail = session?.user?.email || "";
  const userGraphId = (session as any)?.graphId || graphId;
  const tenantId = userId || graphId.replace("U:", "");
  const isLoggedIn = status === "authenticated";

  const copyToClipboard = (id: string, label: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(label);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const renameWorkspace = async (g: GraphSummary) => {
    const name = window.prompt("Rename workspace:", g.name);
    if (!name || name.trim() === g.name) return;

    setGraphs((prev) =>
      prev.map((x) => (x.id === g.id ? { ...x, name: name.trim() } : x)),
    );
    setOpenWorkspace(false);

    try {
      if (!isRemoteApiBase()) return;
      const base = (API_BASE_URL || "").trim().replace(/\/+$/, "");
      await fetch(`${base}/graphs/${encodeURIComponent(g.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...buildFaimHeaders() },
        body: JSON.stringify({ name: name.trim() }),
      });
    } catch {}
  };

  return (
    <div className="relative">
      <button
        ref={wsRef}
        onClick={() => setOpenWorkspace((v) => !v)}
        className={cx(
          "flex min-w-0 items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs",
          "hover:border-white/15 hover:bg-white/5",
        )}
        title="Workspace (graph context)"
      >
        <span className="text-slate-300/70">Workspace</span>
        <span className="mx-1 h-3 w-px bg-white/10" />
        <span className="truncate text-slate-100">
          {currentGraphName}
        </span>
        <IconChevron className="h-4 w-4 text-slate-300/70" />
      </button>

      <Dropdown
        open={openWorkspace}
        anchorRef={wsRef}
        onClose={() => setOpenWorkspace(false)}
        className="left-0 right-auto w-[400px]"
      >
        <div className="p-3">
          {/* User Identity Section - Always visible */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4 text-emerald-400" />
              <span className="text-[11px] font-semibold text-slate-200">
                Your Identity
              </span>
              <span className="ml-auto px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-[9px] font-medium text-emerald-300">
                {isLoggedIn ? "ISOLATED" : "GUEST"}
              </span>
            </div>
            
            <div className="rounded-xl border border-white/10 bg-black/20 divide-y divide-white/5">
              {/* User ID */}
              <div className="flex items-center gap-3 px-3 py-2">
                <User className="h-3.5 w-3.5 text-cyan-400" />
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] text-slate-500">User ID</div>
                  <div className="text-[11px] text-slate-200 font-mono truncate">
                    {userId || userEmail || "(not signed in)"}
                  </div>
                </div>
                {userId && (
                  <button
                    onClick={() => copyToClipboard(userId, "userId")}
                    className="p-1 rounded hover:bg-white/10"
                    title="Copy User ID"
                  >
                    {copiedId === "userId" ? (
                      <Check className="h-3 w-3 text-emerald-400" />
                    ) : (
                      <Copy className="h-3 w-3 text-slate-500" />
                    )}
                  </button>
                )}
              </div>

              {/* Graph ID (Universe) */}
              <div className="flex items-center gap-3 px-3 py-2">
                <Network className="h-3.5 w-3.5 text-purple-400" />
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] text-slate-500">Graph ID (Universe)</div>
                  <div className="text-[11px] text-slate-200 font-mono truncate">
                    {userGraphId}
                  </div>
                </div>
                <button
                  onClick={() => copyToClipboard(userGraphId, "graphId")}
                  className="p-1 rounded hover:bg-white/10"
                  title="Copy Graph ID"
                >
                  {copiedId === "graphId" ? (
                    <Check className="h-3 w-3 text-emerald-400" />
                  ) : (
                    <Copy className="h-3 w-3 text-slate-500" />
                  )}
                </button>
              </div>

              {/* Tenant ID */}
              <div className="flex items-center gap-3 px-3 py-2">
                <Database className="h-3.5 w-3.5 text-amber-400" />
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] text-slate-500">Tenant ID (DB Partition)</div>
                  <div className="text-[11px] text-slate-200 font-mono truncate">
                    {tenantId.length > 20 ? tenantId.slice(0, 20) + "..." : tenantId}
                  </div>
                </div>
                <button
                  onClick={() => copyToClipboard(tenantId, "tenantId")}
                  className="p-1 rounded hover:bg-white/10"
                  title="Copy Tenant ID"
                >
                  {copiedId === "tenantId" ? (
                    <Check className="h-3 w-3 text-emerald-400" />
                  ) : (
                    <Copy className="h-3 w-3 text-slate-500" />
                  )}
                </button>
              </div>
            </div>
            
            <div className="mt-2 text-[9px] text-slate-500">
              All your memories are isolated by tenant_id. No other user can access your data.
            </div>
          </div>
        </div>
      </Dropdown>
    </div>
  );
}
