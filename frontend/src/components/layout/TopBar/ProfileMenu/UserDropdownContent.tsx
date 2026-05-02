"use client";

import React from "react";
import { useSession, signOut } from "next-auth/react";

export function UserDropdownContent({
  goAdmin,
  onClose,
}: {
  goAdmin: (tab?: string) => void;
  onClose: () => void;
}) {
  const { data: session } = useSession();

  return (
    <div className="p-3">
      {/* Header with user info */}
      <div className="mb-3 flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-2">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 text-sm font-semibold text-white">
          {session?.user?.name?.[0] ?? "U"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[13px] font-medium text-slate-200">
            {session?.user?.name || "User"}
          </div>
          <div className="truncate text-[11px] text-slate-500">
            {session?.user?.email || "user@example.com"}
          </div>
        </div>
      </div>

      {/* Menu Options */}
      <div className="space-y-1">
        <button
          onClick={() => {
            onClose();
            goAdmin("account");
          }}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[12px] text-slate-300 hover:bg-white/5 hover:text-white"
        >
          Account settings
        </button>
        <button
          onClick={() => {
            onClose();
            goAdmin("billing");
          }}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[12px] text-slate-300 hover:bg-white/5 hover:text-white"
          >
          Billing & Usage
        </button>
        {Boolean((session as { isAdmin?: boolean } | null)?.isAdmin) && (
          <>
            <button
              onClick={() => {
                onClose();
                goAdmin("admin");
              }}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[12px] text-cyan-300 hover:bg-cyan-500/10 hover:text-cyan-200"
            >
              Admin Control
            </button>
            <button
              onClick={() => {
                onClose();
                goAdmin("alerts");
              }}
              className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[12px] text-rose-300 hover:bg-rose-500/10 hover:text-rose-200"
            >
              Admin Alerts
            </button>
          </>
        )}
        <div className="my-1 h-px bg-white/10" />
        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-[12px] text-rose-300 hover:bg-rose-500/10"
        >
          Sign out
        </button>
      </div>

      <div className="mt-3 border-t border-white/5 pt-2 text-center text-[10px] text-slate-600">
        FAIMATRIX v0.1.0-beta
      </div>
    </div>
  );
}
