"use client";

"use client";

import React from "react";
import { User, Mail, Send, Loader2, CheckCircle, XCircle, Calendar, Save } from "lucide-react";
import { Button } from "@/components/ui";

interface ProfileSettingsProps {
  formData: {
    name: string;
    email: string;
    email_verified: boolean;
    created_at: string;
  };
  setFormData: (data: any) => void;
  onSave: (e: React.FormEvent) => Promise<void>;
  saving: boolean;
  onResendVerification: () => Promise<void>;
  sendingVerification: boolean;
  verificationMessage: string;
  formatDate: (date: string) => string;
}

export function ProfileSettings({
  formData,
  setFormData,
  onSave,
  saving,
  onResendVerification,
  sendingVerification,
  verificationMessage,
  formatDate,
}: ProfileSettingsProps) {
  return (
    <form onSubmit={onSave} className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Personal Information
        </h2>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <label className="text-[10px] uppercase font-bold text-slate-500">Full Name</label>
            <div className="relative">
              <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-2 pl-9 pr-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50 transition-colors"
                placeholder="Your Name"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] uppercase font-bold text-slate-500">Email Address</label>
            <div className="relative">
              <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="email"
                value={formData.email}
                readOnly
                className="w-full bg-slate-950/30 border border-slate-800/50 rounded-xl py-2 pl-9 pr-3 text-xs text-slate-400 cursor-not-allowed"
              />
            </div>
            <p className="text-[10px] text-slate-600">Email cannot be changed</p>
          </div>
        </div>

        <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/30 border border-slate-800/50">
          <div className="flex items-center gap-2">
            {formData.email_verified ? (
              <CheckCircle size={16} className="text-emerald-400" />
            ) : (
              <XCircle size={16} className="text-amber-400" />
            )}
            <span className="text-xs text-slate-300">
              Email {formData.email_verified ? "Verified" : "Not Verified"}
            </span>
          </div>
          {!formData.email_verified && (
            <button
              type="button"
              onClick={onResendVerification}
              disabled={sendingVerification}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-medium transition-colors disabled:opacity-50"
            >
              {sendingVerification ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Send size={12} />
              )}
              Verify Email
            </button>
          )}
        </div>
        {verificationMessage && (
          <p className="text-xs text-slate-400">{verificationMessage}</p>
        )}

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Calendar size={14} />
          <span>Member since {formatDate(formData.created_at)}</span>
        </div>
      </section>

      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={saving}
          variant="primary"
          className="px-6"
        >
          <Save size={16} className="mr-2" />
          {saving ? "Saving..." : "Save Profile"}
        </Button>
      </div>
    </form>
  );
}
