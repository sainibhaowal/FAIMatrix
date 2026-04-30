"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import QRCode from "qrcode";
import { useUser } from "@/contexts/UserContext";
import {
  User,
  Settings,
  ShieldAlert,
  Fingerprint,
  Database,
  Clock,
  ShieldCheck,
  LogOut,
  KeyRound,
  Smartphone,
} from "lucide-react";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Button } from "@/components/ui/Button";

// Real Identity Avatars (clean, no dev prefixes)
const AVATARS = [
  { id: "avatar_01", style: "adventurer", seed: "Felix", bg: "b6e3f4" },
  { id: "avatar_02", style: "adventurer", seed: "Aneka", bg: "c0aede" },
  { id: "avatar_03", style: "adventurer", seed: "Leo", bg: "d1fae5" },
  { id: "avatar_04", style: "adventurer", seed: "Mia", bg: "fde68a" },
  { id: "avatar_11", style: "bottts", seed: "Robot1", bg: "0ea5e9" },
  { id: "avatar_12", style: "bottts", seed: "Robot2", bg: "8b5cf6" },
  { id: "avatar_13", style: "fun-emoji", seed: "Happy", bg: "fbbf24" },
  { id: "avatar_14", style: "fun-emoji", seed: "Cool", bg: "34d399" },
  { id: "avatar_19", style: "notionists", seed: "Pro", bg: "e5e7eb" },
  { id: "avatar_20", style: "notionists", seed: "Dev", bg: "fef3c7" },
  { id: "avatar_23", style: "personas", seed: "Zen", bg: "ddd6fe" },
  { id: "avatar_24", style: "personas", seed: "Max", bg: "ccfbf1" },
];

function getAvatarUrl(avatarId: string): string {
  const avatar = AVATARS.find((a) => a.id === avatarId) || AVATARS[0];
  return `https://api.dicebear.com/7.x/${avatar.style}/svg?seed=${avatar.seed}&backgroundColor=${avatar.bg}&size=256`;
}

type TotpStatus = {
  enabled: boolean;
  recovery_codes_remaining: number;
};

async function readJsonSafely<T>(res: Response): Promise<T | null> {
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default function ProfilePage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [avatarId, setAvatarId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConfirmStep, setDeleteConfirmStep] = useState(0); // 0: none, 1: warning, 2: type confirm
  const [deleteInput, setDeleteInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [totpStatus, setTotpStatus] = useState<TotpStatus | null>(null);
  const [totpSetup, setTotpSetup] = useState<{
    secret: string;
    otpauth_url: string;
    qr: string;
  } | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [totpDisableFactor, setTotpDisableFactor] = useState<
    "totp" | "recovery_code"
  >("totp");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [totpBusy, setTotpBusy] = useState(false);
  const [totpMessage, setTotpMessage] = useState<string | null>(null);
  const [totpError, setTotpError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    const loadProfile = async () => {
      try {
        const token = (session as any)?.accessToken;
        if (!token) return;
        const res = await fetch("/api/v1/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await readJsonSafely<{ user?: { avatar_id?: string } }>(
            res,
          );
          if (!data) return;
          if (data.user?.avatar_id) setAvatarId(data.user.avatar_id);
        }
      } catch {}
    };
    loadProfile();
  }, [session]);

  const authHeaders = useCallback((): Record<string, string> => {
    const token = (session as any)?.accessToken;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [session]);

  const loadTotpStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/auth/totp/status", {
        headers: authHeaders(),
      });
      if (!res.ok) return;
      const data = await readJsonSafely<{
        enabled?: boolean;
        recovery_codes_remaining?: number;
      }>(res);
      if (!data) return;
      setTotpStatus({
        enabled: Boolean(data.enabled),
        recovery_codes_remaining: data.recovery_codes_remaining || 0,
      });
    } catch {}
  }, [authHeaders]);

  useEffect(() => {
    if (!session) return;
    void loadTotpStatus();
  }, [session, loadTotpStatus]);

  const startTotpSetup = async () => {
    setTotpBusy(true);
    setTotpError(null);
    setTotpMessage(null);
    setRecoveryCodes([]);
    try {
      const res = await fetch("/api/v1/auth/totp/setup", {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await readJsonSafely<{
        success?: boolean;
        detail?: string;
        message?: string;
        secret?: string;
        otpauth_url?: string;
      }>(res);
      if (!data) {
        throw new Error("Unexpected response from authenticator setup");
      }
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || "Failed to start setup");
      }
      if (!data.secret || !data.otpauth_url) {
        throw new Error("Authenticator setup response was incomplete");
      }
      const qr = await QRCode.toDataURL(data.otpauth_url, {
        margin: 1,
        width: 180,
        color: { dark: "#020617", light: "#ffffff" },
      });
      setTotpSetup({
        secret: data.secret,
        otpauth_url: data.otpauth_url,
        qr,
      });
      setTotpMessage("Scan the QR code, then enter one authenticator code.");
    } catch (err: any) {
      setTotpError(err.message || "Failed to start setup");
    } finally {
      setTotpBusy(false);
    }
  };

  const confirmTotpSetup = async () => {
    setTotpBusy(true);
    setTotpError(null);
    setTotpMessage(null);
    try {
      const res = await fetch("/api/v1/auth/totp/confirm", {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ code: totpCode }),
      });
      const data = await readJsonSafely<{
        success?: boolean;
        detail?: string;
        message?: string;
        recovery_codes?: string[];
      }>(res);
      if (!data) {
        throw new Error("Unexpected response from authenticator confirmation");
      }
      if (!res.ok || !data.success) {
        throw new Error(
          data.detail || data.message || "Invalid authenticator code",
        );
      }
      setRecoveryCodes(data.recovery_codes || []);
      setTotpSetup(null);
      setTotpCode("");
      setTotpMessage(
        "Authenticator login is enabled. Save your recovery codes now.",
      );
      await loadTotpStatus();
    } catch (err: any) {
      setTotpError(err.message || "Failed to enable authenticator login");
    } finally {
      setTotpBusy(false);
    }
  };

  const regenerateRecoveryCodes = async () => {
    setTotpBusy(true);
    setTotpError(null);
    setTotpMessage(null);
    try {
      const res = await fetch("/api/v1/auth/totp/recovery-codes/regenerate", {
        method: "POST",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ code: totpCode }),
      });
      const data = await readJsonSafely<{
        success?: boolean;
        detail?: string;
        message?: string;
        recovery_codes?: string[];
      }>(res);
      if (!data) {
        throw new Error("Unexpected response from recovery code regeneration");
      }
      if (!res.ok || !data.success) {
        throw new Error(
          data.detail || data.message || "Invalid authenticator code",
        );
      }
      setRecoveryCodes(data.recovery_codes || []);
      setTotpCode("");
      setTotpMessage("New recovery codes generated. Save them now.");
      await loadTotpStatus();
    } catch (err: any) {
      setTotpError(err.message || "Failed to regenerate recovery codes");
    } finally {
      setTotpBusy(false);
    }
  };

  const disableTotp = async () => {
    setTotpBusy(true);
    setTotpError(null);
    setTotpMessage(null);
    try {
      const res = await fetch("/api/v1/auth/totp", {
        method: "DELETE",
        headers: { ...authHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({
          code: totpCode,
          factor_type: totpDisableFactor,
        }),
      });
      const data = await readJsonSafely<{
        success?: boolean;
        detail?: string;
        message?: string;
      }>(res);
      if (!data) {
        throw new Error("Unexpected response from authenticator disable");
      }
      if (!res.ok || !data.success) {
        throw new Error(
          data.detail || data.message || "Invalid authenticator code",
        );
      }
      setTotpCode("");
      setTotpDisableFactor("totp");
      setTotpSetup(null);
      setRecoveryCodes([]);
      setTotpMessage("Authenticator login disabled. Email OTP remains active.");
      await loadTotpStatus();
    } catch (err: any) {
      setTotpError(err.message || "Failed to disable authenticator login");
    } finally {
      setTotpBusy(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteInput.toLowerCase() !== "delete") return;

    setIsDeleting(true);
    setError(null);
    try {
      const token = (session as any)?.accessToken;
      const res = await fetch("/api/v1/auth/me", {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        signOut({ callbackUrl: "/auth/login" });
      } else {
        const errData = await res
          .json()
          .catch(() => ({ detail: "Unknown error" }));
        setError(
          errData.detail || "Failed to delete account. Please try again.",
        );
        setIsDeleting(false);
      }
    } catch (err) {
      setError("An error occurred during deletion.");
      setIsDeleting(false);
    }
  };

  const { userId: contextUserId, graphId: contextGraphId } = useUser();
  const user = session?.user;
  const userId = contextUserId || (user as any)?.id;
  const graphId = contextGraphId || (session as any)?.graphId || "N/A";
  const tenantId = userId ? `user:${userId}` : "N/A";

  return (
    <div className="relative space-y-4 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="Identity Hub"
        subtitle="Real-time profile and data sovereignty management"
        icon={User}
        actions={
          <Button
            size="sm"
            variant="outline"
            onClick={() => signOut({ callbackUrl: "/auth/login" })}
            leftIcon={<LogOut size={14} />}
          >
            Sign Out
          </Button>
        }
      />

      {/* --- Profile Metric Strip --- */}
      <div
        className="grid grid-cols-1 overflow-hidden rounded-xl border sm:grid-cols-2 xl:grid-cols-4"
        style={{
          borderColor: "var(--os-stroke)",
          background: "var(--os-surface-1)",
        }}
      >
        {[
          {
            label: "Access Level",
            value: "Root Admin",
            icon: <ShieldCheck size={18} />,
            color: "text-cyan-200",
          },
          {
            label: "Session Age",
            value: "2.4h",
            icon: <Clock size={18} />,
            color: "text-emerald-400",
          },
          {
            label: "Graph Context",
            value: "Active",
            icon: <Database size={18} />,
            color: "text-amber-400",
          },
          {
            label: "Identity Hash",
            value: "U:621b",
            icon: <Fingerprint size={18} />,
            color: "text-slate-400",
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
              <div className="opacity-20">{stat.icon}</div>
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Left: Avatar Panel */}
        <div className="lg:col-span-1">
          <div
            className="rounded-xl border overflow-hidden"
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
                Neural Avatar
              </p>
            </div>
            <div className="p-8 flex flex-col items-center">
              <div
                className="relative h-32 w-32 rounded-full overflow-hidden border p-1"
                style={{
                  borderColor: "var(--os-stroke)",
                  background: "var(--os-surface-2)",
                }}
              >
                {avatarId || user?.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={avatarId ? getAvatarUrl(avatarId) : user!.image!}
                    alt={user?.name || "User"}
                    className="h-full w-full rounded-full object-cover"
                  />
                ) : (
                  <div className="h-full w-full rounded-full flex items-center justify-center bg-slate-800 text-3xl font-bold text-slate-500">
                    {user?.name?.[0]?.toUpperCase() || "?"}
                  </div>
                )}
              </div>
              <div className="mt-4 text-center">
                <h2 className="text-lg font-bold text-white leading-tight">
                  {user?.name || "Authenticated User"}
                </h2>
                <div className="mt-1 text-[10px] text-slate-500 font-mono uppercase tracking-widest">
                  Identity Validated
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Technical Details Panel */}
        <div className="lg:col-span-3 space-y-6">
          <div
            className="rounded-xl border overflow-hidden"
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
                Technical Parameters
              </p>
            </div>
            <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-8">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  Name
                </label>
                <div className="text-sm font-medium text-slate-200">
                  {user?.name || "N/A"}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  Email
                </label>
                <div className="text-sm font-medium text-slate-200">
                  {user?.email || "N/A"}
                </div>
              </div>
              <div className="space-y-1 md:col-span-2">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  User ID
                </label>
                <div className="text-[11px] font-mono text-cyan-400 bg-cyan-400/5 px-3 py-2 rounded border border-cyan-400/10 break-all leading-relaxed">
                  {userId || "N/A"}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  Tenant ID
                </label>
                <div className="text-[11px] font-mono text-slate-400 bg-white/5 px-3 py-2 rounded border border-white/5 break-all">
                  {tenantId}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  Graph ID
                </label>
                <div className="text-[11px] font-mono text-slate-400 bg-white/5 px-3 py-2 rounded border border-white/5 break-all">
                  {graphId}
                </div>
              </div>
            </div>
          </div>

          {/* Authenticator Security */}
          <div
            className="rounded-xl border overflow-hidden"
            style={{
              borderColor: "rgba(34, 211, 238, 0.22)",
              background: "rgba(8, 47, 73, 0.14)",
            }}
          >
            <div
              className="border-b px-5 py-3 flex items-center justify-between gap-3"
              style={{ borderColor: "rgba(34, 211, 238, 0.14)" }}
            >
              <div className="flex items-center gap-2">
                <KeyRound size={14} className="text-cyan-300" />
                <p className="text-[10px] font-medium uppercase tracking-widest text-cyan-300">
                  Authenticator Login
                </p>
              </div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500">
                {totpStatus?.enabled ? "Enabled" : "Optional"}
              </div>
            </div>
            <div className="p-8 space-y-6">
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_auto]">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
                      <Smartphone size={18} />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        {totpStatus?.enabled
                          ? "Authenticator app is active"
                          : "Use Google Authenticator, Authy, or another app"}
                      </h3>
                      <p className="text-xs text-slate-500">
                        Email OTP stays as the default. Once enabled, you can
                        sign in faster with a 6-digit authenticator code.
                      </p>
                    </div>
                  </div>

                  {totpStatus?.enabled && (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <div className="rounded-lg border border-white/10 bg-black/20 px-4 py-3">
                        <div className="text-[10px] uppercase tracking-widest text-slate-500">
                          Recovery Codes
                        </div>
                        <div className="mt-1 text-lg font-semibold text-cyan-200">
                          {totpStatus.recovery_codes_remaining}
                        </div>
                      </div>
                      <div className="rounded-lg border border-white/10 bg-black/20 px-4 py-3">
                        <div className="text-[10px] uppercase tracking-widest text-slate-500">
                          Default Login
                        </div>
                        <div className="mt-1 text-lg font-semibold text-slate-200">
                          Email OTP
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {!totpStatus?.enabled && !totpSetup && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={startTotpSetup}
                    disabled={totpBusy}
                    leftIcon={<KeyRound size={14} />}
                  >
                    Enable
                  </Button>
                )}
              </div>

              {totpSetup && (
                <div className="grid grid-cols-1 gap-6 rounded-xl border border-white/10 bg-black/20 p-5 md:grid-cols-[auto_1fr]">
                  <div className="rounded-lg bg-white p-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={totpSetup.qr}
                      alt="Authenticator setup QR code"
                      className="h-[180px] w-[180px]"
                    />
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-slate-500">
                        Manual Secret
                      </div>
                      <div className="mt-2 break-all rounded border border-cyan-400/10 bg-cyan-400/5 px-3 py-2 font-mono text-[11px] text-cyan-200">
                        {totpSetup.secret}
                      </div>
                    </div>
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <input
                        type="text"
                        value={totpCode}
                        onChange={(e) => setTotpCode(e.target.value)}
                        placeholder="000000"
                        maxLength={6}
                        className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-center font-mono tracking-[0.35em] text-slate-100 outline-none transition-all focus:border-cyan-400/50"
                      />
                      <Button
                        size="sm"
                        onClick={confirmTotpSetup}
                        disabled={totpBusy || totpCode.length < 6}
                      >
                        Confirm
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {totpStatus?.enabled && (
                <div className="rounded-xl border border-white/10 bg-black/20 p-5">
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto_auto]">
                    <input
                      type="text"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value)}
                      placeholder={
                        totpDisableFactor === "recovery_code"
                          ? "Recovery code"
                          : "Authenticator code"
                      }
                      maxLength={totpDisableFactor === "recovery_code" ? 14 : 6}
                      className="min-w-0 rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-center font-mono tracking-[0.25em] text-slate-100 outline-none transition-all focus:border-cyan-400/50"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={regenerateRecoveryCodes}
                      disabled={
                        totpBusy ||
                        totpDisableFactor !== "totp" ||
                        totpCode.length < 6
                      }
                    >
                      Regenerate Codes
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-rose-500/30 text-rose-400 hover:bg-rose-500 hover:text-white"
                      onClick={disableTotp}
                      disabled={
                        totpBusy ||
                        (totpDisableFactor === "recovery_code"
                          ? totpCode.replace(/[-\s]/g, "").length < 8
                          : totpCode.length < 6)
                      }
                    >
                      Disable
                    </Button>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setTotpCode("");
                      setTotpDisableFactor(
                        totpDisableFactor === "totp" ? "recovery_code" : "totp",
                      );
                    }}
                    className="mt-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500 transition-colors hover:text-cyan-300"
                  >
                    {totpDisableFactor === "totp"
                      ? "Use recovery code to disable"
                      : "Use authenticator code to disable"}
                  </button>
                </div>
              )}

              {recoveryCodes.length > 0 && (
                <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-5">
                  <div className="mb-4 text-[10px] uppercase tracking-widest text-amber-300">
                    Save These Recovery Codes Now
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {recoveryCodes.map((code) => (
                      <div
                        key={code}
                        className="rounded border border-white/10 bg-black/30 px-3 py-2 font-mono text-xs tracking-widest text-slate-100"
                      >
                        {code}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {(totpMessage || totpError) && (
                <div
                  className={`rounded-lg border px-4 py-3 text-xs ${
                    totpError
                      ? "border-rose-500/20 bg-rose-500/10 text-rose-300"
                      : "border-cyan-400/20 bg-cyan-400/10 text-cyan-200"
                  }`}
                >
                  {totpError || totpMessage}
                </div>
              )}
            </div>
          </div>

          {/* Danger Zone */}
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 overflow-hidden">
            <div className="border-b border-rose-500/10 px-5 py-3 flex items-center gap-2">
              <ShieldAlert size={14} className="text-rose-500" />
              <p className="text-[10px] font-medium uppercase tracking-widest text-rose-500">
                Danger Zone
              </p>
            </div>
            <div className="p-8">
              <p className="text-xs text-slate-500 mb-6 max-w-2xl">
                Account deletion is an irreversible operation that
                transactionally purges all associated graph data, memories, and
                access keys from the system.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="border-rose-500/30 text-rose-500 hover:bg-rose-500 hover:text-white"
                onClick={() => setDeleteConfirmStep(1)}
              >
                Delete Account
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Account Deletion Modal (Unchanged logical flow) */}
      {deleteConfirmStep > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="max-w-md w-full bg-slate-900 border border-white/10 rounded-2xl p-8 shadow-2xl">
            {deleteConfirmStep === 1 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h3 className="text-xl font-bold text-white">
                    Confirm Account Deletion
                  </h3>
                  <p className="mt-4 text-slate-400 text-sm leading-relaxed">
                    This will permanently and transactionally delete all records
                    associated with your identity including
                    <span className="text-white font-semibold">
                      {" "}
                      graphs, nodes, events, and API keys
                    </span>
                    . This action is irreversible.
                  </p>
                </div>
                <div className="flex gap-4 pt-2">
                  <button
                    onClick={() => setDeleteConfirmStep(2)}
                    className="flex-1 py-3 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold uppercase tracking-widest transition-all"
                  >
                    Continue
                  </button>
                  <button
                    onClick={() => setDeleteConfirmStep(0)}
                    className="flex-1 py-3 rounded-lg border border-white/10 hover:bg-white/5 text-slate-400 text-xs font-bold uppercase tracking-widest transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {deleteConfirmStep === 2 && (
              <div className="space-y-6">
                <div className="text-center">
                  <h3 className="text-xl font-bold text-white">
                    Intent Verification
                  </h3>
                  <p className="mt-4 text-slate-400 text-sm">
                    To authorize the hard purge, please type
                    <span className="text-white font-mono font-black uppercase block mt-2 text-lg tracking-[0.3em]">
                      DELETE
                    </span>
                  </p>
                </div>
                <div className="space-y-4">
                  <input
                    type="text"
                    value={deleteInput}
                    onChange={(e) => {
                      setDeleteInput(e.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="Type DELETE"
                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-center font-mono text-lg tracking-widest focus:outline-none focus:border-rose-500/50 transition-all font-bold"
                    autoFocus
                  />
                  {error && (
                    <div className="text-rose-500 text-[10px] text-center font-bold uppercase tracking-widest">
                      {error}
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-3 pt-2">
                  <button
                    disabled={
                      deleteInput.toLowerCase() !== "delete" || isDeleting
                    }
                    onClick={handleDeleteAccount}
                    className="w-full py-4 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-30 font-bold text-xs uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 shadow-lg shadow-rose-600/20"
                  >
                    {isDeleting ? (
                      <>
                        <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Executing Purge
                      </>
                    ) : (
                      "Confirm & Purge Identity"
                    )}
                  </button>
                  <button
                    disabled={isDeleting}
                    onClick={() => {
                      setDeleteConfirmStep(0);
                      setDeleteInput("");
                    }}
                    className="text-slate-500 hover:text-slate-300 text-[10px] font-bold uppercase tracking-widest transition-colors py-2"
                  >
                    Abort Operation
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
