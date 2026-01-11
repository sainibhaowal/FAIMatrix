"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  FileText,
  HardDrive,
  Trash2,
  Download,
  Search,
  Info,
  ChevronDown,
  Eye,
} from "lucide-react";
import { getSession } from "next-auth/react";
import { useUserIds } from "@/contexts/UserContext";

// UI Components
import { useToast } from "@/components/ui/Toast";
import {
  Button,
  Modal,
  Spinner,
} from "@/components/ui";
import { FileUploader, StorageList } from "@/components";

type Doc = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  file_size_bytes: number;
};

type SortOption = "date_desc" | "date_asc" | "az" | "za" | "size_desc";

function formatBytes(bytes: number) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export default function StoragePage() {
  const { toast } = useToast();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  
  // -- Upload State --
  const [activeUploads, setActiveUploads] = useState<Record<string, number>>({});
  const [isDragOver, setIsDragOver] = useState(false);

  // -- Selection State --
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // -- Filter/Sort State --
  const [filterQuery, setFilterQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("date_desc");

  // -- Confirmation Dialog State --
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<() => Promise<void>>(async () => {});
  const [confirmTitle, setConfirmTitle] = useState("");
  const [confirmMessage, setConfirmMessage] = useState("");
  const [confirmVariant, setConfirmVariant] = useState<"danger" | "warning">("danger");

  const { graphId, isAuthenticated, isLoading: authLoading } = useUserIds();

  // -- Supported Files Panel --
  const [showSupportedFiles, setShowSupportedFiles] = useState(false);

  // Load Documents (user-scoped via auth token)
  const loadDocs = useCallback(async () => {
    if (!isAuthenticated || authLoading) return;
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resDocs = await fetch(`/api/v1/storage/files`, { headers });
      if (resDocs.ok) {
        const docData = await resDocs.json();
        setDocs(Array.isArray(docData) ? docData : []);
      }
    } catch (e) {
      console.error(e);
      toast.error("Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, authLoading, toast]);

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
       setLoading(true);
       loadDocs();
    }
  }, [isAuthenticated, authLoading, loadDocs]);

  const uploadFiles = async (files: FileList | File[]) => {
    if (!isAuthenticated) return;

    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    const validFiles = fileArray.filter(f => f.size > 0);
    
    const newUploads: Record<string, number> = {};
    validFiles.forEach(f => { newUploads[f.name] = 0; });
    setActiveUploads(prev => ({ ...prev, ...newUploads }));

    const uploadOne = (file: File): Promise<void> => {
      return new Promise<void>((resolve, reject) => {
        const formData = new FormData();
        formData.append("file", file);
        if (graphId) formData.append("graph_id", graphId);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/v1/storage/upload");

        getSession().then((session) => {
          const token = (session as any)?.accessToken;
          if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
          xhr.send(formData);
        });

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            setActiveUploads(prev => ({ ...prev, [file.name]: percent }));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            toast.success(`Uploaded ${file.name}`);
            try {
              const data = JSON.parse(xhr.responseText);
              const newDoc = data.document;
              if (newDoc) setDocs(prev => [newDoc, ...prev]);
            } catch {}
            resolve();
          } else {
            toast.error(`Failed to upload ${file.name}`);
            resolve();
          }
          setActiveUploads(prev => {
            const next = { ...prev };
            delete next[file.name];
            return next;
          });
        };

        xhr.onerror = () => {
          toast.error(`Network error uploading ${file.name}`);
          setActiveUploads(prev => {
             const next = { ...prev };
             delete next[file.name];
             return next;
          });
          resolve(); 
        };
      });
    };

    await Promise.all(validFiles.map(uploadOne));
  };

  const toggleSelection = (id: string, multi: boolean) => {
    const newSet = new Set(multi ? selectedIds : []);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedIds(newSet);
  };

  const selectAll = () => {
    if (selectedIds.size === filteredDocs.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(filteredDocs.map(d => d.id)));
  };

  const deleteSelected = () => {
    confirm(
      `Delete ${selectedIds.size} file(s)?`,
      "This cannot be undone.",
      async () => {
        const idsToDelete = Array.from(selectedIds);
        const session = await getSession();
        const token = (session as any)?.accessToken;
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const results = await Promise.all(idsToDelete.map(async (id) => {
           try {
              const res = await fetch(`/api/v1/storage/files/${id}`, { method: "DELETE", headers });
              return res.ok;
           } catch { return false; }
        }));

        const successCount = results.filter(Boolean).length;
        if (successCount > 0) {
           setDocs(prev => prev.filter(d => !selectedIds.has(d.id)));
           setSelectedIds(new Set());
           toast.success(`Deleted ${successCount} files`);
        } else {
           toast.error("Failed to delete selected files");
        }
      },
      "danger"
    );
  };

  const filteredDocs = useMemo(() => {
    let res = docs;
    if (filterQuery) {
      const q = filterQuery.toLowerCase();
      res = res.filter(d => d.filename.toLowerCase().includes(q) || d.id.toLowerCase().includes(q));
    }
    return [...res].sort((a, b) => {
      switch (sortBy) {
        case "date_asc": return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case "date_desc": return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case "az": return a.filename.localeCompare(b.filename);
        case "za": return b.filename.localeCompare(a.filename);
        case "size_desc": return b.file_size_bytes - a.file_size_bytes;
        default: return 0;
      }
    });
  }, [docs, filterQuery, sortBy]);

  const confirm = (title: string, message: string, action: () => Promise<void>, variant: "danger" | "warning" = "danger") => {
    setConfirmTitle(title);
    setConfirmMessage(message);
    setConfirmAction(() => action);
    setConfirmVariant(variant);
    setConfirmOpen(true);
  };

  const handleExport = async () => { 
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(filteredDocs, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href",     dataStr);
    downloadAnchorNode.setAttribute("download", "faim_storage_export.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };
  
  const [previewDoc, setPreviewDoc] = useState<Doc | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const handlePreview = async (doc: Doc) => {
    setPreviewDoc(doc);
    setPreviewLoading(true);
    setPreviewContent(null);
    
    const ext = doc.filename.split('.').pop()?.toLowerCase();
    const isText = ['txt', 'md', 'json', 'csv', 'py', 'js', 'ts', 'tsx', 'html', 'css', 'sql', 'yaml', 'toml', 'xml', 'log'].includes(ext || '');

    if (isText && doc.file_size_bytes < 2 * 1024 * 1024) {
       try {
         const session = await getSession();
         const token = (session as any)?.accessToken;
         const headers: Record<string, string> = {};
         if (token) headers["Authorization"] = `Bearer ${token}`;

         const res = await fetch(`/api/v1/storage/files/${doc.id}/content`, { headers });
         if (res.ok) {
            const text = await res.text();
            setPreviewContent(text);
         } else {
            setPreviewContent("Error loading content.");
         }
       } catch (e) {
         console.error(e);
         setPreviewContent("Failed to load content.");
       }
    } else if (isText) {
       setPreviewContent("File too large to preview. Please download.");
    } else {
       setPreviewContent(null);
    }
    setPreviewLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <HardDrive className="text-[var(--faim-secondary)]" size={20} /> 
            Storage & Lifecycle
          </h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Manage your knowledge base documents.
          </p>
        </div>
        <div className="flex gap-2">
          {selectedIds.size > 0 && (
            <Button
               variant="danger"
               size="sm"
               onClick={deleteSelected}
               className="text-xs"
            >
               <Trash2 size={14} className="mr-1.5" /> Delete ({selectedIds.size})
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExport}
            className="text-xs"
          >
            <Download size={14} className="mr-1.5" /> Export
          </Button>
        </div>
      </header>

      {/* UPLOAD ZONE */}
      <FileUploader 
        onUpload={uploadFiles}
        activeUploads={activeUploads}
        isDragOver={isDragOver}
        setIsDragOver={setIsDragOver}
        isAuthenticated={isAuthenticated}
      />

      {/* SUPPORTED FILES INFO */}
      <div className="flex justify-center">
        <button
          onClick={() => setShowSupportedFiles(!showSupportedFiles)}
          className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-cyan-400 transition-colors py-1 px-3 rounded-full border border-transparent hover:border-cyan-500/30 hover:bg-cyan-500/5"
        >
          <Info size={12} />
          <span>Supported File Types</span>
          <ChevronDown size={12} className={`transition-transform ${showSupportedFiles ? "rotate-180" : ""}`} />
        </button>
      </div>

      {showSupportedFiles && (
        <div className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-xl p-4 space-y-4 animate-[fadeIn_0.2s_ease-out]">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Documents */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText size={12} /> Documents
              </h4>
              <ul className="text-xs text-[var(--text-secondary)] space-y-1">
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> PDF (.pdf)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Word (.docx, .doc)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> PowerPoint (.pptx, .ppt)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Excel (.xlsx, .xls)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> OpenDocument (.odt, .ods)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Rich Text (.rtf)</li>
              </ul>
            </div>

            {/* Text & Markup */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-violet-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText size={12} /> Text & Markup
              </h4>
              <ul className="text-xs text-[var(--text-secondary)] space-y-1">
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Plain Text (.txt)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Markdown (.md, .markdown)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> HTML (.html, .htm)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> XML (.xml)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> JSON (.json)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> YAML (.yaml, .yml)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> CSV (.csv)</li>
              </ul>
            </div>

            {/* Code Files */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-pink-400 uppercase tracking-wider flex items-center gap-1.5">
                <Eye size={12} /> Code Files
              </h4>
              <ul className="text-xs text-[var(--text-secondary)] space-y-1">
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Python (.py)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> JavaScript (.js, .jsx)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> TypeScript (.ts, .tsx)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Java (.java)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> C/C++ (.c, .cpp, .h)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> C# (.cs)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Go (.go)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Rust (.rs)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> SQL (.sql)</li>
              </ul>
            </div>

            {/* Other Formats */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <HardDrive size={12} /> Other Formats
              </h4>
              <ul className="text-xs text-[var(--text-secondary)] space-y-1">
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> E-books (.epub)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> LaTeX (.tex)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Log files (.log)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Config files (.ini, .cfg)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Shell scripts (.sh, .bash)</li>
                <li className="flex items-center gap-2"><span className="text-emerald-400">✓</span> Dockerfile (Dockerfile)</li>
              </ul>
            </div>
          </div>

          <div className="border-t border-[var(--border-subtle)] pt-3 flex items-center justify-between text-[10px] text-[var(--text-muted)]">
            <span>Maximum file size: <strong className="text-[var(--text-secondary)]">50MB</strong> per file</span>
            <span>Files are processed for knowledge extraction and graph indexing</span>
          </div>
        </div>
      )}

      {/* TOOLBAR */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
         <div className="relative w-full sm:w-72 group">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] group-focus-within:text-cyan-400" size={14} />
            <input
              type="text"
              placeholder="Filter documents..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full bg-[var(--surface-1)] border border-[var(--border-default)] rounded-lg pl-8 pr-3 py-2 text-sm focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-all"
            />
         </div>
         <div className="flex items-center gap-2 self-end sm:self-auto">
            <select
               value={sortBy}
               onChange={(e) => setSortBy(e.target.value as SortOption)}
               className="bg-[var(--surface-1)] border border-[var(--border-default)] rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-cyan-500/50"
            >
               <option value="date_desc">Newest first</option>
               <option value="date_asc">Oldest first</option>
               <option value="az">Name (A-Z)</option>
               <option value="za">Name (Z-A)</option>
               <option value="size_desc">Largest size</option>
            </select>
         </div>
      </div>

      {/* FILE LIST */}
      <StorageList 
        docs={filteredDocs}
        loading={loading}
        selectedIds={selectedIds}
        onToggleSelection={toggleSelection}
        onSelectAll={selectAll}
        onPreview={handlePreview}
        onDelete={(doc) => {
           confirm("Delete file?", "This cannot be undone.", async () => {
              setDocs(prev => prev.filter(p => p.id !== doc.id));
              toast.success("File deleted");
           }, "danger");
        }}
        formatBytes={formatBytes}
      />

      {/* Preview Modal */}
      <Modal
        open={!!previewDoc}
        onClose={() => setPreviewDoc(null)}
        title={previewDoc?.filename || "Preview"}
      >
         <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 bg-[var(--surface-2)] rounded-xl">
               <div className="p-3 bg-[var(--surface-3)] rounded-lg">
                  <FileText size={24} className="text-[var(--faim-primary)]" />
               </div>
               <div>
                  <div className="font-semibold text-[var(--text-primary)]">{previewDoc?.filename}</div>
                  <div className="text-xs text-[var(--text-muted)] mt-1">
                     {previewDoc && formatBytes(previewDoc.file_size_bytes)} • {previewDoc && new Date(previewDoc.created_at).toLocaleString()}
                  </div>
               </div>
            </div>

            {/* Content Preview */}
            <div className="min-h-[300px] max-h-[60vh] overflow-auto bg-[var(--surface-1)] rounded-xl border border-[var(--border-subtle)] p-4 text-xs font-mono text-[var(--text-secondary)] whitespace-pre-wrap">
               {previewLoading ? (
                  <div className="flex h-full items-center justify-center min-h-[200px]">
                     <Spinner />
                  </div>
               ) : previewContent ? (
                  previewContent
               ) : (
                  <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-[var(--text-muted)]">
                     <p>Preview not available for this file type.</p>
                     <Button variant="ghost" size="sm" className="mt-4" onClick={() => {
                        window.open(`/api/v1/storage/files/${previewDoc?.id}/content`, '_blank');
                     }}>
                        <Download size={14} className="mr-2" /> Download to view
                     </Button>
                  </div>
               )}
            </div>
            
            <div className="flex justify-end gap-2">
               <Button variant="ghost" onClick={() => setPreviewDoc(null)}>Close</Button>
               <Button variant="primary" onClick={() => {
                   if (previewDoc) window.open(`/api/v1/storage/files/${previewDoc.id}/content`, '_blank');
               }}>
                  <Download size={14} className="mr-1.5" /> Download
               </Button>
            </div>
         </div>
      </Modal>

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
