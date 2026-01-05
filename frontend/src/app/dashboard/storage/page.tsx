"use client";

import React, { useEffect, useState } from "react";
import { UploadCloud, FileText, CheckCircle, Clock, AlertCircle, HardDrive, Trash2, Download } from "lucide-react";
import { getSession } from "next-auth/react";
import { useUserIds } from "@/contexts/UserContext";

type Doc = {
    id: string;
    filename: string;
    status: string;
    created_at: string;
    file_size_bytes: number;
};

export default function StoragePage() {
    const [docs, setDocs] = useState<Doc[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const { projectId: contextProjectId, graphId: contextGraphId } = useUserIds();
    const [projectId, setProjectId] = useState<string | null>(null);

    useEffect(() => {
        if (contextProjectId) {
            setProjectId(contextProjectId);
        }
    }, [contextProjectId]);

    useEffect(() => {
        async function init() {
            if (!projectId) return;

            try {
                const session = await getSession();
                const token = (session as any)?.accessToken;

                // Headers with optional auth
                const headers: Record<string, string> = {};
                if (token) {
                    headers["Authorization"] = `Bearer ${token}`;
                }

                // Load existing documents
                try {
                    const resDocs = await fetch(`/api/v1/storage/files?project_id=${projectId}`, { headers });
                    if (resDocs.ok) {
                        const docData = await resDocs.json();
                        setDocs(Array.isArray(docData) ? docData : []);
                    }
                } catch (e) {
                    console.log("No documents found");
                }
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        }
        
        if (projectId) {
            init();
        }
    }, [projectId]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || !e.target.files.length || !projectId) return;
        const file = e.target.files[0];
        setUploading(true);

        try {
            const session = await getSession();
            const token = (session as any)?.accessToken;
            const formData = new FormData();
            formData.append("file", file);
            formData.append("project_id", projectId);

            // Include graph_id if available
            const universeId = localStorage.getItem("faim_universe_graph_id") || localStorage.getItem("faim.universe_graph_id");
            if (universeId) {
                formData.append("graph_id", universeId);
            }

            // Optional auth header (works in dev mode without token)
            const headers: Record<string, string> = {};
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const res = await fetch("/api/v1/storage/upload", {
                method: "POST",
                headers,
                body: formData
            });

            const data = await res.json();

            if (data.success && data.document) {
                setDocs([data.document, ...docs]);
                alert(`✅ ${data.message}`);
            } else if (res.ok && data.id) {
                // Legacy response format
                setDocs([data, ...docs]);
            } else {
                alert(`Upload failed: ${data.message || data.detail || "Unknown error"}`);
            }
        } catch (err: any) {
            alert(`Error uploading: ${err.message || err}`);
        } finally {
            setUploading(false);
            // Reset file input
            e.target.value = "";
        }
    };

    const handleExport = async () => {
        const session = await getSession();
        const token = (session as any)?.accessToken;

        const res = await fetch("/api/v1/lifecycle/export", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` }
        });

        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "faim_export.zip";
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            alert("Export failed");
        }
    };

    const handleDeleteAccount = async () => {
        if (!confirm("CRITICAL WARNING: This will permanently delete your account. This cannot be undone.")) return;
        const session = await getSession();
        const token = (session as any)?.accessToken;

        setIsDeleting(true);
        await fetch("/api/v1/lifecycle/account", {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` }
        });
        window.location.href = "/";
    };

    return (
        <div className="space-y-4">
            <header className="flex items-start justify-between gap-3">
                <div>
                    <h1 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                        <HardDrive className="text-purple-400" size={16} /> Storage & Lifecycle
                    </h1>
                    <p className="mt-1 text-xs text-slate-400">Manage uploaded documents and data compliance.</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={handleExport} className="px-3 py-1.5 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 rounded-lg flex items-center gap-1.5 text-[10px] transition-colors text-slate-300">
                        <Download size={12} /> GDPR Export
                    </button>
                    <button
                        onClick={() => {
                            if (window.confirm("Clear all uploaded files from storage? This will not delete your account.")) {
                                // TODO: Implement clear storage API call
                                alert("Storage cleared (API not yet implemented)");
                            }
                        }}
                        className="px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded-lg flex items-center gap-1.5 text-[10px] transition-colors"
                    >
                        <Trash2 size={12} /> Clear Storage
                    </button>
                </div>
            </header>

            {/* UPLOAD AREA */}
            <section className="rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/20 p-6 text-center hover:bg-slate-900/40 transition-colors relative group">
                <input
                    type="file"
                    onChange={handleUpload}
                    disabled={!projectId || uploading}
                    className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                />
                <div className="pointer-events-none">
                    <div className="w-10 h-10 bg-purple-500/20 text-purple-400 rounded-xl flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
                        <UploadCloud size={20} />
                    </div>
                    <div className="font-semibold text-xs text-slate-200 mb-1">
                        {uploading ? "Uploading..." : "Click or drag file to upload"}
                    </div>
                    <div className="text-[10px] text-slate-500">PDF, TXT, MD supported (Max 50MB)</div>
                </div>
            </section>

            {/* FILES LIST */}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
                <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
                    <h2 className="text-xs font-semibold text-slate-100">Documents</h2>
                    <div className="text-[10px] text-slate-500">{docs.length} files</div>
                </div>

                {docs.length === 0 && !loading && (
                    <div className="p-6 text-center text-slate-500 italic text-xs">No files uploaded yet.</div>
                )}

                {loading && <div className="p-6 text-center text-slate-500 animate-pulse text-xs">Loading storage...</div>}

                <div className="divide-y divide-slate-800">
                    {docs.map(doc => (
                        <div key={doc.id} className="p-3 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400">
                                    <FileText size={16} />
                                </div>
                                <div>
                                    <div className="font-medium text-slate-200 text-xs">{doc.filename}</div>
                                    <div className="text-[10px] text-slate-500 flex items-center gap-1.5 mt-0.5">
                                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                                        <span>•</span>
                                        <span>ID: {doc.id.slice(0, 8)}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-3">
                                <div className={`px-2 py-0.5 rounded-full text-[10px] font-medium flex items-center gap-1 border
                                    ${doc.status === 'completed' ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20' :
                                        doc.status === 'processing' ? 'bg-amber-500/10 text-amber-300 border-amber-500/20 animate-pulse' :
                                            doc.status === 'failed' ? 'bg-red-500/10 text-red-300 border-red-500/20' :
                                                'bg-slate-500/10 text-slate-300 border-slate-500/20'}`}>
                                    {doc.status === 'completed' && <CheckCircle size={10} />}
                                    {doc.status === 'processing' && <Clock size={10} />}
                                    {doc.status === 'failed' && <AlertCircle size={10} />}
                                    {doc.status === 'pending' && <Clock size={10} />}
                                    <span className="capitalize">{doc.status}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Supported Formats Info */}
            <section className="mt-6 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50">
                <details className="group">
                    <summary className="cursor-pointer text-xs font-medium text-slate-300 flex items-center gap-2 select-none">
                        <span className="text-purple-400">📁</span>
                        Supported File Formats
                        <span className="text-slate-500 text-[10px]">(click to expand)</span>
                    </summary>
                    <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-[10px]">
                        <div>
                            <div className="text-cyan-400 font-semibold mb-1">Documents</div>
                            <div className="text-slate-400 space-y-0.5">
                                <div>.pdf (text + tables + OCR)</div>
                                <div>.docx / .doc (Word)</div>
                                <div>.pptx / .ppt (PowerPoint)</div>
                                <div>.xlsx / .xls (Excel)</div>
                            </div>
                        </div>
                        <div>
                            <div className="text-cyan-400 font-semibold mb-1">Text</div>
                            <div className="text-slate-400 space-y-0.5">
                                <div>.txt (Plain text)</div>
                                <div>.md (Markdown)</div>
                                <div>.json (JSON data)</div>
                                <div>.csv (Spreadsheet)</div>
                            </div>
                        </div>
                        <div>
                            <div className="text-cyan-400 font-semibold mb-1">Code</div>
                            <div className="text-slate-400 space-y-0.5">
                                <div>.py .js .ts .tsx</div>
                                <div>.go .rs .java .c .cpp</div>
                                <div>.html .css .sql</div>
                                <div>.yaml .toml .xml</div>
                            </div>
                        </div>
                        <div>
                            <div className="text-cyan-400 font-semibold mb-1">Features</div>
                            <div className="text-slate-400 space-y-0.5">
                                <div>✓ OCR for scanned PDFs</div>
                                <div>✓ Table extraction</div>
                                <div>✓ FAIM memory ingestion</div>
                                <div>✓ Fractal inheritance</div>
                            </div>
                        </div>
                    </div>
                </details>
            </section>
        </div>
    );
}
