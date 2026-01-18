"use client";

import React, { useState } from "react";
import { Lock, Key, Eye, EyeOff, Loader2, AlertTriangle, Trash2 } from "lucide-react";
import { Button, Modal } from "@/components/ui";

interface SecuritySettingsProps {
  onPasswordChange: (e: React.FormEvent) => Promise<void>;
  passwordData: any;
  setPasswordData: (data: any) => void;
  changingPassword: boolean;
  passwordError: string;
  onDeleteAccount: () => Promise<void>;
  deleting: boolean;
  deleteError: string;
  showDeleteModal: boolean;
  setShowDeleteModal: (show: boolean) => void;
  deletePassword: string;
  setDeletePassword: (pw: string) => void;
  deleteConfirmText: string;
  setDeleteConfirmText: (text: string) => void;
}

export function SecuritySettings({
  onPasswordChange,
  passwordData,
  setPasswordData,
  changingPassword,
  passwordError,
  onDeleteAccount,
  deleting,
  deleteError,
  showDeleteModal,
  setShowDeleteModal,
  deletePassword,
  setDeletePassword,
  deleteConfirmText,
  setDeleteConfirmText,
}: SecuritySettingsProps) {
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
          <Key size={14} className="text-cyan-400" /> Security
        </h2>

        {!showPasswordSection ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowPasswordSection(true)}
          >
            <Lock size={14} className="mr-2" />
            Change Password
          </Button>
        ) : (
          <form onSubmit={onPasswordChange} className="space-y-4">
            {passwordError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs">
                {passwordError}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold text-slate-500">Current Password</label>
              <div className="relative">
                <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  value={passwordData.current}
                  onChange={(e) => setPasswordData({ ...passwordData, current: e.target.value })}
                  className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-2 pl-9 pr-10 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showCurrentPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-500">New Password</label>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    value={passwordData.new}
                    onChange={(e) => setPasswordData({ ...passwordData, new: e.target.value })}
                    className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-2 px-3 pr-10 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                    placeholder="Min 8 chars, letter + number"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showNewPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] uppercase font-bold text-slate-500">Confirm New Password</label>
                <input
                  type="password"
                  value={passwordData.confirm}
                  onChange={(e) => setPasswordData({ ...passwordData, confirm: e.target.value })}
                  className="w-full bg-slate-950/50 border border-slate-800 rounded-xl py-2 px-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500/50"
                  required
                />
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowPasswordSection(false);
                  setPasswordData({ current: "", new: "", confirm: "" });
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={changingPassword}
              >
                {changingPassword ? <Loader2 size={14} className="animate-spin mr-2" /> : <Lock size={14} className="mr-2" />}
                {changingPassword ? "Changing..." : "Update Password"}
              </Button>
            </div>
          </form>
        )}
      </section>

      <section className="rounded-2xl border border-red-900/30 bg-red-950/10 p-5 space-y-4">
        <h2 className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-2">
          <AlertTriangle size={14} /> Danger Zone
        </h2>
        <p className="text-xs text-slate-400">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>
        <Button
          variant="danger"
          size="sm"
          onClick={() => setShowDeleteModal(true)}
        >
          <Trash2 size={14} className="mr-2" />
          Delete My Account
        </Button>
      </section>

      <Modal
        open={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title={
          <div className="flex items-center gap-3 text-red-400">
            <AlertTriangle size={24} />
            <span>Delete Account</span>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="space-y-3 text-sm text-slate-300">
            <p className="font-medium text-red-300">⚠️ This action is permanent and cannot be undone.</p>
            <p>Deleting your account will:</p>
            <ul className="list-disc list-inside space-y-1 text-slate-400">
              <li>Remove all your personal information</li>
              <li>Delete your entire Universe and all memories</li>
              <li>Remove all uploaded documents</li>
              <li>Revoke all API keys</li>
              <li>Erase all usage history</li>
            </ul>
          </div>

          {deleteError && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs">
              {deleteError}
            </div>
          )}

          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs text-slate-400">
                Type <span className="font-mono font-bold text-red-400">DELETE</span> to confirm
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value.toUpperCase())}
                className="w-full bg-slate-950/50 border border-slate-700 rounded-xl py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-red-500/50"
                placeholder="DELETE"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs text-slate-400 flex items-center gap-1">
                <Lock size={12} /> Enter your password to confirm
              </label>
              <input
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                className="w-full bg-slate-950/50 border border-slate-700 rounded-xl py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-red-500/50"
                placeholder="Your password"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <Button
              variant="ghost"
              className="flex-1"
              onClick={() => {
                setShowDeleteModal(false);
                setDeletePassword("");
                setDeleteConfirmText("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              className="flex-1"
              disabled={deleting || deleteConfirmText !== "DELETE" || !deletePassword}
              onClick={onDeleteAccount}
            >
              {deleting ? (
                <>
                  <Loader2 size={16} className="animate-spin mr-2" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 size={16} className="mr-2" />
                  Delete Forever
                </>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
