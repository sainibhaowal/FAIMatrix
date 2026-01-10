"use client";

import React, { useState, useRef } from "react";
import { 
  GraphSummary, 
  API_BASE_URL, 
  DEFAULT_GRAPH_ID, 
  isRemoteApiBase, 
  buildFaimHeaders, 
} from "../../../lib/api";
import { IconChevron } from "./IconChevron";
import { Dropdown } from "./Dropdown";

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
  const [openWorkspace, setOpenWorkspace] = useState(false);
  const wsRef = useRef<HTMLButtonElement>(null);

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
        className="left-0 right-auto w-[360px]"
      >
        <div className="p-3">
          <div className="mb-2">
            <div className="text-[11px] font-semibold text-slate-200">
              Workspaces
            </div>
          </div>

          <div className="mb-2 text-[10px] text-slate-500">
            Scope for memory, metrics, FIG, and retrieval. (graph_id stays
            internal)
          </div>

          <div className="max-h-[280px] overflow-y-auto rounded-xl border border-white/10">
            {graphsLoaded && graphs.length === 0 ? (
              <div className="px-3 py-6 text-center text-[11px] text-slate-500">
                No workspaces found.
              </div>
            ) : (
              <ul className="divide-y divide-white/10">
                {graphs.map((g) => {
                  const active = g.id === graphId;
                  return (
                    <li
                      key={g.id}
                      className={cx("px-3 py-2", active && "bg-white/5")}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <button
                          className="min-w-0 flex-1 text-left"
                          onClick={() => {
                            setGraphId(g.id);
                            setOpenWorkspace(false);
                          }}
                          title={`id: ${g.id}`}
                        >
                          <div className="truncate text-[12px] font-medium text-slate-100">
                            {g.name}
                          </div>
                          <div className="truncate text-[10px] text-slate-500">
                            id: {g.id}
                          </div>
                        </button>

                        <div className="flex items-center gap-1">
                          <button
                            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200 hover:bg-white/10"
                            onClick={() => renameWorkspace(g)}
                          >
                            Rename
                          </button>
                          <button
                            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] text-slate-200 hover:bg-white/10"
                            onClick={() => {
                              navigator.clipboard.writeText(g.id);
                              alert(`Copied ID: ${g.id}`);
                            }}
                          >
                            Copy ID
                          </button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="mt-2 text-[10px] text-slate-500">
            Tip: In production, show only display name; id stays internal
            (uuid/slug).
          </div>
        </div>
      </Dropdown>
    </div>
  );
}
