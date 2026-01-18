"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Globe,
  Loader2,
  Sparkles,
  CheckCircle,
} from "lucide-react";
import { getSession, signOut } from "next-auth/react";

// Components
import { AvatarPicker, ProfileSettings, SecuritySettings } from "@/components";

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
  const [passwordData, setPasswordData] = useState({
    current: "",
    new: "",
    confirm: "",
  });
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");

  // Email verification state
  const [sendingVerification, setSendingVerification] = useState(false);
  const [verificationMessage, setVerificationMessage] = useState("");

  // Delete account state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const fetchProfile = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

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

  if (loading)
    return (
      <div className="flex items-center gap-2 text-slate-500">
        <Loader2 className="animate-spin" size={16} />
        Loading profile...
      </div>
    );

  const getAvatarUrl = (avatarId: string) => {
    return `https://api.dicebear.com/7.x/adventurer/svg?seed=${avatarId}&backgroundColor=b6e3f4&size=128`;
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <header className="flex items-center gap-4">
        {/* Avatar with edit button */}
        <div className="relative group cursor-pointer" onClick={() => setShowAvatarPicker(true)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
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

      <ProfileSettings
        formData={formData}
        setFormData={setFormData}
        onSave={handleSave}
        saving={saving}
        onResendVerification={handleResendVerification}
        sendingVerification={sendingVerification}
        verificationMessage={verificationMessage}
        formatDate={formatDate}
      />

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

      <SecuritySettings
        onPasswordChange={handleChangePassword}
        passwordData={passwordData}
        setPasswordData={setPasswordData}
        changingPassword={changingPassword}
        passwordError={passwordError}
        onDeleteAccount={handleDeleteAccount}
        deleting={deleting}
        deleteError={deleteError}
        showDeleteModal={showDeleteModal}
        setShowDeleteModal={setShowDeleteModal}
        deletePassword={deletePassword}
        setDeletePassword={setDeletePassword}
        deleteConfirmText={deleteConfirmText}
        setDeleteConfirmText={setDeleteConfirmText}
      />

      <AvatarPicker
        open={showAvatarPicker}
        onClose={() => setShowAvatarPicker(false)}
        selectedAvatar={selectedAvatar}
        onSelect={setSelectedAvatar}
        onSave={handleSaveAvatar}
        saving={savingAvatar}
        currentAvatarId={formData.avatar_id}
      />
    </div>
  );
}
