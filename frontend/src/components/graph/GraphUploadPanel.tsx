"use client";

import * as React from "react";
import { useState } from "react";
import { API_BASE_URL, buildFaimHeaders } from "@/lib/api-client";

const API_BASE = API_BASE_URL;

const MAX_FRAGMENT_CHARS = 4000;
const TEXT_FILE_EXTS = [".txt", ".md", ".json"];
const PDF_MIME = "application/pdf";
const DOCX_MIME =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function isTextFile(file: File): boolean {
  const name = file.name.toLowerCase();
  if (TEXT_FILE_EXTS.some((ext) => name.endsWith(ext))) return true;
  if (file.type.startsWith("text/")) return true;
  if (file.type === "application/json") return true;
  return false;
}

function isPdfFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith(".pdf") || file.type === PDF_MIME;
}

function isDocxFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return name.endsWith(".docx") || file.type === DOCX_MIME;
}

function normalizeText(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function chunkText(input: string, size: number): string[] {
  const out: string[] = [];
  let i = 0;
  while (i < input.length) {
    out.push(input.slice(i, i + size));
    i += size;
  }
  return out;
}

async function extractPdfText(file: File): Promise<string> {
  const pdfjs: any = await import("pdfjs-dist/legacy/build/pdf.mjs");
  const lib = pdfjs?.default ?? pdfjs;
  if (lib?.GlobalWorkerOptions && !lib.GlobalWorkerOptions.workerSrc) {
    lib.GlobalWorkerOptions.workerSrc = new URL(
      "/pdf.worker.min.mjs",
      window.location.href,
    ).toString();
  }
  const data = await file.arrayBuffer();
  const doc = await lib.getDocument({ data, disableWorker: true }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= doc.numPages; i += 1) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    const text = (content.items || [])
      .map((item: any) => item?.str ?? "")
      .filter(Boolean)
      .join(" ");
    if (text) pages.push(text);
  }
  return pages.join("\n");
}

async function extractDocxText(file: File): Promise<string> {
  const mammoth: any = await import("mammoth");
  const lib = mammoth?.default ?? mammoth;
  const data = await file.arrayBuffer();
  const result = await lib.extractRawText({ arrayBuffer: data });
  return String(result?.value ?? "");
}

type IngestFileResult = {
  filename: string;
  size_bytes: number;
  content_type?: string | null;
  chunks: number;
  skipped: boolean;
  note?: string | null;
};

type IngestResponse = {
  status: string;
  graph_id: string;
  files: IngestFileResult[];
  nodes_created: number;
  source: string;
  note?: string | null;
};

interface GraphUploadPanelProps {
  graphId: string;
  onIngestComplete?: (result: IngestResponse) => void;
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

/**
 * Sticky glow updater:
 * - updates --mx/--my on pointer move capture
 * - keeps last position (no reset on leave)
 * - controlled intensity (avoid "too much glow")
 */
function onStickyGlowMove(intensity = 0.22) {
  return (e: React.PointerEvent<HTMLElement>) => {
    const el = e.currentTarget as HTMLElement;
    const r = el.getBoundingClientRect();
    const x = clamp((e.clientX - r.left) / Math.max(1, r.width), 0, 1) * 100;
    const y = clamp((e.clientY - r.top) / Math.max(1, r.height), 0, 1) * 100;
    el.style.setProperty("--mx", `${x.toFixed(2)}%`);
    el.style.setProperty("--my", `${y.toFixed(2)}%`);
    el.style.setProperty("--gvis", String(intensity));
  };
}

const GraphUploadPanel: React.FC<GraphUploadPanelProps> = ({
  graphId,
  onIngestComplete,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<
    "idle" | "uploading" | "success" | "error"
  >("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<IngestResponse | null>(null);

  const handleFileChange: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    setSelectedFiles(e.target.files);
    setMessage(null);
    setStatus("idle");
  };

  const handleDrop: React.DragEventHandler<HTMLDivElement> = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(e.dataTransfer.files);
      setMessage(null);
      setStatus("idle");
    }
  };

  const handleDragOver: React.DragEventHandler<HTMLDivElement> = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave: React.DragEventHandler<HTMLDivElement> = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      setMessage("Select at least one file to upload.");
      setStatus("error");
      return;
    }

    try {
      setStatus("uploading");
      setMessage(null);

      const formData = new FormData();
      for (let i = 0; i < selectedFiles.length; i += 1) {
        formData.append("files", selectedFiles.item(i)!);
      }

      const ingestUrl = `${API_BASE}/graphs/${encodeURIComponent(graphId)}/ingest`;
      const res = await fetch(ingestUrl, {
        method: "POST",
        headers: buildFaimHeaders({ Accept: "application/json" }),
        body: formData,
      });

      if (!res.ok) {
        if ([404, 405, 415].includes(res.status)) {
          const fallbackResult: IngestResponse = {
            status: "ok",
            graph_id: graphId,
            files: [],
            nodes_created: 0,
            source: "text-fallback",
            note: "Ingest endpoint unavailable. Using client-side text extraction.",
          };

          for (let i = 0; i < selectedFiles.length; i += 1) {
            const file = selectedFiles.item(i)!;
            const isText = isTextFile(file);
            const isPdf = isPdfFile(file);
            const isDocx = isDocxFile(file);

            if (!isText && !isPdf && !isDocx) {
              fallbackResult.files.push({
                filename: file.name,
                size_bytes: file.size,
                content_type: file.type || null,
                chunks: 0,
                skipped: true,
                note: "Unsupported file type for client-side ingest.",
              });
              continue;
            }

            let raw = "";
            try {
              if (isText) raw = await file.text();
              else if (isPdf) raw = await extractPdfText(file);
              else if (isDocx) raw = await extractDocxText(file);
            } catch {
              fallbackResult.files.push({
                filename: file.name,
                size_bytes: file.size,
                content_type: file.type || null,
                chunks: 0,
                skipped: true,
                note: "Failed to extract file content.",
              });
              continue;
            }

            const cleaned = normalizeText(raw);
            if (!cleaned) {
              fallbackResult.files.push({
                filename: file.name,
                size_bytes: file.size,
                content_type: file.type || null,
                chunks: 0,
                skipped: true,
                note: "No extractable text found.",
              });
              continue;
            }

            const chunks = chunkText(cleaned, MAX_FRAGMENT_CHARS).filter((c) =>
              c.trim(),
            );
            let ok = true;
            let ingestedChunks = 0;

            for (const chunk of chunks) {
              const url = `${API_BASE}/graphs/${encodeURIComponent(
                graphId,
              )}/add?text=${encodeURIComponent(chunk)}`;
              const addRes = await fetch(url, {
                method: "POST",
                headers: buildFaimHeaders(),
              });

              if (!addRes.ok) {
                ok = false;
                break;
              }
              ingestedChunks += 1;
              fallbackResult.nodes_created += 1;
            }

            fallbackResult.files.push({
              filename: file.name,
              size_bytes: file.size,
              content_type: file.type || null,
              chunks: ingestedChunks,
              skipped: !ok,
              note: ok ? null : "Failed to ingest all chunks.",
            });
          }

          setLastResult(fallbackResult);
          setStatus("success");

          const totalFiles = fallbackResult.files.length;
          const skipped = fallbackResult.files.filter((f) => f.skipped).length;
          const effective = totalFiles - skipped;
          let msg = `Uploaded ${effective} file(s) via text fallback. Nodes created: ${fallbackResult.nodes_created}.`;
          if (skipped > 0) msg += ` Skipped ${skipped} file(s).`;
          if (fallbackResult.note) msg += ` Note: ${fallbackResult.note}`;
          setMessage(msg);

          if (onIngestComplete) {
            onIngestComplete(fallbackResult);
          }
          return;
        }

        const text = await res.text();
        setStatus("error");
        setMessage(
          `Upload failed (${res.status}). ${
            text || "See backend logs for details."
          }`,
        );
        return;
      }

      const json = (await res.json()) as IngestResponse;
      setLastResult(json);
      setStatus("success");

      const totalFiles = json.files.length;
      const skipped = json.files.filter((f) => f.skipped).length;
      const effective = totalFiles - skipped;

      let msg = `Uploaded ${effective} file(s). Nodes created: ${json.nodes_created}.`;
      if (skipped > 0) {
        msg += ` Skipped ${skipped} file(s) (type or size limits).`;
      }
      if (json.note) {
        msg += ` Note: ${json.note}`;
      }
      setMessage(msg);

      if (onIngestComplete) {
        onIngestComplete(json);
      }
    } catch (err) {
      console.error(err);
      setStatus("error");
      setMessage("Unexpected error during upload. Check console/backend logs.");
    }
  };

  const statusLabel =
    status === "uploading"
      ? "Uploading…"
      : status === "success"
        ? "Upload complete"
        : status === "error"
          ? "Upload error"
          : "Idle";

  const borderClass =
    status === "error"
      ? "border-red-600"
      : status === "success"
        ? "border-emerald-600"
        : isDragging
          ? "border-cyan-400"
          : "border-slate-700";

  return (
    <section
      onPointerMoveCapture={onStickyGlowMove(0.22)}
      onPointerLeave={() => {}}
      style={
        {
          "--mx": "50%",
          "--my": "35%",
          "--gvis": "0",
        } as React.CSSProperties
      }
      className={[
        // base
        "group relative mb-4 overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4",
        // neon frame
        "ring-1 ring-inset ring-cyan-500/10",
        "transition duration-200 hover:border-cyan-500/35",
        // depth
        "shadow-[0_0_0_1px_rgba(15,23,42,0.55),0_18px_70px_-40px_rgba(0,0,0,0.85)]",

        // pseudo glow layers must have content
        "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
        "after:content-[''] after:pointer-events-none after:absolute after:inset-0",

        // sticky glow layers (controlled)
        "before:[background:radial-gradient(720px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.11),transparent_66%)]",
        "before:opacity-[var(--gvis)]",
        "after:[background:radial-gradient(520px_circle_at_var(--mx)_var(--my),rgba(168,85,247,0.09),transparent_70%)]",
        "after:opacity-[var(--gvis)]",
      ].join(" ")}
    >
      {/* subtle neon edge line */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-cyan-400/10" />

      <div className="relative z-[1]">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Upload to FAIM
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Drop documents here and FAIM will turn them into nodes in{" "}
              <span className="font-mono text-cyan-300">{graphId}</span>.
            </p>
          </div>
          <span
            className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[0.65rem] text-slate-400"
            aria-label="Upload status"
          >
            {statusLabel}
          </span>
        </div>

        {/* Dropzone with its own glow */}
        <div
          onPointerMoveCapture={onStickyGlowMove(0.18)}
          onPointerLeave={() => {}}
          style={
            {
              "--mx": "50%",
              "--my": "45%",
              "--gvis": "0",
            } as React.CSSProperties
          }
          className={[
            "group relative mb-3 flex cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl border-2 border-dashed bg-slate-950/60 px-3 py-6 text-center transition-colors",
            borderClass,

            // pseudo glow layers for dropzone
            "before:content-[''] before:pointer-events-none before:absolute before:inset-0",
            "before:[background:radial-gradient(520px_circle_at_var(--mx)_var(--my),rgba(34,211,238,0.10),transparent_66%)]",
            "before:opacity-[var(--gvis)]",
          ].join(" ")}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="relative z-[1]">
            <p className="text-xs text-slate-400">
              Drag &amp; drop files here, or
            </p>
            <label className="mt-2 inline-flex cursor-pointer items-center rounded-full bg-slate-800 px-3 py-1 text-[0.7rem] font-medium text-slate-100 shadow-sm shadow-slate-900 hover:bg-slate-700">
              Browse files
              <input
                type="file"
                multiple
                className="hidden"
                onChange={handleFileChange}
              />
            </label>
            <p className="mt-2 text-[0.65rem] text-slate-500">
              Allowed: .txt, .md, .json, .pdf, .docx (client-side extraction)
            </p>
          </div>
        </div>

        <div className="mb-3 flex items-center justify-between">
          <div className="text-[0.7rem] text-slate-400">
            {selectedFiles && selectedFiles.length > 0 ? (
              <span>
                Selected{" "}
                <span className="font-semibold text-slate-100">
                  {selectedFiles.length}
                </span>{" "}
                file(s)
              </span>
            ) : (
              <span>No files selected yet.</span>
            )}
          </div>

          <button
            type="button"
            onClick={handleUpload}
            disabled={
              status === "uploading" ||
              !selectedFiles ||
              selectedFiles.length === 0
            }
            className="rounded-full bg-cyan-500 px-4 py-1.5 text-[0.7rem] font-semibold text-slate-950 shadow-md shadow-cyan-500/30 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400 disabled:shadow-none"
          >
            {status === "uploading" ? "Uploading…" : "Upload to FAIM"}
          </button>
        </div>

        {message && (
          <p
            className={`mb-2 text-[0.7rem] ${
              status === "error" ? "text-red-400" : "text-slate-300"
            }`}
          >
            {message}
          </p>
        )}

        {lastResult && lastResult.files.length > 0 && (
          <div className="mt-2 max-h-40 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/60">
            <table className="min-w-full border-collapse text-[0.7rem]">
              <thead>
                <tr className="bg-slate-900/80 text-slate-400">
                  <th className="px-3 py-2 text-left font-medium">File</th>
                  <th className="px-3 py-2 text-left font-medium">Size</th>
                  <th className="px-3 py-2 text-left font-medium">Chunks</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {lastResult.files.map((f) => (
                  <tr
                    key={f.filename}
                    className="border-t border-slate-800 text-slate-300"
                  >
                    <td className="px-3 py-1.5">
                      <span className="font-mono text-[0.65rem] text-slate-200">
                        {f.filename}
                      </span>
                    </td>
                    <td className="px-3 py-1.5">
                      {(f.size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="px-3 py-1.5">{f.chunks}</td>
                    <td className="px-3 py-1.5">
                      {f.skipped ? (
                        <span className="rounded-full bg-amber-900/60 px-2 py-0.5 text-[0.6rem] text-amber-200">
                          Skipped
                        </span>
                      ) : (
                        <span className="rounded-full bg-emerald-900/60 px-2 py-0.5 text-[0.6rem] text-emerald-200">
                          Ingested
                        </span>
                      )}
                      {f.note && (
                        <span className="ml-1 text-[0.6rem] text-slate-500">
                          {f.note}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};

export default GraphUploadPanel;
