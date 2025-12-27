'use client';

/* =============================================================================
   FAIM LAB — Admin Console (Golden Edition)
   -----------------------------------------------------------------------------
   Requirements:
   - NO separate /profile page. Everything lives inside /admin.
   - TopBar user icon routes into /admin?tab=profile etc.
   - Safe: client-only placeholders; no backend auth assumptions.
   - Dangerous actions require confirmations.
============================================================================= */

import React, { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  KeyRound,
  User,
  CreditCard,
  Shield,
  Trash2,
  LogOut,
  Database,
  Settings,
} from 'lucide-react';
import { API_BASE_URL, buildFaimHeaders } from '@/lib/api';

type TabId = 'profile' | 'account' | 'apikeys' | 'billing' | 'data' | 'security';

type TabDef = {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  description: string;
};

const TABS: TabDef[] = [
  {
    id: 'profile',
    label: 'Profile',
    icon: User,
    description: 'User identity and basic preferences (name/email).',
  },
  {
    id: 'account',
    label: 'Account',
    icon: Settings,
    description: 'Logout, account lifecycle, and account-level controls.',
  },
  {
    id: 'apikeys',
    label: 'API Keys',
    icon: KeyRound,
    description: 'Manage FAIM API keys (server-side).',
  },
  {
    id: 'billing',
    label: 'Billing',
    icon: CreditCard,
    description: 'Plans, invoices, refunds (future backend integration).',
  },
  {
    id: 'data',
    label: 'Data Controls',
    icon: Database,
    description: 'Clear memory, export data, reset workspace data (guarded).',
  },
  {
    id: 'security',
    label: 'Security',
    icon: Shield,
    description: 'Sessions, device logins, audit events (future).',
  },
];

function asTabId(x: string | null | undefined): TabId {
  const v = (x ?? '').toLowerCase().trim();
  const ok = new Set<TabId>(['profile', 'account', 'apikeys', 'billing', 'data', 'security']);
  return ok.has(v as TabId) ? (v as TabId) : 'profile';
}

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ');
}

/* =============================================================================
   Local-only storage keys (safe, no backend assumptions)
============================================================================= */
const LS_PROFILE = 'faim.admin.profile.v1';
const LS_ACTIVE_KEY = 'faim_api_key';
const LS_ADMIN_KEY = 'faim_admin_key';

type ProfileState = {
  displayName: string;
  email: string;
};

type ApiKeyRecord = {
  id: string;
  prefix: string;
  last4: string;
  created_at: number;
  revoked_at?: number | null;
  label?: string | null;
  active?: boolean;
};

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function writeJson<T>(key: string, value: T) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // fail-soft
  }
}

function readActiveKey(): string {
  if (typeof window === 'undefined') return '';
  try {
    return window.localStorage.getItem(LS_ACTIVE_KEY) ?? '';
  } catch {
    return '';
  }
}

function writeActiveKey(value: string) {
  try {
    if (value) {
      window.localStorage.setItem(LS_ACTIVE_KEY, value);
    } else {
      window.localStorage.removeItem(LS_ACTIVE_KEY);
    }
  } catch {
    // ignore
  }
}

function readAdminKey(): string {
  if (typeof window === 'undefined') return '';
  try {
    return window.localStorage.getItem(LS_ADMIN_KEY) ?? '';
  } catch {
    return '';
  }
}

function writeAdminKey(value: string) {
  try {
    if (value) {
      window.localStorage.setItem(LS_ADMIN_KEY, value);
    } else {
      window.localStorage.removeItem(LS_ADMIN_KEY);
    }
  } catch {
    // ignore
  }
}

/* =============================================================================
   Page
============================================================================= */
function AdminPageInner() {

  const router = useRouter();
  const sp = useSearchParams();

  const activeTab = useMemo(() => asTabId(sp.get('tab')), [sp]);

  const [profile, setProfile] = useState<ProfileState>(() =>
    readJson<ProfileState>(LS_PROFILE, { displayName: 'User', email: 'user@local' }),
  );


  useEffect(() => {
    writeJson(LS_PROFILE, profile);
  }, [profile]);


  const goTab = (id: TabId) => {
    router.push(`/admin?tab=${encodeURIComponent(id)}`);
  };

  const tabDef = TABS.find((t) => t.id === activeTab) ?? TABS[0];

  return (
    <div className="space-y-4">
      {/* Header */}
      <header className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-sm font-semibold text-slate-100">Admin</h1>
            <p className="mt-1 text-xs text-slate-400">
              Single control center for Profile, Account, API Keys, Billing, and Data Controls.
            </p>
          </div>

          <div className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-3 py-1 text-[11px] text-cyan-100">
            Active: {tabDef.label}
          </div>
        </div>
      </header>

      {/* Layout */}
      <section className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        {/* Left nav */}
        <aside className="rounded-2xl border border-slate-800 bg-slate-900/40 p-2">
          <div className="px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-slate-400">
            Admin Sections
          </div>

          <nav className="space-y-1 p-2">
            {TABS.map((t) => {
              const Icon = t.icon;
              const active = t.id === activeTab;
              return (
                <button
                  key={t.id}
                  onClick={() => goTab(t.id)}
                  className={cx(
                    'w-full text-left group flex items-center gap-3 rounded-xl px-3 py-2 transition',
                    active
                      ? 'border border-cyan-400/25 bg-cyan-500/10 text-cyan-100'
                      : 'border border-transparent hover:border-white/10 hover:bg-white/5 text-slate-200',
                  )}
                >
                  <Icon size={16} className={cx(active ? 'text-cyan-200' : 'text-slate-400 group-hover:text-cyan-200')} />
                  <div className="min-w-0">
                    <div className="text-[12px] font-medium">{t.label}</div>
                    <div className="text-[11px] text-slate-500 truncate">{t.description}</div>
                  </div>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Right content */}
        <main className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="mb-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
              {tabDef.label}
            </h2>
            <p className="mt-1 text-[11px] text-slate-500">{tabDef.description}</p>
          </div>

          {activeTab === 'profile' ? (
            <ProfilePanel profile={profile} setProfile={setProfile} />
          ) : null}

          {activeTab === 'apikeys' ? <ApiKeysPanel /> : null}

          {activeTab === 'billing' ? <BillingPanel /> : null}

          {activeTab === 'data' ? <DataControlsPanel /> : null}

          {activeTab === 'account' ? <AccountPanel /> : null}

          {activeTab === 'security' ? <SecurityPanel /> : null}
        </main>
      </section>
    </div>
  );
}
export default function AdminPage() {
  return (
    <Suspense fallback={<div className="p-4 text-xs text-slate-400">Loading admin…</div>}>
      <AdminPageInner />
    </Suspense>
  );
}

/* =============================================================================
   Panels
============================================================================= */

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="block">
      <div className="mb-1 text-[11px] text-slate-400">{label}</div>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={cx(
          'w-full rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2 text-[12px] text-slate-100',
          'outline-none focus:border-cyan-400/30 focus:ring-2 focus:ring-cyan-500/10',
        )}
      />
    </label>
  );
}

function ProfilePanel({
  profile,
  setProfile,
}: {
  profile: ProfileState;
  setProfile: (p: ProfileState) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <Field
          label="Display name"
          value={profile.displayName}
          onChange={(v) => setProfile({ ...profile, displayName: v })}
          placeholder="Your name"
        />
        <Field
          label="Email"
          value={profile.email}
          onChange={(v) => setProfile({ ...profile, email: v })}
          placeholder="you@example.com"
          type="email"
        />
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Notes</div>
        <ul className="mt-2 list-disc pl-5 text-[11px] text-slate-500 space-y-1">
          <li>This is stored locally for now (no auth backend wired yet).</li>
          <li>Once auth exists, these fields should sync to your user record.</li>
        </ul>
      </div>
    </div>
  );
}

function ApiKeysPanel() {
  const [keys, setKeys] = useState<ApiKeyRecord[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [label, setLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeKey, setActiveKey] = useState('');
  const [adminKey, setAdminKey] = useState('');

  const fetchKeys = async () => {
    const adminHeader = (adminKey || readAdminKey()).trim();
    try {
      const res = await fetch(`${API_BASE_URL}/keys`, {
        cache: 'no-store',
        headers: buildFaimHeaders(
          adminHeader ? { 'X-FAIM-ADMIN-KEY': adminHeader } : undefined,
        ),
      });
      if (!res.ok) throw new Error('Failed to fetch keys');
      const data = (await res.json()) as { keys?: ApiKeyRecord[] };
      setKeys(Array.isArray(data.keys) ? data.keys : []);
      setError(null);
    } catch (err) {
      setError('Unable to load keys from FAIM backend.');
    }
  };

  useEffect(() => {
    setActiveKey(readActiveKey());
    setAdminKey(readAdminKey());
    void fetchKeys();
  }, []);

  const createKey = async () => {
    setLoading(true);
    const adminHeader = (adminKey || readAdminKey()).trim();
    try {
      const res = await fetch(`${API_BASE_URL}/keys`, {
        method: 'POST',
        headers: buildFaimHeaders({
          'Content-Type': 'application/json',
          ...(adminHeader ? { 'X-FAIM-ADMIN-KEY': adminHeader } : {}),
        }),
        body: JSON.stringify({ label: label.trim() || undefined }),
      });
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(text || 'Failed to create key');
      }
      const data = (await res.json()) as { key?: string; record?: ApiKeyRecord };
      setNewKey(data.key ?? null);
      if (data.key) {
        setActiveKey(data.key);
        writeActiveKey(data.key);
      }
      await fetchKeys();
      setLabel('');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create key.');
    } finally {
      setLoading(false);
    }
  };

  const revokeKey = async (id: string, hard = false) => {
    setLoading(true);
    const adminHeader = (adminKey || readAdminKey()).trim();
    try {
      const res = await fetch(
        `${API_BASE_URL}/keys/${encodeURIComponent(id)}${hard ? '?hard=1' : ''}`,
        {
        method: 'DELETE',
        headers: buildFaimHeaders(
          adminHeader ? { 'X-FAIM-ADMIN-KEY': adminHeader } : undefined,
        ),
        },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to revoke key');
      }
      await fetchKeys();
      setError(null);
    } catch {
      setError('Unable to revoke key.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 text-[11px] text-amber-100/90">
        FAIM API keys are stored on the server. Generate once and store securely in your SaaS app.
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Active key (this browser)</div>
        <p className="mt-1 text-[11px] text-slate-500">
          This key is used by the FAIM UI to call protected endpoints.
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
          <Field
            label="FAIM API key"
            value={activeKey}
            onChange={(v) => setActiveKey(v)}
            placeholder="faim_live_..."
          />
          <button
            onClick={() => writeActiveKey(activeKey.trim())}
            className="mt-[22px] inline-flex items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-[12px] text-cyan-100"
          >
            Save key
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Admin key (key management)</div>
        <p className="mt-1 text-[11px] text-slate-500">
          Required only when FAIM_ADMIN_KEY is set on the backend.
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
          <Field
            label="FAIM admin key"
            value={adminKey}
            onChange={(v) => setAdminKey(v)}
            placeholder="faim_admin_..."
          />
          <button
            onClick={() => writeAdminKey(adminKey.trim())}
            className="mt-[22px] inline-flex items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-[12px] text-cyan-100"
          >
            Save admin key
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Generate FAIM API key</div>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto]">
          <Field
            label="Key label (optional)"
            value={label}
            onChange={setLabel}
            placeholder="linkweave-prod"
          />
          <button
            onClick={createKey}
            disabled={loading}
            className="mt-[22px] inline-flex items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-[12px] text-cyan-100"
          >
            {loading ? 'Working...' : 'Create key'}
          </button>
        </div>
        {newKey && (
          <div className="mt-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-[12px] text-emerald-100">
            New key (copy now): <span className="font-semibold">{newKey}</span>
          </div>
        )}
        {error && (
          <div className="mt-3 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-100">
            {error}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Active keys</div>
        <div className="mt-3 space-y-2">
          {keys.filter((k) => k.revoked_at == null).length === 0 && (
            <div className="text-[11px] text-slate-500">No keys created yet.</div>
          )}
          {keys.filter((k) => k.revoked_at == null).map((k) => {
            const revoked = k.revoked_at != null;
            return (
              <div
                key={k.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-[11px]"
              >
                <div>
                  <div className="text-slate-100">
                    {k.label || 'FAIM key'} · {k.prefix}••••{k.last4}
                  </div>
                  <div className="text-slate-500">
                    {revoked ? 'revoked' : 'active'} · created{' '}
                    {new Date(k.created_at * 1000).toLocaleString()}
                  </div>
                </div>
                <button
                  onClick={() => revokeKey(k.id, false)}
                  disabled={loading || revoked}
                  className="inline-flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-100"
                >
                  <Trash2 size={14} /> Revoke
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Revoked keys</div>
        <div className="mt-3 space-y-2">
          {keys.filter((k) => k.revoked_at != null).length === 0 && (
            <div className="text-[11px] text-slate-500">No revoked keys.</div>
          )}
          {keys.filter((k) => k.revoked_at != null).map((k) => (
            <div
              key={k.id}
              className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2 text-[11px]"
            >
              <div>
                <div className="text-slate-100">
                  {k.label || 'FAIM key'} · {k.prefix}••••{k.last4}
                </div>
                <div className="text-slate-500">
                  revoked · created {new Date(k.created_at * 1000).toLocaleString()}
                </div>
              </div>
              <button
                onClick={() => revokeKey(k.id, true)}
                disabled={loading}
                className="inline-flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-100"
              >
                <Trash2 size={14} /> Delete
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BillingPanel() {
  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Billing (placeholder)</div>
        <p className="mt-2 text-[11px] text-slate-500">
          When backend is ready, this tab will show: plan, invoices, payment history, refunds.
        </p>
      </div>
    </div>
  );
}

function DataControlsPanel() {
  const [confirm, setConfirm] = useState('');

  const canDanger = confirm.trim().toUpperCase() === 'DELETE';

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Export data</div>
        <p className="mt-2 text-[11px] text-slate-500">
          Future: export memories, graphs, and audit logs as a downloadable bundle.
        </p>
        <button
          className="mt-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[12px] text-slate-100 hover:bg-white/10"
          onClick={() => alert('Export will be wired to backend later.')}
        >
          Export (placeholder)
        </button>
      </div>

      <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4">
        <div className="text-[12px] font-medium text-rose-100">Danger Zone</div>
        <p className="mt-2 text-[11px] text-rose-100/80">
          Clearing memory is destructive. In production this must require auth + confirmations.
        </p>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="block">
            <div className="mb-1 text-[11px] text-rose-100/70">Type DELETE to unlock</div>
            <input
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-xl border border-rose-500/20 bg-slate-950/40 px-3 py-2 text-[12px] text-slate-100 outline-none"
              placeholder="DELETE"
            />
          </label>

          <button
            disabled={!canDanger}
            onClick={() => alert('Clear data will be wired to backend later.')}
            className={cx(
              'h-[40px] rounded-xl px-3 text-[12px] inline-flex items-center justify-center gap-2',
              canDanger
                ? 'border border-rose-500/30 bg-rose-500/15 text-rose-100 hover:bg-rose-500/20'
                : 'border border-white/10 bg-white/5 text-slate-500 cursor-not-allowed',
            )}
          >
            <Trash2 size={16} /> Clear all memory (placeholder)
          </button>
        </div>
      </div>
    </div>
  );
}

function AccountPanel() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Session</div>
        <p className="mt-2 text-[11px] text-slate-500">
          In production this is tied to auth. For now these are placeholders.
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => alert('Logout will be wired to auth later.')}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[12px] text-slate-100 hover:bg-white/10"
          >
            <LogOut size={16} /> Log out (placeholder)
          </button>
        </div>
      </div>

      <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4">
        <div className="text-[12px] font-medium text-rose-100">Delete account</div>
        <p className="mt-2 text-[11px] text-rose-100/80">
          This is irreversible. In production: require password/2FA + retention policies.
        </p>
        <button
          onClick={() => alert('Delete account will be wired to backend later.')}
          className="mt-3 inline-flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/15 px-3 py-2 text-[12px] text-rose-100 hover:bg-rose-500/20"
        >
          <Trash2 size={16} /> Delete account (placeholder)
        </button>
      </div>
    </div>
  );
}

function SecurityPanel() {
  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
        <div className="text-[12px] font-medium text-slate-100">Security (placeholder)</div>
        <ul className="mt-2 list-disc pl-5 text-[11px] text-slate-500 space-y-1">
          <li>Active sessions/devices</li>
          <li>2FA (future)</li>
          <li>Audit events</li>
          <li>Admin actions log</li>
        </ul>
      </div>
    </div>
  );
}
