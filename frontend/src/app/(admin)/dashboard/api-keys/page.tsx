"use client";

import {
  AlertTriangle,
  BookOpen,
  Check,
  Copy,
  KeyRound,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { getSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge, Button, Input, useToast } from "@/components/ui";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { ApiKeysManual } from "@/components/manuals/ApiKeysManual";

type ApiKeyItem = {
  tenant_id: string;
  key_id: string;
  key_prefix: string;
  label?: string | null;
  scopes: string[];
  created_at?: string | null;
  created_by?: string | null;
  expires_at?: string | null;
  last_used_at?: string | null;
  is_active: boolean;
};

type ApiKeyListResponse = {
  items: ApiKeyItem[];
  total: number;
};

type ApiKeyCreateResponse = {
  key: ApiKeyItem;
  plaintext_key: string;
};

const ALL_SCOPES = [
  "memory.read",
  "memory.write",
  "keys.read",
  "keys.write",
  "memory.admin",
] as const;

const EXPIRY_OPTIONS = [
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "365d", label: "1 year" },
  { value: "never", label: "Never expires" },
] as const;

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = {};
  if (token) base.Authorization = `Bearer ${token}`;
  if (!extra) return base;
  return { ...base, ...(extra as Record<string, string>) };
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await authHeaders(init?.headers);
  const resp = await fetch(path, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!resp.ok) {
    let message = `Request failed (${resp.status})`;
    try {
      const payload = (await resp.json()) as {
        detail?: string;
        error?: string;
      };
      message = payload.detail || payload.error || message;
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }
  return (await resp.json()) as T;
}

function computeExpiryIso(selection: string): string | undefined {
  if (selection === "never") return undefined;
  const days = Number.parseInt(selection.replace("d", ""), 10);
  if (!Number.isFinite(days) || days <= 0) return undefined;
  return new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString();
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "—";
  return dt.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ApiKeysPage() {
  const { toast } = useToast();

  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);

  // Create & One-Time Reveal Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [label, setLabel] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    "memory.read",
    "memory.write",
    "keys.read",
    "keys.write",
  ]);
  const [expiryPreset, setExpiryPreset] = useState("90d");
  const [creating, setCreating] = useState(false);
  const [revealedKey, setRevealedKey] = useState<{
    plaintext: string;
    label: string;
    prefix: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // Permanent Delete Confirmation
  const [deleteTarget, setDeleteTarget] = useState<ApiKeyItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadKeys = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiRequest<ApiKeyListResponse>(
        "/api/v1/api-keys?include_revoked=false",
      );
      setKeys((data.items || []).filter((k) => k.is_active));
    } catch (err) {
      toast.error(
        "Failed to load API keys",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  const stats = useMemo(() => {
    const now = Date.now();
    const fourteenDays = 14 * 24 * 60 * 60 * 1000;
    const expiringSoon = keys.filter((k) => {
      if (!k.expires_at) return false;
      const ms = new Date(k.expires_at).getTime() - now;
      return ms > 0 && ms <= fourteenDays;
    }).length;
    const neverExpires = keys.filter((k) => !k.expires_at).length;
    return { active: keys.length, expiringSoon, neverExpires };
  }, [keys]);

  function toggleScope(scope: string) {
    setSelectedScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  }

  function openCreateModal() {
    setLabel("");
    setSelectedScopes([
      "memory.read",
      "memory.write",
      "keys.read",
      "keys.write",
    ]);
    setExpiryPreset("90d");
    setRevealedKey(null);
    setCopied(false);
    setCreateOpen(true);
  }

  function closeCreateModal() {
    setCreateOpen(false);
    setRevealedKey(null);
    setCopied(false);
  }

  async function handleCreate() {
    if (selectedScopes.length === 0) {
      toast.error("Select at least one permission scope");
      return;
    }
    setCreating(true);
    try {
      const res = await apiRequest<ApiKeyCreateResponse>("/api/v1/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: label.trim() || null,
          scopes: selectedScopes,
          expires_at: computeExpiryIso(expiryPreset),
        }),
      });
      setRevealedKey({
        plaintext: res.plaintext_key,
        label: res.key.label || label.trim() || "API Key",
        prefix: res.key.key_prefix,
      });
      setKeys((prev) => [res.key, ...prev]);
      toast.success("Secret key created");
    } catch (err) {
      toast.error(
        "Failed to create API key",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setCreating(false);
    }
  }

  async function handleCopy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success("Copied secret key to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  }

  async function handleConfirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await apiRequest(
        `/api/v1/api-keys/${encodeURIComponent(deleteTarget.key_id)}`,
        {
          method: "DELETE",
        },
      );
      setKeys((prev) => prev.filter((k) => k.key_id !== deleteTarget.key_id));
      toast.success("API key permanently deleted");
      setDeleteTarget(null);
    } catch (err) {
      toast.error(
        "Failed to delete API key",
        err instanceof Error ? err.message : undefined,
      );
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />
      <GlassHeader
        title="API Keys"
        subtitle="Create and manage secret keys for SDK, CLI, and external agent access"
        icon={KeyRound}
        titleTestId="api-keys-page-title"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void loadKeys()}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setManualOpen(true)}
              className="gap-1.5"
            >
              <BookOpen className="h-3.5 w-3.5" />
              User Manual
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={openCreateModal}
              className="gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" />
              Create new secret key
            </Button>
          </div>
        }
      />

      <div className="w-full space-y-4">
        {/* Compact Summary */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent" />
            <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/80 via-cyan-400/30 to-transparent" />
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Active Keys
                </p>
                <p className="mt-1 text-2xl font-semibold text-cyan-300">
                  {stats.active}
                </p>
              </div>
              <KeyRound className="h-5 w-5 text-cyan-400/70" />
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-amber-500/80 via-amber-400/40 to-transparent" />
            <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-amber-400/80 via-amber-400/30 to-transparent" />
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Expiring (&lt; 14 days)
                </p>
                <p className="mt-1 text-2xl font-semibold text-amber-300">
                  {stats.expiringSoon}
                </p>
              </div>
              <AlertTriangle className="h-5 w-5 text-amber-400/70" />
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
            <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-emerald-500/80 via-emerald-400/40 to-transparent" />
            <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-emerald-400/80 via-emerald-400/30 to-transparent" />
            <div className="flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
                  Non-Expiring
                </p>
                <p className="mt-1 text-2xl font-semibold text-emerald-300">
                  {stats.neverExpires}
                </p>
              </div>
              <ShieldCheck className="h-5 w-5 text-emerald-400/70" />
            </div>
          </div>
        </div>

        {/* Production Key Table */}
        <div className="relative overflow-hidden rounded-[18px] border border-white/8 bg-[linear-gradient(180deg,rgba(5,7,13,0.98),rgba(9,13,21,0.94))] shadow-[0_14px_40px_rgba(0,0,0,0.24)]">
          <div className="pointer-events-none absolute top-0 left-6 right-6 h-[2px] rounded-full bg-gradient-to-r from-cyan-500/80 via-cyan-400/40 to-transparent" />
          <div className="pointer-events-none absolute top-0 left-0 bottom-0 w-[2px] bg-gradient-to-b from-cyan-400/70 via-cyan-400/25 to-transparent" />
          <div className="p-0">
            <div className="flex items-center justify-between border-b border-white/8 px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  Secret Keys
                </h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  Secret keys are shown only once at creation. Deleted keys are
                  permanently removed with no history kept.
                </p>
              </div>
            </div>

            {loading && keys.length === 0 ? (
              <div className="px-6 py-12 text-center text-sm text-slate-400">
                Loading API keys...
              </div>
            ) : keys.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
                <div className="rounded-full border border-cyan-500/20 bg-cyan-500/10 p-3">
                  <KeyRound className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">
                    No API keys yet
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    Create a secret key to connect external agents, scripts, or
                    the FAIM Python SDK.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={openCreateModal}
                  className="mt-1 gap-1.5"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Create new secret key
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-[11px] uppercase tracking-wider text-slate-400">
                      <th className="px-5 py-3 font-medium">Name</th>
                      <th className="px-5 py-3 font-medium">Secret Key</th>
                      <th className="px-5 py-3 font-medium">Permissions</th>
                      <th className="px-5 py-3 font-medium">Created</th>
                      <th className="px-5 py-3 font-medium">Last Used</th>
                      <th className="px-5 py-3 font-medium">Expires</th>
                      <th className="px-5 py-3 text-right font-medium">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {keys.map((item) => (
                      <tr
                        key={item.key_id}
                        className="transition-colors hover:bg-white/[0.02]"
                      >
                        <td className="px-5 py-3.5 font-medium text-slate-100">
                          {item.label || "Untitled key"}
                        </td>
                        <td className="px-5 py-3.5 font-mono text-slate-300">
                          {item.key_prefix}••••••••••••
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex flex-wrap gap-1">
                            {(item.scopes || []).map((scope) => (
                              <Badge key={scope} variant="default">
                                {scope}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">
                          {formatDate(item.created_at)}
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">
                          {formatDate(item.last_used_at)}
                        </td>
                        <td className="px-5 py-3.5 text-slate-400">
                          {item.expires_at
                            ? formatDate(item.expires_at)
                            : "Never"}
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(item)}
                            title="Delete key permanently"
                            className="inline-flex items-center gap-1 rounded-lg border border-rose-500/20 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-300 transition hover:bg-rose-500/20"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create & One-Time Secret Reveal Modal */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-white/15 bg-[#0d1424] p-6 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-100">
                {revealedKey ? "Save your secret key" : "Create new secret key"}
              </h3>
              <button
                type="button"
                onClick={closeCreateModal}
                className="rounded-lg p-1 text-slate-400 hover:bg-white/10 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {revealedKey ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
                  Please save this secret key somewhere safe. For security
                  reasons,{" "}
                  <strong>you will not be able to view it again</strong> after
                  closing this window.
                </div>

                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                    Key Name
                  </p>
                  <p className="text-sm font-medium text-slate-200">
                    {revealedKey.label}
                  </p>
                </div>

                <div>
                  <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                    Secret Key
                  </p>
                  <div className="flex items-center gap-2 rounded-xl border border-cyan-500/30 bg-[#070b14] p-2.5">
                    <code className="flex-1 break-all font-mono text-xs text-cyan-300">
                      {revealedKey.plaintext}
                    </code>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => void handleCopy(revealedKey.plaintext)}
                      className="shrink-0 gap-1"
                    >
                      {copied ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                      {copied ? "Copied" : "Copy"}
                    </Button>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={closeCreateModal}
                  >
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">
                    Name
                  </label>
                  <Input
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    placeholder="e.g. cursor-local, production-agent"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">
                    Permissions
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {ALL_SCOPES.map((scope) => {
                      const active = selectedScopes.includes(scope);
                      return (
                        <button
                          key={scope}
                          type="button"
                          onClick={() => toggleScope(scope)}
                          className={`rounded-lg border px-2.5 py-1 text-xs font-mono transition ${
                            active
                              ? "border-cyan-400/50 bg-cyan-500/15 text-cyan-200"
                              : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10"
                          }`}
                        >
                          {scope}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">
                    Expiration
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {EXPIRY_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setExpiryPreset(opt.value)}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                          expiryPreset === opt.value
                            ? "border-cyan-400/50 bg-cyan-500/15 text-cyan-200"
                            : "border-white/10 bg-white/5 text-slate-400 hover:bg-white/10"
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={closeCreateModal}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => void handleCreate()}
                    disabled={creating}
                  >
                    {creating ? "Creating..." : "Create secret key"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Permanent Delete Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-white/15 bg-[#0d1424] p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-semibold text-slate-100">
              Delete API key?
            </h3>
            <p className="text-xs leading-relaxed text-slate-400">
              <strong className="text-slate-200">
                {deleteTarget.label || deleteTarget.key_prefix}
              </strong>{" "}
              ({deleteTarget.key_prefix}••••) will be permanently deleted with
              no history kept. Any application using it will immediately lose
              access.
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <button
                type="button"
                onClick={() => void handleConfirmDelete()}
                disabled={deleting}
                className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete forever"}
              </button>
            </div>
          </div>
        </div>
      )}

      <ApiKeysManual open={manualOpen} onClose={() => setManualOpen(false)} />
    </div>
  );
}
