"use client";

import { create } from "zustand";
import type { StateCreator } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

/* ============================================================================
   Types
============================================================================ */

type Turn = { role: "system" | "user" | "assistant"; content: string };

export type SessionStatus = "active" | "archived" | "trashed";

export type Session = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: Turn[];
  usedNodes: any[]; // swap later to RtUsedNodeSummary[]
  status: SessionStatus;
};

/* ============================================================================
   Helpers
============================================================================ */

function makeSession(now: number, initialSystemText?: string): Session {
  return {
    id: `s_${now}`,
    title: "New Session",
    createdAt: now,
    updatedAt: now,
    turns: [
      {
        role: "system",
        content:
          initialSystemText ??
          "FAIM Neural Core initialized. Memory context active.",
      },
      {
        role: "assistant",
        content:
          "Hello. I’m ready. Ask anything — FAIM will show you which memories influenced the answer.",
      },
    ],
    usedNodes: [],
    status: "active",
  };
}

function setStatus(s: Session, status: SessionStatus): Session {
  return { ...s, status, updatedAt: Date.now() };
}

function pickFallbackActive(sessions: Session[]): string {
  const a = sessions.find((x) => x.status === "active");
  return a?.id ?? "";
}

/* ============================================================================
   Store
============================================================================ */

export type ChatState = {
  // persisted
  bootstrapped: boolean; // prevents "auto recreate" after user clears everything
  activeSessionId: string;
  sessions: Session[];

  // init
  ensureInitialized: () => void;

  // selectors (optional helpers)
  getActive: () => Session | null;

  // actions
  setActive: (id: string) => void;
  newSession: () => void;

  updateActive: (mut: (s: Session) => Session) => void;
  renameSession: (id: string, title: string) => void;

  archiveSession: (id: string) => void;
  trashSession: (id: string) => void;
  restoreSession: (id: string) => void;

  deleteForever: (id: string) => void;
  emptyTrash: () => void;

  // ✅ user-intent "wipe"
  clearAll: () => void;
};

const creator: StateCreator<ChatState, [], [], ChatState> = (set, get) => ({
  bootstrapped: false,
  activeSessionId: "",
  sessions: [],

  ensureInitialized: () => {
    const { sessions, activeSessionId, bootstrapped } = get();

    // If user already cleared everything intentionally, do NOT auto recreate
    if (bootstrapped && sessions.length === 0) return;

    // First ever boot (fresh storage): create 1 session
    if (sessions.length === 0 || !activeSessionId) {
      const now = Date.now();
      const s = makeSession(now);
      set({ sessions: [s], activeSessionId: s.id, bootstrapped: true });
      return;
    }

    // Also mark bootstrapped once we have something
    if (!bootstrapped) set({ bootstrapped: true });
  },

  getActive: () => {
    const { sessions, activeSessionId } = get();
    if (!sessions.length || !activeSessionId) return null;
    const s = sessions.find((x) => x.id === activeSessionId) ?? null;
    return s;
  },

  setActive: (id) => {
    const { sessions } = get();
    const s = sessions.find((x) => x.id === id);
    // don't allow selecting trashed as active chat
    if (!s || s.status !== "active") {
      set({ activeSessionId: pickFallbackActive(sessions) });
      return;
    }
    set({ activeSessionId: id });
  },

  newSession: () => {
    const now = Date.now();
    const s = makeSession(
      now,
      "New session created. Memory context will attach to this run.",
    );
    const prev = get().sessions;
    set({ sessions: [s, ...prev], activeSessionId: s.id, bootstrapped: true });
  },

  updateActive: (mut) => {
    const { sessions, activeSessionId } = get();
    if (!activeSessionId) return;
    const cur = sessions.find((x) => x.id === activeSessionId);
    if (!cur || cur.status !== "active") return;

    set({
      sessions: sessions.map((s) => (s.id === activeSessionId ? mut(s) : s)),
    });
  },

  renameSession: (id, title) => {
    const t = title.trim();
    if (!t) return;
    const { sessions } = get();
    set({
      sessions: sessions.map((s) =>
        s.id === id
          ? { ...s, title: t.slice(0, 60), updatedAt: Date.now() }
          : s,
      ),
    });
  },

  archiveSession: (id) => {
    const { sessions, activeSessionId } = get();
    const next = sessions.map((s) =>
      s.id === id ? setStatus(s, "archived") : s,
    );

    let nextActive = activeSessionId;
    if (id === activeSessionId) nextActive = pickFallbackActive(next);

    set({ sessions: next, activeSessionId: nextActive });
  },

  trashSession: (id) => {
    const { sessions, activeSessionId } = get();
    const next = sessions.map((s) =>
      s.id === id ? setStatus(s, "trashed") : s,
    );

    let nextActive = activeSessionId;
    if (id === activeSessionId) nextActive = pickFallbackActive(next);

    set({ sessions: next, activeSessionId: nextActive });
  },

  restoreSession: (id) => {
    const { sessions } = get();
    const next = sessions.map((s) =>
      s.id === id ? setStatus(s, "active") : s,
    );
    // if nothing active, restore becomes active candidate
    const nextActive = pickFallbackActive(next) || id;
    set({ sessions: next, activeSessionId: nextActive });
  },

  deleteForever: (id) => {
    const { sessions, activeSessionId } = get();
    const next = sessions.filter((s) => s.id !== id);

    let nextActive = activeSessionId;
    if (id === activeSessionId) nextActive = pickFallbackActive(next);

    set({ sessions: next, activeSessionId: nextActive });
  },

  emptyTrash: () => {
    const { sessions, activeSessionId } = get();
    const next = sessions.filter((s) => s.status !== "trashed");

    let nextActive = activeSessionId;
    if (nextActive && !next.find((x) => x.id === nextActive))
      nextActive = pickFallbackActive(next);

    set({ sessions: next, activeSessionId: nextActive });
  },

  clearAll: () => {
    // user intent: wipe everything and keep it empty (no auto reinit)
    set({ sessions: [], activeSessionId: "", bootstrapped: true });
  },
});

export const useChatStore = create<ChatState>()(
  persist(creator, {
    name: "faim_lab_chat_v1",
    storage: createJSONStorage(() => localStorage),
    version: 2,
    partialize: (s) => ({
      bootstrapped: s.bootstrapped,
      activeSessionId: s.activeSessionId,
      sessions: s.sessions,
    }),
  }),
);
