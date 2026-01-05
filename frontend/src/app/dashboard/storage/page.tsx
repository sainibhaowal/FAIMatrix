"use client";

import React, { useEffect, useState } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  HardDrive,
  Trash2,
  Download,
} from "lucide-react";
import { getSession } from "next-auth/react";
import { useUserIds } from "@/contexts/UserContext";

// UI Components
import { useToast } from "@/components/ui/Toast";
import {
  Card,
  Button,
  Spinner,
  Skeleton,
  EmptyState,
  Modal,
  Badge,
} from "@/components/ui";

type Doc = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  file_size_bytes: number;
};

export default function StoragePage() {
  const { toast } = useToast();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Confirmation Dialog State
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<() => Promise<void>>(async () => {});
  const [confirmTitle, setConfirmTitle] = useState("");
  const [confirmMessage, setConfirmMessage] = useState("");
  const [confirmVariant, setConfirmVariant] = useState<"danger" | "warning">("danger");

  const { projectId: contextProjectId } = useUserIds();
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

        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        try {
          const resDocs = await fetch(
            `/api/v1/storage/files?project_id=${projectId}`,
            { headers },
          );
          if (resDocs.ok) {
            const docData = await resDocs.json();
            setDocs(Array.isArray(docData) ? docData : []);
          }
        } catch (e) {
          console.log("No documents found");
        }
      } catch (e) {
        console.error(e);
        toast.error("Failed to load documents");
      } finally {
        setLoading(false);
      }
    }

    if (projectId) {
      init();
    }
  }, [projectId, toast]);

  const confirm = (title: string, message: string, action: () => Promise<void>, variant: "danger" | "warning" = "danger") => {
    setConfirmTitle(title);
    setConfirmMessage(message);
    setConfirmAction(() => action);
    setConfirmVariant(variant);
    setConfirmOpen(true);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files.length || !projectId) return;
    const file = e.target.files[0];
    setUploading(true);

    // const loadingToast = toast.loading("Uploading document...");

    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;
      const formData = new FormData();
      formData.append("file", file);
      formData.append("project_id", projectId);

      const universeId =
        localStorage.getItem("faim_universe_graph_id") ||
        localStorage.getItem("faim.universe_graph_id");
      if (universeId) {
        formData.append("graph_id", universeId);
      }

      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch("/api/v1/storage/upload", {
        method: "POST",
        headers,
        body: formData,
      });

      const data = await res.json();

      if (data.success && data.document) {
        setDocs([data.document, ...docs]);
        toast.success("Document uploaded successfully");
      } else if (res.ok && data.id) {
        setDocs([data, ...docs]);
        toast.success("Document uploaded");
      } else {
        toast.error(data.message || data.detail || "Upload failed");
      }
    } catch (err: any) {
      toast.error(err.message || "Error uploading file");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleExport = async () => {
    const session = await getSession();
    const token = (session as any)?.accessToken;
    
    toast.info("Preparing export...");

    try {
      const res = await fetch("/api/v1/lifecycle/export", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
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
        toast.success("Export download started");
      } else {
        toast.error("Export failed");
      }
    } catch (e) {
      toast.error("Network error during export");
    }
  };

  const handleDeleteAccount = () => {
    confirm(
      "Delete Account?",
      "CRITICAL WARNING: This will permanently delete your account. This cannot be undone.",
      async () => {
        try {
          const session = await getSession();
          const token = (session as any)?.accessToken;

          setIsDeleting(true);
          await fetch("/api/v1/lifecycle/account", {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
          });
          window.location.href = "/";
        } catch (e) {
          toast.error("Failed to delete account");
          setIsDeleting(false);
        }
      },
      "danger"
    );
  };

  const handleClearStorage = () => {
    confirm(
      "Clear Storage?",
      "Clear all uploaded files from storage? This action cannot be undone.",
      async () => {
        // TODO: Implement clear storage API call
        toast.info("Storage cleared (Demo)");
      },
      "warning"
    );
  };

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <HardDrive className="text-[var(--faim-secondary)]" size={20} /> 
            Storage & Lifecycle
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Manage uploaded documents and data compliance.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExport}
            className="text-xs"
          >
            <Download size={14} className="mr-1.5" /> GDPR Export
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearStorage}
            className="text-xs text-[var(--faim-warning)] hover:text-[var(--faim-warning)] hover:bg-[var(--faim-warning-muted)]"
          >
            <Trash2 size={14} className="mr-1.5" /> Clear
          </Button>
        </div>
      </header>

      {/* UPLOAD AREA */}
      <Card
        className="relative border-dashed border-2 border-[var(--border-default)] bg-[var(--surface-1)] hover:bg-[var(--surface-2)] transition-colors group"
        noPadding
      >
        <div className="p-8 text-center">
          <input
            type="file"
            onChange={handleUpload}
            disabled={!projectId || uploading}
            className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
          />
          <div className="w-12 h-12 bg-[var(--faim-secondary-muted)] text-[var(--faim-secondary)] rounded-xl flex items-center justify-center mx-auto mb-3 group-hover:scale-110 transition-transform">
            {uploading ? <Spinner size="sm" /> : <UploadCloud size={24} />}
          </div>
          <div className="font-semibold text-sm text-[var(--text-primary)] mb-1">
            {uploading ? "Uploading..." : "Click or drag file to upload"}
          </div>
          <div className="text-xs text-[var(--text-muted)]">
            PDF, TXT, MD supported (Max 50MB)
          </div>
        </div>
      </Card>

      {/* FILES LIST */}
      <Card>
        <div className="px-5 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Documents</h2>
          <Badge variant="default" size="sm">{docs.length} files</Badge>
        </div>

        {loading ? (
          <div className="p-5 space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton height={40} width={40} className="rounded-lg" />
                <div className="space-y-2 flex-1">
                  <Skeleton height={14} width="40%" />
                  <Skeleton height={10} width="20%" />
                </div>
              </div>
            ))}
          </div>
        ) : docs.length === 0 ? (
          <EmptyState
            icon="documents"
            title="No files yet"
            description="Upload documents to get started building your knowledge graph."
            size="sm"
          />
        ) : (
          <div className="divide-y divide-[var(--border-subtle)]">
            {docs.map((doc) => (
              <div
                key={doc.id}
                className="p-4 flex items-center justify-between hover:bg-[var(--surface-2)] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-[var(--surface-2)] flex items-center justify-center text-[var(--text-secondary)]">
                    <FileText size={20} />
                  </div>
                  <div>
                    <div className="font-medium text-[var(--text-primary)] text-sm">
                      {doc.filename}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] flex items-center gap-1.5 mt-0.5">
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      <span>•</span>
                      <span className="font-mono">{doc.id.slice(0, 8)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <StatusBadge status={doc.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Supported Formats Info */}
      <details className="group p-4 rounded-xl bg-[var(--surface-1)] border border-[var(--border-subtle)]">
        <summary className="cursor-pointer text-xs font-medium text-[var(--text-secondary)] flex items-center gap-2 select-none group-hover:text-[var(--text-primary)]">
          <span className="text-[var(--faim-secondary)]">📁</span>
          Supported File Formats
          <span className="text-[var(--text-muted)] text-[10px]">
            (click to expand)
          </span>
        </summary>
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-4 text-[10px]">
          <div>
            <div className="text-[var(--faim-primary)] font-semibold mb-1">Documents</div>
            <div className="text-[var(--text-muted)] space-y-0.5">
              <div>.pdf (text + tables + OCR)</div>
              <div>.docx / .doc (Word)</div>
              <div>.pptx / .ppt (PowerPoint)</div>
              <div>.xlsx / .xls (Excel)</div>
            </div>
          </div>
          <div>
            <div className="text-[var(--faim-primary)] font-semibold mb-1">Text</div>
            <div className="text-[var(--text-muted)] space-y-0.5">
              <div>.txt (Plain text)</div>
              <div>.md (Markdown)</div>
              <div>.json (JSON data)</div>
              <div>.csv (Spreadsheet)</div>
            </div>
          </div>
          <div>
            <div className="text-[var(--faim-primary)] font-semibold mb-1">Code</div>
            <div className="text-[var(--text-muted)] space-y-0.5">
              <div>.py .js .ts .tsx</div>
              <div>.go .rs .java .c .cpp</div>
              <div>.html .css .sql</div>
              <div>.yaml .toml .xml</div>
            </div>
          </div>
          <div>
            <div className="text-[var(--faim-primary)] font-semibold mb-1">Features</div>
            <div className="text-[var(--text-muted)] space-y-0.5">
              <div>✓ OCR for scanned PDFs</div>
              <div>✓ Table extraction</div>
              <div>✓ FAIM memory ingestion</div>
              <div>✓ Fractal inheritance</div>
            </div>
          </div>
        </div>
      </details>
      
      {/* Confirm Dialog */}
      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title={confirmTitle}
      >
        <div className="space-y-4">
           <p className="text-sm text-[var(--text-secondary)]">
             {confirmMessage}
           </p>
           <div className="flex justify-end gap-2">
             <Button variant="ghost" onClick={() => setConfirmOpen(false)}>Cancel</Button>
             <Button 
               variant={confirmVariant === "danger" ? "danger" : "primary"}
               onClick={async () => {
                 await confirmAction();
                 setConfirmOpen(false);
               }}
             >
               Confirm
             </Button>
           </div>
        </div>
      </Modal>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variantMap: Record<string, "success" | "warning" | "error" | "default"> = {
    completed: "success",
    processing: "warning",
    pending: "warning",
    failed: "error",
  };
  
  const iconMap: Record<string, any> = {
    completed: CheckCircle,
    processing: Clock,
    pending: Clock,
    failed: AlertCircle,
  };

  const Icon = iconMap[status] || Clock;

  return (
    <Badge variant={variantMap[status] || "default"} size="sm" className="gap-1.5 capitalize">
      <Icon size={10} />
      {status}
    </Badge>
  );
}
