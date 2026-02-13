"use client";

import {
  Copy,
  KeyRound,
  RefreshCw,
  RotateCcw,
  Shield,
  ShieldCheck,
  ShieldOff,
  Trash2,
} from "lucide-react";
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
      const payload = (await resp.json()) as { detail?: string; error?: string };
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
  const { notifySuccess, notifyError, notifyInfo } = useToast();

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

  const userName = useMemo(() => {
    const typed = session as { user?: { email?: string; name?: string } } | null;
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
      const msg = err instanceof Error ? err.message : "Failed to load API keys";
      notifyError(msg);
    } finally {
      setLoadingKeys(false);
    }
  }, [includeRevoked, notifyError]);

  const loadAudit = useCallback(async () => {
    setLoadingAudit(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "80");
      if (auditKeyFilter !== "all") {
        params.set("key_id", auditKeyFilter);
      }
      const data = await apiRequest<ApiKeyAuditResponse>(`/api/v1/api-keys/audit?${params.toString()}`);
      setAuditItems(data.items || []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load API key audit";
      notifyError(msg);
    } finally {
      setLoadingAudit(false);
    }
  }, [auditKeyFilter, notifyError]);

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
      notifyInfo("Select at least one scope before creating a key.");
      return;
    }

    setCreating(true);
    try {
      const payload = {
        label: label.trim() || undefined,
        scopes: selectedScopes,
        expires_at: computeExpiryIso(expiryPreset),
      };

      const response = await apiRequest<ApiKeyCreateResponse>("/api/v1/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      setReveal({
        keyId: response.key.key_id,
        plaintext: response.plaintext_key,
        mode: "created",
      });
      setLabel("");

      notifySuccess("API key created. Copy it now; it is shown only once.");
      await Promise.all([loadKeys(), loadAudit()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create key";
      notifyError(msg);
    } finally {
      setCreating(false);
    }
  };

  const rotateKey = async (keyId: string) => {
    const ok = window.confirm(`Rotate key ${keyId}? The old key will be revoked.`);
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
      notifySuccess("API key rotated. Copy the new key now.");
      await Promise.all([loadKeys(), loadAudit()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to rotate key";
      notifyError(msg);
    } finally {
      setBusyKeyId(null);
    }
  };

  const revokeKey = async (keyId: string) => {
    const ok = window.confirm(`Revoke key ${keyId}? This action cannot be undone.`);
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
      notifySuccess("API key revoked.");
      await Promise.all([loadKeys(), loadAudit()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to revoke key";
      notifyError(msg);
    } finally {
      setBusyKeyId(null);
    }
  };

  const copyReveal = async () => {
    if (!reveal?.plaintext) return;
    try {
      await navigator.clipboard.writeText(reveal.plaintext);
      notifySuccess("API key copied to clipboard.");
    } catch {
      notifyError("Clipboard access failed. Copy manually.");
    }
  };

  return (
    <div className="space-y-6 pb-8 text-[var(--text-primary)]">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">API Keys</h1>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Tenant-scoped key lifecycle, scope control, rotation, revocation, and audit history.
          </p>
        </div>
        <Button
          variant="outline"
          leftIcon={<RefreshCw size={15} />}
          onClick={() => {
            void loadKeys();
            void loadAudit();
          }}
          disabled={loadingKeys || loadingAudit}
        >
          Refresh
        </Button>
      </header>

      {reveal && (
        <Card className="rounded-2xl border border-[var(--faim-warning)]/30 bg-[var(--faim-warning-muted)]">
          <CardHeader
            title="One-time key reveal"
            description={`${reveal.mode === "created" ? "New" : "Rotated"} key: ${reveal.keyId}`}
          />
          <CardContent className="space-y-3 pt-3">
            <p className="text-xs text-[var(--text-secondary)]">
              Save this key now. It will not be shown again.
            </p>
            <div className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-2)] p-3 font-mono text-xs break-all">
              {reveal.plaintext}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="primary" leftIcon={<Copy size={14} />} onClick={copyReveal}>
                Copy key
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setReveal(null)}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="rounded-2xl">
          <CardHeader title="Create API key" description={`Actor: ${userName}`} />
          <CardContent className="space-y-4 pt-4">
            <Input
              label="Label (optional)"
              placeholder="billing-bot / retrieval-agent"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />

            <div className="space-y-2">
              <p className="text-xs text-[var(--text-secondary)]">Scopes</p>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_SCOPES.map((scope) => {
                  const selected = selectedScopes.includes(scope);
                  return (
                    <button
                      key={scope}
                      type="button"
                      className={[
                        "rounded-lg border px-2 py-1 text-xs transition-colors",
                        selected
                          ? "border-[var(--faim-primary)] bg-[var(--faim-primary-muted)] text-[var(--faim-primary)]"
                          : "border-[var(--border-default)] bg-[var(--surface-2)] text-[var(--text-secondary)] hover:border-[var(--border-primary)]",
                      ].join(" ")}
                      onClick={() => toggleScope(scope)}
                    >
                      {scope}
                    </button>
                  );
                })}
              </div>
            </div>

            <Select
              label="Expiry"
              options={EXPIRY_OPTIONS}
              value={expiryPreset}
              onChange={setExpiryPreset}
              fullWidth
            />

            <Button
              leftIcon={<KeyRound size={15} />}
              onClick={createKey}
              loading={creating}
              fullWidth
            >
              Create key
            </Button>
          </CardContent>
        </Card>

        <Card className="rounded-2xl lg:col-span-2">
          <CardHeader
            title="Key inventory"
            description={`Total ${summary.total} | Active ${summary.active} | Revoked ${summary.revoked} | Expired ${summary.expired}`}
            action={
              <Button
                size="sm"
                variant={includeRevoked ? "secondary" : "outline"}
                onClick={() => setIncludeRevoked((prev) => !prev)}
              >
                {includeRevoked ? "Hide revoked" : "Show revoked"}
              </Button>
            }
          />
          <CardContent className="space-y-3 pt-4">
            {loadingKeys && <p className="text-sm text-[var(--text-secondary)]">Loading keys...</p>}
            {!loadingKeys && keys.length === 0 && (
              <p className="text-sm text-[var(--text-secondary)]">No API keys found for this tenant.</p>
            )}

            {!loadingKeys &&
              keys.map((item) => {
                const status = statusForKey(item);
                const isBusy = busyKeyId === item.key_id;
                return (
                  <div
                    key={item.key_id}
                    className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-2)] p-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <p className="font-mono text-sm">{item.key_prefix}</p>
                        <p className="text-xs text-[var(--text-secondary)]">
                          key_id: {shortId(item.key_id)} | created: {formatTs(item.created_at)}
                        </p>
                        <p className="text-xs text-[var(--text-secondary)]">
                          expires: {formatTs(item.expires_at)} | last used: {formatTs(item.last_used_at)}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {status === "active" && (
                          <Badge variant="success" icon={<ShieldCheck size={12} />}>
                            active
                          </Badge>
                        )}
                        {status === "revoked" && (
                          <Badge variant="error" icon={<ShieldOff size={12} />}>
                            revoked
                          </Badge>
                        )}
                        {status === "expired" && (
                          <Badge variant="warning" icon={<Shield size={12} />}>
                            expired
                          </Badge>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          leftIcon={<RotateCcw size={14} />}
                          onClick={() => rotateKey(item.key_id)}
                          disabled={Boolean(item.revoked_at) || isBusy}
                          loading={isBusy}
                        >
                          Rotate
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          leftIcon={<Trash2 size={14} />}
                          onClick={() => revokeKey(item.key_id)}
                          disabled={Boolean(item.revoked_at) || isBusy}
                          loading={isBusy}
                        >
                          Revoke
                        </Button>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {item.scopes.length === 0 ? (
                        <Badge variant="default">no scopes</Badge>
                      ) : (
                        item.scopes.map((scope) => (
                          <Badge key={`${item.key_id}:${scope}`} size="xs" variant="info">
                            {scope}
                          </Badge>
                        ))
                      )}
                    </div>
                  </div>
                );
              })}
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl">
        <CardHeader
          title="Key audit timeline"
          description="Lifecycle events for key creation, rotation, revocation, and verification."
          action={
            <div className="w-56">
              <Select
                options={[
                  { value: "all", label: "All keys" },
                  ...keys.map((key) => ({
                    value: key.key_id,
                    label: `${key.key_prefix} (${shortId(key.key_id)})`,
                  })),
                ]}
                value={auditKeyFilter}
                onChange={setAuditKeyFilter}
                fullWidth
              />
            </div>
          }
        />
        <CardContent className="space-y-2 pt-4">
          {loadingAudit && <p className="text-sm text-[var(--text-secondary)]">Loading audit timeline...</p>}
          {!loadingAudit && auditItems.length === 0 && (
            <p className="text-sm text-[var(--text-secondary)]">No audit events available.</p>
          )}
          {!loadingAudit &&
            auditItems.map((event) => (
              <div
                key={event.id}
                className="rounded-xl border border-[var(--border-default)] bg-[var(--surface-2)] p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{event.action}</Badge>
                    <span className="font-mono text-xs text-[var(--text-secondary)]">
                      {shortId(event.key_id)}
                    </span>
                  </div>
                  <span className="text-xs text-[var(--text-secondary)]">{formatTs(event.created_at)}</span>
                </div>
                <p className="mt-2 text-xs text-[var(--text-secondary)]">
                  actor: {event.actor || "-"} | request: {event.request_id || "-"}
                </p>
              </div>
            ))}
        </CardContent>
      </Card>
    </div>
  );
}
