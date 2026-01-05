"use client";

import React, { useEffect, useState } from "react";
import {
  Users,
  Database,
  FileText,
  Activity,
  Ban,
  CheckCircle,
  Server,
  ShieldAlert,
  ToggleLeft,
  ToggleRight,
  Scale,
  AlertTriangle,
} from "lucide-react";
import { getSession } from "next-auth/react";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("health");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Data State
  const [health, setHealth] = useState<any>(null);
  const [flags, setFlags] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);

  // Helper
  const fetchWithAuth = async (path: string) => {
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;
      const res = await fetch(path, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 403) throw new Error("Access Denied");
      if (!res.ok) return null;
      return res.json();
    } catch (e) {
      return null;
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      if (activeTab === "health") {
        setHealth(await fetchWithAuth("/api/ops/health"));
        setStats(await fetchWithAuth("/api/admin/stats"));
      } else if (activeTab === "flags") {
        setFlags((await fetchWithAuth("/api/ops/flags")) || []);
      } else if (activeTab === "legal") {
        setAudit((await fetchWithAuth("/api/ops/audit")) || []);
      } else if (activeTab === "tenants") {
        setUsers((await fetchWithAuth("/api/admin/users")) || []);
      }
    } catch (e: any) {
      setError(e.message || "Error loading data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeTab]);

  // Actions
  const toggleFlag = async (name: string, currentState: boolean) => {
    const session = await getSession();
    const token = (session as any)?.accessToken;
    await fetch(`/api/ops/flags/${name}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled: !currentState }),
    });
    loadData();
  };

  const toggleBan = async (userId: string, currentStatus: string) => {
    const action = currentStatus === "suspended" ? "unban" : "ban";
    const session = await getSession();
    const token = (session as any)?.accessToken;

    await fetch(`/api/admin/users/${userId}/${action}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    loadData();
  };

  if (error) return <div className="p-4 text-red-400 text-xs">{error}</div>;

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">
            Operator Control Panel
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            System health, feature flags, and tenant management.
          </p>
        </div>
        <div className="flex gap-1">
          {["health", "tenants", "legal", "flags"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-medium capitalize transition-colors ${activeTab === tab ? "bg-slate-700 text-slate-100" : "bg-slate-800/50 text-slate-500 hover:bg-slate-700/50"}`}
            >
              {tab}
            </button>
          ))}
        </div>
      </header>

      {loading && (
        <div className="text-xs text-slate-500 animate-pulse">Loading...</div>
      )}

      {/* HEALTH TAB */}
      {activeTab === "health" && !loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            {["db", "redis", "keycloak"].map((sys) => (
              <section
                key={sys}
                className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-2 capitalize font-medium text-xs text-slate-200">
                  <Server size={14} className="text-slate-500" /> {sys}
                </div>
                <div
                  className={`flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider ${health?.[sys] === "healthy" ? "text-emerald-400" : health?.[sys] === "offline" ? "text-amber-400" : "text-red-400"}`}
                >
                  <div
                    className={`w-1.5 h-1.5 rounded-full ${health?.[sys] === "healthy" ? "bg-emerald-400" : health?.[sys] === "offline" ? "bg-amber-400" : "bg-red-400"}`}
                  />
                  {health?.[sys] || "unknown"}
                </div>
              </section>
            ))}
          </div>

          <div className="grid grid-cols-4 gap-3">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="text-slate-500 text-[10px] uppercase mb-1">
                Total Users
              </div>
              <div className="text-xl font-bold text-slate-100">
                {stats?.total_users ?? "—"}
              </div>
            </section>
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="text-slate-500 text-[10px] uppercase mb-1">
                Total Graphs
              </div>
              <div className="text-xl font-bold text-slate-100">
                {stats?.total_graphs ?? "—"}
              </div>
            </section>
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="text-slate-500 text-[10px] uppercase mb-1">
                Total Projects
              </div>
              <div className="text-xl font-bold text-slate-100">
                {stats?.total_projects ?? "—"}
              </div>
            </section>
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
              <div className="text-slate-500 text-[10px] uppercase mb-1">
                Total Docs
              </div>
              <div className="text-xl font-bold text-slate-100">
                {stats?.total_docs ?? "—"}
              </div>
            </section>
          </div>
        </div>
      )}

      {/* FLAGS TAB */}
      {activeTab === "flags" && !loading && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60">
            <h2 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
              <ToggleRight size={14} /> Feature Flags
            </h2>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Live configuration toggles. Affects all users immediately.
            </p>
          </div>
          <div className="divide-y divide-slate-800">
            {(Array.isArray(flags) ? flags : []).map((f) => (
              <div
                key={f.name}
                className="p-3 flex items-center justify-between hover:bg-slate-800/30"
              >
                <div>
                  <div className="font-medium text-xs text-slate-200">
                    {f.name}
                  </div>
                  <div className="text-slate-500 text-[10px]">
                    {f.description}
                  </div>
                </div>
                <button
                  onClick={() => toggleFlag(f.name, f.is_enabled)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all text-[10px] ${f.is_enabled ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" : "bg-slate-800/50 border-slate-700 text-slate-500"}`}
                >
                  {f.is_enabled ? (
                    <ToggleRight size={16} />
                  ) : (
                    <ToggleLeft size={16} />
                  )}
                  <span className="uppercase font-bold tracking-wider">
                    {f.is_enabled ? "On" : "Off"}
                  </span>
                </button>
              </div>
            ))}
            {(!flags || flags.length === 0) && (
              <div className="p-4 text-center text-slate-500 text-xs italic">
                No feature flags configured.
              </div>
            )}
          </div>
        </section>
      )}

      {/* LEGAL TAB */}
      {activeTab === "legal" && !loading && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60">
            <h2 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
              <Scale size={14} /> Audit Log
            </h2>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Immutable record of sensitive actions.
            </p>
          </div>
          <div className="divide-y divide-slate-800">
            {(Array.isArray(audit) ? audit : []).slice(0, 20).map((log) => (
              <div
                key={log.id}
                className="p-3 flex items-center justify-between text-xs hover:bg-slate-800/30"
              >
                <div className="flex items-center gap-3">
                  <div className="text-slate-500 font-mono text-[10px]">
                    {new Date(log.ts).toLocaleString()}
                  </div>
                  <div className="font-medium text-slate-200">{log.action}</div>
                </div>
                <div
                  className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${log.outcome === "success" ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}
                >
                  {log.outcome}
                </div>
              </div>
            ))}
            {(!audit || audit.length === 0) && (
              <div className="p-4 text-center text-slate-500 text-xs italic">
                No audit logs recorded yet.
              </div>
            )}
          </div>
        </section>
      )}

      {/* TENANTS TAB */}
      {activeTab === "tenants" && !loading && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="p-4 border-b border-slate-800 bg-slate-900/60">
            <h2 className="text-xs font-semibold text-slate-100 flex items-center gap-2">
              <Users size={14} /> All Users
            </h2>
            <p className="text-[10px] text-slate-500 mt-0.5">
              Manage user accounts and access.
            </p>
          </div>
          <div className="divide-y divide-slate-800">
            {(Array.isArray(users) ? users : []).map((user) => (
              <div
                key={user.id}
                className="p-3 flex items-center justify-between hover:bg-slate-800/30"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 text-xs font-bold">
                    {(user.full_name || user.email || "?")[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="font-medium text-xs text-slate-200">
                      {user.full_name || user.email}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {user.email}
                    </div>
                    <div className="text-[10px] text-cyan-400/70">
                      {user.graph_id || "No graph"}
                      {user.email_verified
                        ? " • ✓ Verified"
                        : " • ⚠ Unverified"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${user.status === "active" ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}
                  >
                    {user.status}
                  </div>
                  <button
                    onClick={() => toggleBan(user.id, user.status)}
                    className={`p-1.5 rounded-lg transition-colors ${user.status === "suspended" ? "text-emerald-400 hover:bg-emerald-400/10" : "text-red-400 hover:bg-red-400/10"}`}
                    title={
                      user.status === "suspended" ? "Unban User" : "Ban User"
                    }
                  >
                    {user.status === "suspended" ? (
                      <CheckCircle size={14} />
                    ) : (
                      <Ban size={14} />
                    )}
                  </button>
                </div>
              </div>
            ))}
            {(!users || users.length === 0) && (
              <div className="p-4 text-center text-slate-500 text-xs italic">
                No users found.
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
