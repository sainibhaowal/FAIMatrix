"use client";

import React, { useState } from "react";
import { Sparkles, X, CheckCircle, Loader2 } from "lucide-react";
import { Modal, Button } from "@/components/ui";

export const AVATARS = [
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

export function getAvatarUrl(avatarId: string): string {
  const avatar = AVATARS.find((a) => a.id === avatarId) || AVATARS[0];
  return `https://api.dicebear.com/7.x/${avatar.style}/svg?seed=${avatar.seed}&backgroundColor=${avatar.bg}&size=128`;
}

interface AvatarPickerProps {
  open: boolean;
  onClose: () => void;
  selectedAvatar: string;
  onSelect: (id: string) => void;
  onSave: () => Promise<void>;
  saving: boolean;
  currentAvatarId: string;
}

export function AvatarPicker({
  open,
  onClose,
  selectedAvatar,
  onSelect,
  onSave,
  saving,
  currentAvatarId,
}: AvatarPickerProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-3 text-cyan-400">
          <Sparkles size={24} />
          <span>Choose Your Avatar</span>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="grid grid-cols-4 sm:grid-cols-6 gap-3 max-h-[40vh] overflow-y-auto p-1">
          {AVATARS.map((avatar) => (
            <button
              key={avatar.id}
              onClick={() => onSelect(avatar.id)}
              className={`relative p-1 rounded-xl transition-all ${
                selectedAvatar === avatar.id
                  ? "ring-2 ring-cyan-400 bg-cyan-500/20 scale-105"
                  : "hover:bg-slate-800 hover:scale-105"
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
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
          <Button
            variant="ghost"
            onClick={onClose}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={onSave}
            disabled={saving || selectedAvatar === currentAvatarId}
            className="flex-1"
          >
            {saving ? (
              <>
                <Loader2 size={16} className="animate-spin mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Sparkles size={16} className="mr-2" />
                Apply Avatar
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
