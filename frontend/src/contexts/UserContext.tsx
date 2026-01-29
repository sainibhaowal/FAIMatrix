"use client";

/**
 * FAIM User Context - Provides authenticated user's IDs to components
 *
 * NEW FILE - Safe wrapper that provides graphId from session.
 * Components use this instead of hardcoded values for multi-tenant isolation.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { useSession } from "next-auth/react";

interface UserContextType {
  userId: string | null;
  email: string | null;
  name: string | null;
  graphId: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const defaultContext: UserContextType = {
  userId: null,
  email: null,
  name: null,
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


      // Initial state from session
      setUserInfo({
        userId: session.user?.id || null,
        email: session.user?.email || null,
        name: session.user?.name || null,

        graphId: graphId,
        isLoading: false,
        isAuthenticated: true,
      });

      // SYNC FRESH DATA: JWT might be stale (e.g. after DB wipe), so fetch real ID from DB
      const accessToken = (session as any).accessToken;
      
      fetch("/api/v1/me", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
        .then(async (res) => {
          if (!res.ok) {
            throw new Error(`Sync failed with status: ${res.status}`);
          }
          const contentType = res.headers.get("content-type");
          if (!contentType || !contentType.includes("application/json")) {
            throw new Error("Received non-JSON response from server");
          }
          return res.json();
        })
        .then((data) => {
          if (data.graph_id && data.graph_id !== graphId) {
            // Auto-heal stale Graph ID silently
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
  const { graphId, isLoading, isAuthenticated } = useUser();

  // Warn in dev if using without auth
  useEffect(() => {
    if (!isLoading && !isAuthenticated && graphId) {
      console.warn(
        "[FAIM] Using dev mode IDs. In production, users should be authenticated.",
      );
    }
  }, [isLoading, isAuthenticated, graphId]);

  return { graphId, isLoading, isAuthenticated };
}
