"use client";

import {
  ChevronDown,
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  RefreshCw,
  RotateCcw,
  Shield,
  ShieldCheck,
  ShieldOff,
  Trash2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { getSession, useSession } from "next-auth/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Input,
  Select,
  useToast,
} from "@/components/ui";
import { GlassHeader } from "@/components/layout/GlassHeader";

type ApiKeyItem = {
  tenant_id: string;
  key_id: string;
  key_prefix: string;
  scopes: string[];
  created_at?: string | null;
  created_by?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
  revoked_reason?: string | null;
  rotated_from_key_id?: string | null;
  last_used_at?: string | null;
  is_active: boolean;
};

type ApiKeyListResponse = {
  items: ApiKeyItem[];
  total: number;
  include_revoked: boolean;
};

type ApiKeyCreateResponse = {
  key: ApiKeyItem;
  plaintext_key: string;
};

type ApiKeyRotateResponse = {
  old_key: ApiKeyItem;
  new_key: ApiKeyItem;
  plaintext_key: string;
};

type ApiKeyRevokeResponse = {
  key: ApiKeyItem;
};

type ApiKeyAuditItem = {
  id: string;
  tenant_id: string;
  key_id: string;
  action: string;
  actor?: string | null;
  request_id?: string | null;
  meta: Record<string, unknown>;
  created_at?: string | null;
};

type ApiKeyAuditResponse = {
  items: ApiKeyAuditItem[];
  total: number;
  limit: number;
};

// --- Custom Themed Select Component (Storage Parity) ---
function ThemedSelect<T extends string>({
  value,
  onChange,
  options,
  className = "",
  placeholder = "Select...",
  label = "",
}: {
  value: T;
  onChange: (val: T) => void;
  options: { value: T; label: string }[];
  className?: string;
  placeholder?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);

  return (
    <div className={`relative ${className}`}>
      {label && (
        <p
          className="mb-1.5 text-[10px] font-medium uppercase tracking-wider"
          style={{ color: "var(--text-tertiary)" }}
        >
          {label}
        </p>
      )}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-8 w-full items-center justify-between gap-2 rounded-lg border px-2.5 text-xs outline-none transition-all hover:bg-white/5 active:scale-[0.98]"
        style={{
          background: "var(--os-surface-2)",
          borderColor: "var(--os-stroke)",
          color: "var(--text-primary)",
        }}
      >
        <span className="truncate">{current?.label || placeholder}</span>
        <ChevronDown
          size={14}
          className={`shrink-0 transition-transform duration-300 ${open ? "rotate-180" : ""}`}
          style={{ color: "var(--text-tertiary)" }}
        />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-[var(--z-modal)]"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -4 }}
              className="absolute left-0 top-full z-[var(--z-dropdown)] w-full min-w-[120px] mt-1 overflow-hidden rounded-xl border p-1 shadow-2xl backdrop-blur-xl"
              style={{
                background: "rgba(10, 15, 25, 0.95)",
                borderColor: "var(--os-stroke)",
                boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
              }}
            >
              {options.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                  className={`flex h-8 w-full items-center rounded-lg px-2.5 text-xs transition-colors ${
                    opt.value === value
                      ? "bg-indigo-500/10 font-medium text-indigo-400"
                      : "text-[var(--text-secondary)] hover:bg-white/5"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type RevealState = {
  keyId: string;
  plaintext: string;
  mode: "created" | "rotated";
};

const AVAILABLE_SCOPES = [
  "keys.read",
  "keys.write",
  "memory.read",
  "memory.write",
  "memory.admin",
];

const EXPIRY_OPTIONS = [
  { value: "never", label: "Never expires" },
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
];

function statusForKey(item: ApiKeyItem): "active" | "revoked" | "expired" {
  if (item.revoked_at) return "revoked";
  if (item.expires_at && new Date(item.expires_at).getTime() <= Date.now()) {
    return "expired";
  }
  return "active";
}

function shortId(value?: string | null): string {
  if (!value) return "-";
  if (value.length <= 14) return value;
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function formatTs(value?: string | null): string {
  if (!value) return "-";
  const ts = new Date(value);
  if (Number.isNaN(ts.getTime())) return value;
  return ts.toLocaleString();
}

function maskSecret(value: string): string {
  const len = Math.max(24, Math.min(96, value.length));
  return "•".repeat(len);
}

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  const base: Record<string, string> = {};
  if (token) {
    base.Authorization = `Bearer ${token}`;
  }

  if (!extra) return base;
  if (extra instanceof Headers) {
    const merged = new Headers(base);
    extra.forEach((v, k) => merged.set(k, v));
    return merged;
  }
  if (Array.isArray(extra)) {
    const merged = new Headers(base);
    for (const [k, v] of extra) merged.set(k, v);
    return merged;
  }
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
    throw new ApiError(resp.status, message);
  }
  return (await resp.json()) as T;
}

function computeExpiryIso(selection: string): string | undefined {
  if (selection === "never") return undefined;
  const days = Number.parseInt(selection.replace("d", ""), 10);
  if (!Number.isFinite(days) || days <= 0) return undefined;
  const target = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  return target.toISOString();
}

export default function ApiKeysPage() {
  const { data: session } = useSession();
  const { toast } = useToast();

  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [auditItems, setAuditItems] = useState<ApiKeyAuditItem[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const [includeRevoked, setIncludeRevoked] = useState(true);
  const [auditKeyFilter, setAuditKeyFilter] = useState("all");

  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    "keys.read",
    "keys.write",
    "memory.read",
    "memory.write",
  ]);
  const [expiryPreset, setExpiryPreset] = useState("90d");
  const [label, setLabel] = useState("");
  const [creating, setCreating] = useState(false);
  const [busyKeyId, setBusyKeyId] = useState<string | null>(null);
  const [reveal, setReveal] = useState<RevealState | null>(null);
  const [isRevealVisible, setIsRevealVisible] = useState(false);

  const userName = useMemo(() => {
    const typed = session as {
      user?: { email?: string; name?: string };
    } | null;
    return typed?.user?.name || typed?.user?.email || "Current user";
  }, [session]);

  const loadKeys = useCallback(async () => {
    setLoadingKeys(true);
    try {
      const data = await apiRequest<ApiKeyListResponse>(
        `/api/v1/api-keys?include_revoked=${includeRevoked ? "true" : "false"}`,
      );
      setKeys(data.items || []);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load API keys";
      toast.error(msg);
    } finally {
      setLoadingKeys(false);
    }
  }, [includeRevoked, toast]);

  const loadAudit = useCallback(async () => {
    setLoadingAudit(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "80");
      if (auditKeyFilter !== "all") {
        params.set("key_id", auditKeyFilter);
      }
      const data = await apiRequest<ApiKeyAuditResponse>(
        `/api/v1/api-keys/audit?${params.toString()}`,
      );
      setAuditItems(data.items || []);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to load API key audit";
      toast.error(msg);
    } finally {
      setLoadingAudit(false);
    }
  }, [auditKeyFilter, toast]);

  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  useEffect(() => {
    void loadAudit();
  }, [loadAudit]);

  const summary = useMemo(() => {
    let active = 0;
    let revoked = 0;
    let expired = 0;
    for (const item of keys) {
      const status = statusForKey(item);
      if (status === "active") active += 1;
      if (status === "revoked") revoked += 1;
      if (status === "expired") expired += 1;
    }
    return { total: keys.length, active, revoked, expired };
  }, [keys]);

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) => {
      if (prev.includes(scope)) {
        return prev.filter((item) => item !== scope);
      }
      return [...prev, scope];
    });
  };

  const createKey = async () => {
    if (selectedScopes.length === 0) {
      toast.info("Select at least one scope before creating a key.");
      return;
    }

    setCreating(true);
    try {
      const payload = {
        label: label.trim() || undefined,
        scopes: selectedScopes,
        expires_at: computeExpiryIso(expiryPreset),
      };

      const response = await apiRequest<ApiKeyCreateResponse>(
        "/api/v1/api-keys",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );

      setReveal({
        keyId: response.key.key_id,
        plaintext: response.plaintext_key,
        mode: "created",
      });
      setIsRevealVisible(false);
      setLabel("");

      toast.success("API key created. Copy it now; it is shown only once.");
      await Promise.all([loadKeys(), loadAudit()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create key";
      toast.error(msg);
    } finally {
      setCreating(false);
    }
  };

  const rotateKey = async (keyId: string) => {
    const ok = window.confirm(
      `Rotate key ${keyId}? The old key will be revoked.`,
    );
    if (!ok) return;

    setBusyKeyId(keyId);
    try {
      const response = await apiRequest<ApiKeyRotateResponse>(
        `/api/v1/api-keys/${encodeURIComponent(keyId)}/rotate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reason: "rotated from dashboard",
          }),
        },
      );

      setReveal({
        keyId: response.new_key.key_id,
        plaintext: response.plaintext_key,
        mode: "rotated",
      });
      setIsRevealVisible(false);
      toast.success("API key rotated. Copy the new key now.");
      await Promise.all([loadKeys(), loadAudit()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to rotate key";
      toast.error(msg);
    } finally {
      setBusyKeyId(null);
    }
  };

  const revokeKey = async (keyId: string) => {
    const ok = window.confirm(
      `Revoke key ${keyId}? This action cannot be undone.`,
    );
    if (!ok) return;

    setBusyKeyId(keyId);
    try {
      await apiRequest<ApiKeyRevokeResponse>(
        `/api/v1/api-keys/${encodeURIComponent(keyId)}/revoke`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reason: "revoked from dashboard",
          }),
        },
      );
      toast.success("API key revoked.");
      await Promise.all([loadKeys(), loadAudit()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to revoke key";
      toast.error(msg);
    } finally {
      setBusyKeyId(null);
    }
  };

  const copyReveal = async () => {
    if (!reveal?.plaintext) return;
    try {
      await navigator.clipboard.writeText(reveal.plaintext);
      toast.success("API key copied to clipboard.");
    } catch {
      toast.error("Clipboard access failed. Copy manually.");
    }
  };

  return (
    <div className="relative min-h-screen space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="API Keys"
        subtitle="Manage Secure Access Matrix and Tenant-Scoped Lifecycle"
        icon={KeyRound}
        actions={
          <Button
            variant="outline"
            leftIcon={<RefreshCw size={14} />}
            onClick={() => {
              void loadKeys();
              void loadAudit();
            }}
            className="rounded-xl border-white/5 bg-white/5 hover:bg-white/10 backdrop-blur-md h-10 px-5 text-[11px] font-bold uppercase tracking-[0.2em]"
            disabled={loadingKeys || loadingAudit}
          >
            Refresh Matrix
          </Button>
        }
      />

      {/* --- Metrics Scorecard (Storage Parity) --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        {[
          {
            label: "Total Keys",
            value: summary.total,
            icon: KeyRound,
            color: "text-cyan-200",
          },
          {
            label: "Active Keys",
            value: summary.active,
            icon: ShieldCheck,
            color: "text-emerald-400",
          },
          {
            label: "Revoked",
            value: summary.revoked,
            icon: ShieldOff,
            color: "text-rose-400",
          },
          {
            label: "Expired",
            value: summary.expired,
            icon: RotateCcw,
            color: "text-amber-400",
          },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className="relative flex flex-col justify-center px-6 py-3"
            style={{
              borderLeft: i > 0 ? "1px solid var(--os-stroke)" : undefined,
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                {stat.label}
              </p>
              <stat.icon size={18} className="opacity-20" />
            </div>
            <p
              className="font-semibold tabular-nums leading-none"
              style={{ fontSize: 26 }}
            >
              <span className={stat.color}>{stat.value}</span>
            </p>
          </div>
        ))}
      </div>

      <div
        className="overflow-hidden rounded-xl border transition-all duration-500"
        style={{
          borderColor: reveal ? "var(--faim-warning)" : "var(--os-stroke)",
          background: reveal
            ? "var(--faim-warning-muted)"
            : "var(--os-surface-1)",
        }}
      >
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-1.5"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
            One-time key reveal
          </p>
          <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
            {reveal
              ? `${reveal.mode === "created" ? "New" : "Rotated"} key: ${reveal.keyId}`
              : "Awaiting key generation"}
          </p>
        </div>
        <div
          className={
            reveal ? "pt-5" : "pt-0 pb-6 opacity-40 transition-all duration-500"
          }
        >
          <AnimatePresence mode="wait">
            {reveal ? (
              <motion.div
                key="revealed"
                initial={{ opacity: 0, height: 0, y: -10, filter: "blur(4px)" }}
                animate={{
                  opacity: 1,
                  height: "auto",
                  y: 0,
                  filter: "blur(0px)",
                }}
                exit={{ opacity: 0, height: 0, y: -10, filter: "blur(4px)" }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="space-y-4 overflow-hidden"
              >
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--faim-warning-text)]">
                  Save this key now. It will not be shown again.
                </p>
                <div
                  className="rounded-xl border p-4 font-mono text-xs break-all text-white shadow-inner"
                  style={{
                    background: "var(--os-surface-2)",
                    borderColor: "var(--os-stroke)",
                  }}
                >
                  {isRevealVisible
                    ? reveal.plaintext
                    : maskSecret(reveal.plaintext)}
                </div>
                <div className="flex gap-3 pb-1">
                  <Button
                    size="sm"
                    variant="outline"
                    leftIcon={
                      isRevealVisible ? <EyeOff size={14} /> : <Eye size={14} />
                    }
                    onClick={() => setIsRevealVisible((prev) => !prev)}
                    className="bg-black/20 border-white/10"
                  >
                    {isRevealVisible ? "Hide key" : "Show key"}
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    leftIcon={<Copy size={14} />}
                    onClick={copyReveal}
                    className="shadow-sm"
                  >
                    Copy key
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setReveal(null)}
                    className="text-slate-400"
                  >
                    Dismiss
                  </Button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="flex flex-col items-center justify-center gap-2 overflow-hidden"
              >
                <KeyRound size={24} className="text-slate-500" />
                <p className="text-[10px] font-bold tracking-widest uppercase text-slate-400">
                  No unrevealed keys
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:items-start">
        <div
          className="overflow-hidden rounded-xl border flex flex-col h-[520px]"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <div
            className="border-b px-5 py-1.5"
            style={{ borderColor: "var(--os-stroke)" }}
          >
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
              Create API key
            </p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
              Actor: {userName}
            </p>
          </div>
          <div className="space-y-5 pt-5 px-5 flex-1">
            <Input
              label="Label (optional)"
              placeholder="billing-bot / retrieval-agent"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              style={{
                background: "var(--os-surface-2)",
                borderColor: "var(--os-stroke)",
              }}
            />

            <div className="space-y-3">
              <p className="text-[10px] uppercase font-bold tracking-[0.15em] text-slate-500">
                Scopes
              </p>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_SCOPES.map((scope) => {
                  const selected = selectedScopes.includes(scope);
                  return (
                    <button
                      key={scope}
                      type="button"
                      className={[
                        "rounded-xl border px-3 py-1.5 text-[11px] font-bold transition-all duration-300",
                        selected
                          ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.15)]"
                          : "border-white/5 bg-white/5 text-slate-400 hover:border-white/20 hover:bg-white/10",
                      ].join(" ")}
                      onClick={() => toggleScope(scope)}
                    >
                      {scope}
                    </button>
                  );
                })}
              </div>
            </div>

            <ThemedSelect
              label="Expiry"
              options={EXPIRY_OPTIONS}
              value={expiryPreset}
              onChange={setExpiryPreset}
            />

            <Button
              leftIcon={<KeyRound size={15} />}
              onClick={createKey}
              loading={creating}
              fullWidth
              className="mt-2"
            >
              Create key
            </Button>
          </div>
        </div>

        <div
          className="lg:col-span-2 overflow-hidden rounded-xl border flex flex-col h-[520px]"
          style={{
            borderColor: "var(--os-stroke)",
            background: "var(--os-surface-1)",
          }}
        >
          <div
            className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-1.5"
            style={{ borderColor: "var(--os-stroke)" }}
          >
            <div>
              <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
                Key Inventory
              </p>
              <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Displaying {summary.total} persistent access identifiers
              </p>
            </div>
            <Button
              size="sm"
              variant={includeRevoked ? "secondary" : "outline"}
              onClick={() => setIncludeRevoked((prev) => !prev)}
              className="rounded-xl border-white/5 h-8 px-3 text-[11px]"
            >
              {includeRevoked ? "Hide revoked" : "Show revoked"}
            </Button>
          </div>
          <div className="pt-0 px-0 flex-1 min-h-0 flex flex-col">
            {loadingKeys && (
              <p className="text-sm text-slate-500 animate-pulse px-5">
                Loading secure keys...
              </p>
            )}
            {!loadingKeys && keys.length === 0 && (
              <p className="py-8 text-center text-sm text-slate-500 italic px-5">
                No API keys found for this tenant.
              </p>
            )}

            {!loadingKeys && keys.length > 0 && (
              <div className="flex-1 overflow-y-auto custom-scrollbar">
                {keys.map((item) => {
                  const status = statusForKey(item);
                  const isBusy = busyKeyId === item.key_id;
                  return (
                    <div
                      key={item.key_id}
                      className="group px-5 py-4 transition-all duration-300 hover:bg-white/[0.02]"
                      style={{ borderBottom: "1px solid var(--os-stroke)" }}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="space-y-1.5 flex-1 min-w-[200px]">
                          <p className="font-mono text-sm font-bold text-white tracking-tight">
                            {item.key_prefix}
                          </p>
                          <div className="space-y-0.5">
                            <p className="text-[10px] text-slate-500 font-mono break-all leading-relaxed">
                              KEY_ID:{" "}
                              <span className="text-slate-400">
                                {item.key_id}
                              </span>
                            </p>
                            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                              CREATED:{" "}
                              <span className="text-slate-400">
                                {formatTs(item.created_at)}
                              </span>
                            </p>
                            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                              EXPIRES:{" "}
                              <span className="text-slate-400">
                                {formatTs(item.expires_at)}
                              </span>{" "}
                              | USED:{" "}
                              <span className="text-slate-400">
                                {formatTs(item.last_used_at)}
                              </span>
                            </p>
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          {status === "active" && (
                            <Badge
                              variant="success"
                              className="h-5 px-3 uppercase text-[9px] font-black tracking-widest shadow-[0_0_10px_rgba(16,185,129,0.15)]"
                            >
                              active
                            </Badge>
                          )}
                          {status === "revoked" && (
                            <Badge
                              variant="error"
                              className="h-5 px-3 uppercase text-[9px] font-black tracking-widest opacity-60"
                            >
                              revoked
                            </Badge>
                          )}
                          {status === "expired" && (
                            <Badge
                              variant="warning"
                              className="h-5 px-3 uppercase text-[9px] font-black tracking-widest opacity-70"
                            >
                              expired
                            </Badge>
                          )}
                          <div className="flex items-center gap-1.5 ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button
                              size="xs"
                              variant="outline"
                              leftIcon={<RotateCcw size={12} />}
                              onClick={() => rotateKey(item.key_id)}
                              disabled={Boolean(item.revoked_at) || isBusy}
                              loading={isBusy}
                              className="h-7 rounded-lg"
                            >
                              Rotate
                            </Button>
                            <Button
                              size="xs"
                              variant="danger"
                              leftIcon={<Trash2 size={12} />}
                              onClick={() => revokeKey(item.key_id)}
                              disabled={Boolean(item.revoked_at) || isBusy}
                              loading={isBusy}
                              className="h-7 rounded-lg"
                            >
                              Revoke
                            </Button>
                          </div>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {item.scopes.length === 0 ? (
                          <Badge variant="default" className="text-[8px] h-4">
                            no scopes
                          </Badge>
                        ) : (
                          item.scopes.map((scope) => (
                            <Badge
                              key={`${item.key_id}:${scope}`}
                              variant="secondary"
                              className="text-[10px] px-2 py-0 h-5 border-white/5 bg-white/5 text-slate-300"
                            >
                              {scope}
                            </Badge>
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      <div
        className="overflow-hidden rounded-xl border flex flex-col h-[400px]"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3"
          style={{ borderColor: "var(--os-stroke)" }}
        >
          <div>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
              Key audit timeline
            </p>
            <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
              Lifecycle events and security signals
            </p>
          </div>
          <div className="w-64">
            <ThemedSelect
              options={[
                { value: "all", label: "All keys" },
                ...keys.map((key) => ({
                  value: key.key_id,
                  label: `${key.key_prefix} (${key.key_id.slice(0, 8)})`,
                })),
              ]}
              value={auditKeyFilter}
              onChange={setAuditKeyFilter}
            />
          </div>
        </div>
        <div className="pt-0 px-0 flex-1 min-h-0 flex flex-col">
          {loadingAudit && (
            <p className="text-sm text-slate-500 animate-pulse px-5">
              Synchronizing audit signals...
            </p>
          )}
          {!loadingAudit && auditItems.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-500 italic px-5">
              No security signals recorded.
            </p>
          )}
          {!loadingAudit && auditItems.length > 0 && (
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {auditItems.map((event) => (
                <div
                  key={event.id}
                  className="group px-5 py-4 flex flex-wrap items-center justify-between gap-4 transition-all hover:bg-[var(--glass-hover)]"
                  style={{ borderBottom: "1px solid var(--os-stroke)" }}
                >
                  <div className="flex items-center gap-4">
                    <Badge
                      variant="outline"
                      className="uppercase text-[9px] font-black tracking-widest px-2.5 h-5 text-slate-300"
                      style={{
                        background: "var(--os-surface-2)",
                        borderColor: "var(--os-stroke)",
                      }}
                    >
                      {event.action}
                    </Badge>
                    <div className="flex flex-col gap-0.5">
                      <span className="font-mono text-xs font-bold text-white tracking-tight">
                        {shortId(event.key_id)}
                      </span>
                      <span className="text-[10px] text-slate-500 tracking-widest font-black uppercase">
                        ACTOR:{" "}
                        <span className="text-slate-400">
                          {event.actor || "system-node"}
                        </span>
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 font-mono block mb-0.5">
                      {formatTs(event.created_at)}
                    </span>
                    <span className="text-[9px] text-slate-600 font-bold uppercase tracking-tighter">
                      REQ_ID: {shortId(event.request_id) || "direct_op"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
