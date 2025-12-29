"use client";

import React, { useEffect, useState } from "react";
import { Copy, Plus, Trash2, ShieldAlert } from "lucide-react";
import { getSession } from "next-auth/react";

// Types
type APIKey = {
    id: string;
    name: string;
    key_prefix: string;
    created_at: string;
    status: string;
    scopes: string[];
};

export default function ApiKeysPage() {
    const [keys, setKeys] = useState<APIKey[]>([]);
    const [loading, setLoading] = useState(true);
    const [newKey, setNewKey] = useState<string | null>(null);
    const [error, setError] = useState("");

    const [createName, setCreateName] = useState("");
    const [isCreating, setIsCreating] = useState(false);

    // Determine Project Context (for Phase 2 MVP we might just fetch *all* user's keys or default project's)
    // Ideally this page should be under /org/[orgId]/project/[projectId]/settings
    // But for simple /settings/keys, we'll fetch the first available project or just pass a hardcoded project_id if needed.
    // Wait, router_keys_v2 requires `project_id`. Frontend must know usage context.
    // We'll resort to resolving project from /v1/projects first or assume user has one context.
    // For this demo, let's assume we can fetch projects and use the first one.

    const [projectId, setProjectId] = useState<string | null>(null);

    useEffect(() => {
        async function init() {
            setLoading(true);
            try {
                const session = await getSession();
                const token = (session as any)?.accessToken;

                // In dev mode, API works without token. Only add header if token exists.
                const headers: Record<string, string> = {};
                if (token) {
                    headers["Authorization"] = `Bearer ${token}`;
                }

                // Fetch orgs
                const resOrgs = await fetch("/api/v1/orgs", { headers });
                const orgs = await resOrgs.json();
                if (!Array.isArray(orgs) || orgs.length === 0) {
                    setError("No organization found. Please create one first.");
                    return;
                }

                const orgId = orgs[0].id;

                // Fetch projects
                const resProjs = await fetch(`/api/v1/projects?org_id=${orgId}`, { headers });
                const projects = await resProjs.json();
                if (!Array.isArray(projects) || projects.length === 0) {
                    setError("No project found. Please create one first.");
                    return;
                }

                const pid = projects[0].id;
                setProjectId(pid);

                // Load existing keys
                const resKeys = await fetch(`/api/v1/api_keys?project_id=${pid}`, { headers });
                if (resKeys.ok) {
                    const keysData = await resKeys.json();
                    setKeys(Array.isArray(keysData) ? keysData : []);
                }
            } catch (err: any) {
                console.error(err);
                setError(err.message || "Failed to load");
            } finally {
                setLoading(false);
            }
        }
        init();
    }, []);

    const handleCreate = async () => {
        if (!createName || !projectId) return;
        setIsCreating(true);
        try {
            const session = await getSession();
            const token = (session as any)?.accessToken;

            const headers: Record<string, string> = {
                "Content-Type": "application/json"
            };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const res = await fetch("/api/v1/api_keys", {
                method: "POST",
                headers,
                body: JSON.stringify({
                    project_id: projectId,
                    name: createName,
                    scopes: ["graph:read", "graph:write"]
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to create key");
            }

            const data = await res.json();
            setNewKey(data.full_key); // ONLY SHOWN ONCE
            setKeys([...keys, { ...data, status: "active" }]);
            setCreateName("");
        } catch (err: any) {
            alert(err.message || "Error creating key");
        } finally {
            setIsCreating(false);
        }
    };

    const handleRevoke = async (id: string) => {
        if (!confirm("Are you sure? This application will lose access immediately.")) return;
        try {
            const session = await getSession();
            const token = (session as any)?.accessToken;

            await fetch(`/api/v1/api_keys/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` }
            });

            setKeys(keys.filter(k => k.id !== id));
        } catch (err) {
            alert("Error revoking key");
        }
    };

    return (
        <div className="space-y-4">
            <header className="flex items-start justify-between gap-3">
                <div>
                    <h1 className="text-sm font-semibold text-slate-100">Developer Keys</h1>
                    <p className="mt-1 text-xs text-slate-400">Manage API keys for accessing your FAIM graphs programmatically.</p>
                </div>
            </header>

            {loading && <div className="text-xs text-slate-500 animate-pulse">Loading context...</div>}
            {error && <div className="text-red-400 bg-red-400/10 p-3 rounded-xl text-xs mb-4">{error}</div>}

            {/* CREATE SECTION */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 mb-4">
                <h2 className="text-xs font-semibold text-slate-100 mb-3">Generate New Key</h2>
                <div className="flex gap-3">
                    <input
                        type="text"
                        value={createName}
                        onChange={e => setCreateName(e.target.value)}
                        placeholder="Key Name (e.g. Mobile App)"
                        className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-cyan-500/50 transition-colors placeholder:text-slate-600"
                    />
                    <button
                        onClick={handleCreate}
                        disabled={!createName || isCreating || !projectId}
                        className="bg-cyan-500 hover:bg-cyan-400 text-black font-semibold px-4 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-xs"
                    >
                        {isCreating ? "Generating..." : <><Plus size={14} /> Generate</>}
                    </button>
                </div>

                {/* SUCCESS MODAL / INLINE */}
                {newKey && (
                    <div className="mt-4 bg-cyan-900/20 border border-cyan-500/30 rounded-xl p-3">
                        <div className="flex items-start gap-3">
                            <ShieldAlert className="text-cyan-400 shrink-0 mt-0.5" size={16} />
                            <div className="flex-1 overflow-hidden">
                                <div className="font-semibold text-cyan-100 text-xs mb-1">Key Generated Successfully</div>
                                <div className="text-[10px] text-cyan-200/60 mb-2">
                                    Copy this key now. You won't be able to see it again!
                                </div>
                                <div className="flex items-center gap-2 bg-black/60 rounded-lg px-2 py-1.5 font-mono text-[10px] text-cyan-300 break-all">
                                    <span>{newKey}</span>
                                    <button
                                        onClick={() => navigator.clipboard.writeText(newKey)}
                                        className="ml-auto hover:text-white transition-colors"
                                    >
                                        <Copy size={12} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </section>

            {/* LIST SECTION */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
                <h2 className="text-xs font-semibold text-slate-100 mb-3">Active Keys</h2>
                {keys.length === 0 && !loading && (
                    <div className="text-slate-500 italic text-xs">No API keys found.</div>
                )}
                <div className="space-y-2">
                    {keys.map(key => (
                        <div key={key.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-700/50 bg-slate-800/30 hover:bg-slate-800/50 transition-colors group">
                            <div>
                                <div className="font-medium text-slate-200 text-xs">{key.name}</div>
                                <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                                    {key.key_prefix}... • Created {new Date(key.created_at).toLocaleDateString()}
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="px-2 py-0.5 rounded bg-slate-700/50 text-[9px] text-slate-400 uppercase tracking-wider">
                                    {key.status}
                                </div>
                                <button
                                    onClick={() => handleRevoke(key.id)}
                                    className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-400/10 transition-all opacity-0 group-hover:opacity-100"
                                    title="Revoke Key"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
