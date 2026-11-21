"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "next-auth/react";

function OAuthAuthorizeContent() {
  const searchParams = useSearchParams();
  const { data: session, status } = useSession();

  const clientId = searchParams.get("client_id") || "";
  const redirectUri = searchParams.get("redirect_uri") || "";
  const codeChallenge = searchParams.get("code_challenge") || "";
  const codeChallengeMethod =
    searchParams.get("code_challenge_method") || "S256";
  const scope = searchParams.get("scope") || "mcp:read mcp:write";
  const state = searchParams.get("state") || "";

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated" && typeof window !== "undefined") {
      const callbackUrl = window.location.pathname + window.location.search;
      window.location.href = `/auth/login?callbackUrl=${encodeURIComponent(callbackUrl)}`;
    }
  }, [status]);

  const missingParams = !clientId || !redirectUri || !codeChallenge;
  const scopes = scope.split(/\s+/).filter(Boolean);

  async function handleApprove() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/oauth/authorize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          redirect_uri: redirectUri,
          code_challenge: codeChallenge,
          code_challenge_method: codeChallengeMethod,
          scope,
          state,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Authorization failed");
        setSubmitting(false);
        return;
      }
      const target = new URL(redirectUri);
      target.searchParams.set("code", data.code);
      if (state) target.searchParams.set("state", state);
      window.location.href = target.toString();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
      setSubmitting(false);
    }
  }

  function handleDeny() {
    if (!redirectUri) return;
    const target = new URL(redirectUri);
    target.searchParams.set("error", "access_denied");
    if (state) target.searchParams.set("state", state);
    window.location.href = target.toString();
  }

  if (status === "loading" || status === "unauthenticated") {
    return (
      <div className="min-h-screen bg-[#070b14] text-slate-200 flex items-center justify-center p-6">
        <div className="text-sm text-slate-400">Checking FAIM session...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d1424] p-6 shadow-2xl space-y-5">
        <div className="space-y-1">
          <div className="text-xs font-mono uppercase tracking-wider text-cyan-400">
            FAIM MCP Authorization
          </div>
          <h1 className="text-xl font-semibold">Connect External AI Agent</h1>
          <p className="text-sm text-slate-400">
            An MCP client is requesting access to your FAIM memory graphs.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#080d19] p-4 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Account</span>
            <span className="font-mono text-slate-200 truncate">
              {session?.user?.email ||
                session?.user?.name ||
                "Authenticated User"}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Client ID</span>
            <span className="font-mono text-xs text-slate-300 truncate">
              {clientId || "missing"}
            </span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-400">Redirect</span>
            <span className="font-mono text-xs text-slate-300 truncate">
              {redirectUri || "missing"}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Requested Permissions
          </div>
          <div className="flex flex-wrap gap-2">
            {scopes.map((s) => (
              <span
                key={s}
                className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-xs font-mono text-cyan-300"
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {missingParams && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
            Missing required OAuth PKCE parameters (client_id, redirect_uri, or
            code_challenge).
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={handleDeny}
            disabled={submitting || !redirectUri}
            className="flex-1 rounded-xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800 disabled:opacity-50"
          >
            Deny
          </button>
          <button
            type="button"
            onClick={handleApprove}
            disabled={submitting || missingParams}
            className="flex-1 rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
          >
            {submitting ? "Authorizing..." : "Authorize FAIM"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function OAuthAuthorizePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#070b14] text-slate-400 flex items-center justify-center p-6 text-sm">
          Loading authorization...
        </div>
      }
    >
      <OAuthAuthorizeContent />
    </Suspense>
  );
}
