"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  User,
  Mail,
  Save,
  Globe,
  Trash2,
  AlertTriangle,
  Loader2,
  Lock,
  CheckCircle,
  XCircle,
  Calendar,
  Key,
  Send,
  Eye,
  EyeOff,
  Sparkles,
  X,
} from "lucide-react";
import { getSession, signOut } from "next-auth/react";

// Beautiful avatar collection using DiceBear API
const AVATARS = [
  { id: "avatar_01", style: "adventurer", seed: "Felix", bg: "b6e3f4" },
  { id: "avatar_02", style: "adventurer", seed: "Aneka", bg: "c0aede" },
  { id: "avatar_03", style: "adventurer", seed: "Leo", bg: "d1fae5" },
  { id: "avatar_04", style: "adventurer", seed: "Mia", bg: "fde68a" },
  { id: "avatar_05", style: "adventurer-neutral", seed: "Alex", bg: "fecaca" },
  { id: "avatar_06", style: "adventurer-neutral", seed: "Sam", bg: "bfdbfe" },
  { id: "avatar_07", style: "avataaars", seed: "Charlie", bg: "c7d2fe" },
  { id: "avatar_08", style: "avataaars", seed: "Jordan", bg: "fbcfe8" },
  { id: "avatar_09", style: "big-ears", seed: "Riley", bg: "d9f99d" },
  { id: "avatar_10", style: "big-ears", seed: "Casey", bg: "fed7aa" },
  { id: "avatar_11", style: "bottts", seed: "Robot1", bg: "0ea5e9" },
  { id: "avatar_12", style: "bottts", seed: "Robot2", bg: "8b5cf6" },
  { id: "avatar_13", style: "fun-emoji", seed: "Happy", bg: "fbbf24" },
  { id: "avatar_14", style: "fun-emoji", seed: "Cool", bg: "34d399" },
  { id: "avatar_15", style: "lorelei", seed: "Luna", bg: "f9a8d4" },
  { id: "avatar_16", style: "lorelei", seed: "Nova", bg: "a5b4fc" },
  { id: "avatar_17", style: "micah", seed: "Kai", bg: "86efac" },
  { id: "avatar_18", style: "micah", seed: "Sage", bg: "fca5a5" },
  { id: "avatar_19", style: "notionists", seed: "Pro", bg: "e5e7eb" },
  { id: "avatar_20", style: "notionists", seed: "Dev", bg: "fef3c7" },
  { id: "avatar_21", style: "open-peeps", seed: "Tech", bg: "cffafe" },
  { id: "avatar_22", style: "open-peeps", seed: "Art", bg: "fce7f3" },
  { id: "avatar_23", style: "personas", seed: "Zen", bg: "ddd6fe" },
  { id: "avatar_24", style: "personas", seed: "Max", bg: "ccfbf1" },
];

function getAvatarUrl(avatarId: string): string {
  const avatar = AVATARS.find((a) => a.id === avatarId) || AVATARS[0];
  return `https://api.dicebear.com/7.x/${avatar.style}/svg?seed=${avatar.seed}&backgroundColor=${avatar.bg}&size=128`;
}

export default function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // Profile data
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    graph_id: "",
    user_id: "",
    avatar_id: "avatar_01",
    email_verified: false,
    created_at: "",
  });

  // Avatar picker modal
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [selectedAvatar, setSelectedAvatar] = useState("avatar_01");
  const [savingAvatar, setSavingAvatar] = useState(false);

  // Password change state
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  const [passwordData, setPasswordData] = useState({
    current: "",
    new: "",
    confirm: "",
  });
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Email verification state
  const [sendingVerification, setSendingVerification] = useState(false);
  const [verificationMessage, setVerificationMessage] = useState("");

  // Delete account state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  // For portal rendering (client-side only)
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => setIsMounted(true), []);

  const fetchProfile = async () => {
    setLoading(true);
    setError("");
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const res = await fetch("/api/v1/me", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Failed to load profile");

      const data = await res.json();
      setFormData({
        name: data.name || "",
        email: data.email || "",
        graph_id: data.graph_id || "",
        user_id: data.user_id || data.id || "",
        avatar_id: data.avatar_id || "avatar_01",
        email_verified: data.email_verified || false,
        created_at: data.created_at || "",
      });
      setSelectedAvatar(data.avatar_id || "avatar_01");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");

    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const res = await fetch("/api/v1/me", {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: formData.name,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update profile");

      setMessage("Profile updated successfully");
      fetchProfile();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAvatar = async () => {
    setSavingAvatar(true);
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const res = await fetch("/api/v1/me", {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ avatar_id: selectedAvatar }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update avatar");

      setFormData({ ...formData, avatar_id: selectedAvatar });
      setShowAvatarPicker(false);
      setMessage("Avatar updated!");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSavingAvatar(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangingPassword(true);
    setPasswordError("");
    setPasswordSuccess("");

    if (passwordData.new !== passwordData.confirm) {
      setPasswordError("New passwords do not match");
      setChangingPassword(false);
      return;
    }

    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const res = await fetch("/api/v1/me/password", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: passwordData.current,
          new_password: passwordData.new,
          confirm_password: passwordData.confirm,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to change password");

      setPasswordSuccess("Password changed successfully!");
      setPasswordData({ current: "", new: "", confirm: "" });
      setShowPasswordSection(false);
    } catch (e: any) {
      setPasswordError(e.message);
    } finally {
      setChangingPassword(false);
    }
  };

  const handleResendVerification = async () => {
    setSendingVerification(true);
    setVerificationMessage("");

    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const res = await fetch("/api/v1/me/resend-verification", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send verification");

      setVerificationMessage("Verification email sent! Check your inbox.");
    } catch (e: any) {
      setVerificationMessage(`Error: ${e.message}`);
    } finally {
      setSendingVerification(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText !== "DELETE") {
      setDeleteError("Please type DELETE to confirm");
      return;
    }

    if (!deletePassword) {
      setDeleteError("Please enter your password");
      return;
    }

    setDeleting(true);
    setDeleteError("");

    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const res = await fetch("/api/v1/me", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password: deletePassword }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to delete account");

      await signOut({ callbackUrl: "/auth/login?deleted=true" });
    } catch (e: any) {
      setDeleteError(e.message);
      setDeleting(false);
    }
  };

  const formatDate = (isoString: string) => {
    if (!isoString) return "Unknown";
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  if (loading)
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <Loader2 className="animate-spin" size={16} />
        Loading profile...
      </div>
    );

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <header className="flex items-center gap-4">
        {/* Avatar with edit button */}
        <div className="relative group cursor-pointer" onClick={() => setShowAvatarPicker(true)}>
          <img
            src={getAvatarUrl(formData.avatar_id)}
            alt="Avatar"
            className="w-20 h-20 rounded-full border-2 border-cyan-500/30 transition-transform group-hover:scale-105"
          />
          <div className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Sparkles size={20} className="text-white" />
          </div>
          {formData.email_verified && (
            <div className="absolute -bottom-1 -right-1 bg-emerald-500 rounded-full p-0.5">
              <CheckCircle size={14} className="text-white" />
            </div>
          )}
        </div>
        <div>
          <h1 className="text-lg font-semibold text-slate-100">My Profile</h1>
          <p className="text-xs text-slate-400">
            Click avatar to change • Manage your account
          </p>
        </div>
      </header>

      {error && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-200 text-xs">
          {error}
        </div>
      )}

      {message && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-xs">
          {message}
        </div>
      )}

      {passwordSuccess && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-xs">
          {passwordSuccess}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Personal Info Card */}
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

          {/* Email Verification Status */}
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
                onClick={handleResendVerification}
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

          {/* Account Created Date */}
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Calendar size={14} />
            <span>Member since {formatDate(formData.created_at)}</span>
          </div>
        </section>

        {/* Universe Card */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Globe size={14} className="text-purple-400" /> Your Universe
          </h2>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold text-slate-500">Universe ID</label>
              <input
                type="text"
                readOnly
                value={formData.graph_id}
                className="w-full bg-slate-950/30 border border-slate-800/50 rounded-xl py-2 px-3 text-xs text-slate-400 font-mono cursor-not-allowed"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] uppercase font-bold text-slate-500">User ID</label>
              <input
                type="text"
                readOnly
                value={formData.user_id}
                className="w-full bg-slate-950/30 border border-slate-800/50 rounded-xl py-2 px-3 text-xs text-slate-500 font-mono cursor-not-allowed"
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save size={16} />
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </div>
      </form>

      {/* Security Section */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
          <Key size={14} className="text-cyan-400" /> Security
        </h2>

        {!showPasswordSection ? (
          <button
            type="button"
            onClick={() => setShowPasswordSection(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-700 bg-slate-800/50 hover:bg-slate-800 text-slate-300 text-xs font-medium transition-colors"
          >
            <Lock size={14} />
            Change Password
          </button>
        ) : (
          <form onSubmit={handleChangePassword} className="space-y-4">
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
              <button
                type="button"
                onClick={() => {
                  setShowPasswordSection(false);
                  setPasswordData({ current: "", new: "", confirm: "" });
                  setPasswordError("");
                }}
                className="px-4 py-2 rounded-xl border border-slate-700 bg-slate-800/50 hover:bg-slate-800 text-slate-300 text-xs font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={changingPassword}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold transition-all disabled:opacity-50"
              >
                {changingPassword ? <Loader2 size={14} className="animate-spin" /> : <Lock size={14} />}
                {changingPassword ? "Changing..." : "Update Password"}
              </button>
            </div>
          </form>
        )}
      </section>

      {/* Danger Zone */}
      <section className="rounded-2xl border border-red-900/30 bg-red-950/10 p-5 space-y-4">
        <h2 className="text-xs font-semibold text-red-400 uppercase tracking-wider flex items-center gap-2">
          <AlertTriangle size={14} /> Danger Zone
        </h2>

        <p className="text-xs text-slate-400">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>

        <button
          type="button"
          onClick={() => setShowDeleteModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 text-red-300 text-xs font-medium transition-all"
        >
          <Trash2 size={14} />
          Delete My Account
        </button>
      </section>

      {/* Avatar Picker Modal */}
      {isMounted && showAvatarPicker && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-cyan-500/30 rounded-2xl p-6 max-w-2xl w-full mx-4 space-y-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 text-cyan-400">
                <Sparkles size={24} />
                <h3 className="text-lg font-bold text-slate-100">Choose Your Avatar</h3>
              </div>
              <button
                onClick={() => setShowAvatarPicker(false)}
                className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            <div className="grid grid-cols-4 sm:grid-cols-6 gap-3">
              {AVATARS.map((avatar) => (
                <button
                  key={avatar.id}
                  onClick={() => setSelectedAvatar(avatar.id)}
                  className={`relative p-1 rounded-xl transition-all ${
                    selectedAvatar === avatar.id
                      ? "ring-2 ring-cyan-400 bg-cyan-500/20 scale-105"
                      : "hover:bg-slate-800 hover:scale-105"
                  }`}
                >
                  <img
                    src={getAvatarUrl(avatar.id)}
                    alt={avatar.id}
                    className="w-full aspect-square rounded-lg"
                  />
                  {selectedAvatar === avatar.id && (
                    <div className="absolute -top-1 -right-1 bg-cyan-500 rounded-full p-0.5">
                      <CheckCircle size={12} className="text-white" />
                    </div>
                  )}
                </button>
              ))}
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowAvatarPicker(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveAvatar}
                disabled={savingAvatar || selectedAvatar === formData.avatar_id}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-700 disabled:text-slate-500 text-slate-950 text-sm font-bold transition-all disabled:cursor-not-allowed"
              >
                {savingAvatar ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    Apply Avatar
                  </>
                )}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Delete Confirmation Modal */}
      {isMounted && showDeleteModal && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-red-500/30 rounded-2xl p-6 max-w-md w-full mx-4 space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle size={24} />
              <h3 className="text-lg font-bold">Delete Account</h3>
            </div>

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
              <button
                type="button"
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeletePassword("");
                  setDeleteConfirmText("");
                  setDeleteError("");
                }}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-all"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={deleting || deleteConfirmText !== "DELETE" || !deletePassword}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 disabled:bg-red-900/50 disabled:text-red-300/50 text-white text-sm font-bold transition-all disabled:cursor-not-allowed"
              >
                {deleting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    Delete Forever
                  </>
                )}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
