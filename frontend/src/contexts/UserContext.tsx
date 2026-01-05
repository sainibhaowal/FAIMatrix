"use client";

/**
 * FAIM User Context - Provides authenticated user's IDs to components
 *
 * NEW FILE - Safe wrapper that provides projectId and graphId from session.
 * Components use this instead of hardcoded values for multi-tenant isolation.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { useSession } from "next-auth/react";

interface UserContextType {
  userId: string | null;
  email: string | null;
  name: string | null;
  projectId: string | null;
  graphId: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const defaultContext: UserContextType = {
  userId: null,
  email: null,
  name: null,
  projectId: null,
  graphId: null,
  isLoading: true,
  isAuthenticated: false,
};

const UserContext = createContext<UserContextType>(defaultContext);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const [userInfo, setUserInfo] = useState<UserContextType>(defaultContext);

  useEffect(() => {
    if (status === "loading") {
      setUserInfo((prev) => ({ ...prev, isLoading: true }));
      return;
    }

    if (status === "authenticated" && session) {
      let graphId = (session as any).graphId || null;
      let projectId = (session as any).projectId || null;

      // Initial state from session
      setUserInfo({
        userId: session.user?.id || null,
        email: session.user?.email || null,
        name: session.user?.name || null,
        projectId: projectId,
        graphId: graphId,
        isLoading: false,
        isAuthenticated: true,
      });

      // SYNC FRESH DATA: JWT might be stale (e.g. after DB wipe), so fetch real ID from DB
      fetch("/api/v1/me")
        .then((res) => {
          if (res.ok) return res.json();
          throw new Error("Sync failed");
        })
        .then((data) => {
          if (data.graph_id && data.graph_id !== graphId) {
            console.log(
              "[UserContext] Auto-healing stale Graph ID:",
              data.graph_id,
            );
            // Update localStorage
            try {
              window.localStorage.setItem(
                "faim.universe_graph_id",
                data.graph_id,
              );
              window.localStorage.setItem(
                "faim_universe_graph_id",
                data.graph_id,
              );
              window.localStorage.setItem("faim_user_id", data.user_id || "");
            } catch (e) {
              /* ignore */
            }

            // Update Context State
            setUserInfo((prev) => ({
              ...prev,
              graphId: data.graph_id,
              projectId: data.project_id || prev.projectId,
            }));
          } else if (graphId) {
            // Ensure storage is set even if matching (for first load)
            try {
              window.localStorage.setItem("faim.universe_graph_id", graphId);
              window.localStorage.setItem("faim_universe_graph_id", graphId);
            } catch (e) {}
          }
        })
        .catch((err) => console.warn("[UserContext] User sync skipped:", err));
    } else {
      // Not authenticated - landing page or logged out
      setUserInfo({
        ...defaultContext,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  }, [session, status]);

  return (
    <UserContext.Provider value={userInfo}>{children}</UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}

// Hook for components that need the IDs with warnings
export function useUserIds() {
  const { projectId, graphId, isLoading, isAuthenticated } = useUser();

  // Warn in dev if using without auth
  useEffect(() => {
    if (!isLoading && !isAuthenticated && (projectId || graphId)) {
      console.warn(
        "[FAIM] Using dev mode IDs. In production, users should be authenticated.",
      );
    }
  }, [isLoading, isAuthenticated, projectId, graphId]);

  return { projectId, graphId, isLoading };
}
