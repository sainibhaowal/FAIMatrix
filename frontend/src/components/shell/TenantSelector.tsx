"use client";

import React, { useEffect, useState } from "react";
import { ChevronDown, Building, FolderGit2 } from "lucide-react";
import { getSession } from "next-auth/react";

// Types matching /v1/orgs and /v1/projects
type Org = { id: string; name: string; role: string };
type Project = { id: string; name: string; plan: string };

export function TenantSelector() {
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<Org | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch logic
  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const session = await getSession();
        // If no session, we can't fetch tenants.
        if (!session || !(session as any).accessToken) {
          return;
        }

        const token = (session as any).accessToken;
        const headers = { Authorization: `Bearer ${token}` };
        const apiBase = (
          process.env.NEXT_PUBLIC_FAIM_API_BASE_URL || "/api/v1"
        ).replace(/\/+$/, "");

        // 1. Fetch Orgs
        const resOrgs = await fetch(`${apiBase}/orgs`, { headers });
        if (resOrgs.ok) {
          const dataOrgs: Org[] = await resOrgs.json();
          setOrgs(dataOrgs);
          if (dataOrgs.length > 0) setSelectedOrg(dataOrgs[0]);
        }
      } catch (err) {
        console.warn("TenantSelector fetch error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // When org changes, fetch projects (mock logic for now for brevity, or real if endpoint ready)
  useEffect(() => {
    if (!selectedOrg) return;
    // Real impl would fetch `/v1/projects?org_id=...`
    // For visual stub, just set a placeholder or fetch if backend ready
  }, [selectedOrg]);

  if (loading)
    return (
      <div className="text-xs text-white/40 px-4 py-2">Loading context...</div>
    );

  // Fallback if no orgs found (e.g. backend down or new user)
  if (orgs.length === 0) {
    return (
      <div className="mb-4 px-4 py-2">
        <div className="text-xs text-white/40 uppercase tracking-widest font-semibold mb-1">
          Context
        </div>
        <div className="flex items-center gap-2 text-sm text-white/60">
          <Building size={14} />
          <span>Personal</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 space-y-2 px-2">
      {/* ORG SELECTOR */}
      <div className="group relative">
        <button className="flex w-full items-center justify-between rounded-xl border border-white/5 bg-white/5 px-3 py-2 text-left text-sm text-slate-300 hover:border-white/10 hover:bg-white/10 transition-colors">
          <div className="flex items-center gap-2 overflow-hidden">
            <Building size={14} className="text-cyan-400/70" />
            <span className="truncate">
              {selectedOrg?.name || "Select Org"}
            </span>
          </div>
          <ChevronDown size={14} className="opacity-50" />
        </button>
      </div>

      {/* PROJECT SELECTOR */}
      <div className="group relative">
        <button className="flex w-full items-center justify-between rounded-xl border border-white/5 bg-transparent px-3 py-2 text-left text-sm text-slate-400 hover:border-white/10 hover:bg-white/5 transition-colors">
          <div className="flex items-center gap-2 overflow-hidden">
            <FolderGit2 size={14} className="text-purple-400/60" />
            <span className="truncate">
              {selectedProject?.name || "Default Project"}
            </span>
          </div>
          <ChevronDown size={14} className="opacity-50" />
        </button>
      </div>
    </div>
  );
}
