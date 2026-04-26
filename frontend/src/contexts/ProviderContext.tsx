"use client";

/**
 * Provider Context
 *
 * Manages the state of LLM providers: loading, creating, selecting, and managing models.
 * Stores all providers in localStorage via the providers.ts library.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import {
  Provider,
  loadProviders,
  saveProviders,
  addProvider as addProviderLib,
  removeProvider as removeProviderLib,
  setActiveProvider as setActiveProviderLib,
  setActiveModel as setActiveModelLib,
  updateProviderModels,
  normalizeBaseUrl,
} from "@/lib/providers";

interface ProviderContextType {
  providers: Provider[];
  activeProvider: Provider | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  addProvider: (
    name: string,
    type: "local" | "openai" | "custom",
    baseUrl: string,
    apiKey?: string,
    models?: string[],
    activeModel?: string,
  ) => Promise<string | null>; // Returns provider ID on success, null on error
  removeProvider: (id: string) => void;
  setActiveProvider: (id: string) => void;
  setActiveModel: (providerId: string, model: string) => void;
  discoverModels: (providerId: string) => Promise<boolean>; // Returns success
  refreshAllProvidersStatus: () => Promise<void>;
}

const ProviderContext = createContext<ProviderContextType | undefined>(
  undefined,
);

export function ProviderProvider({ children }: { children: React.ReactNode }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [activeProvider, setActiveProviderState] = useState<Provider | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial load from localStorage
  useEffect(() => {
    const loaded = loadProviders();
    setProviders(loaded);
    const active = loaded.find((p) => p.isActive) || null;
    setActiveProviderState(active);
    setIsLoading(false);
  }, []);

  const addProvider = useCallback(
    async (
      name: string,
      type: "local" | "openai" | "custom",
      baseUrl: string,
      apiKey?: string,
      models?: string[],
      activeModel?: string,
    ): Promise<string | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const normalized = normalizeBaseUrl(baseUrl);

        // Create provider — use pre-discovered models if provided, else fetch
        let resolvedModels = models ?? [];
        let resolvedActiveModel = activeModel ?? "";

        if (resolvedModels.length === 0) {
          // Fallback: discover models now
          const res = await fetch("/api/provider/discover", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ baseUrl: normalized, apiKey }),
          });
          if (res.ok) {
            const data = await res.json();
            resolvedModels = data.models ?? [];
            resolvedActiveModel = resolvedModels[0] ?? "";
          }
        }

        const newProvider: Omit<Provider, "id"> = {
          name,
          type,
          baseUrl: normalized,
          apiKey,
          models: resolvedModels,
          activeModel: resolvedActiveModel,
          isActive: providers.length === 0,
          status: resolvedModels.length > 0 ? "online" : "untested",
        };

        const provider = addProviderLib(newProvider);

        // Reload from localStorage to get updated state
        const updated = loadProviders();
        setProviders(updated);
        const active = updated.find((p) => p.isActive) || null;
        setActiveProviderState(active);

        return provider.id;
      } catch (e: any) {
        setError(e.message || "Failed to add provider");
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [providers.length],
  );

  const removeProvider = useCallback((id: string) => {
    try {
      removeProviderLib(id);
      const updated = loadProviders();
      setProviders(updated);
      const active = updated.find((p) => p.isActive) || null;
      setActiveProviderState(active);
    } catch (e: any) {
      setError(e.message || "Failed to remove provider");
    }
  }, []);

  const setActiveProvider = useCallback((id: string) => {
    try {
      setActiveProviderLib(id);
      const updated = loadProviders();
      setProviders(updated);
      const active = updated.find((p) => p.isActive) || null;
      setActiveProviderState(active);
    } catch (e: any) {
      setError(e.message || "Failed to set active provider");
    }
  }, []);

  const setActiveModel = useCallback((providerId: string, model: string) => {
    try {
      setActiveModelLib(providerId, model);
      const updated = loadProviders();
      setProviders(updated);
      const active = updated.find((p) => p.isActive) || null;
      setActiveProviderState(active);
    } catch (e: any) {
      setError(e.message || "Failed to set active model");
    }
  }, []);

  const discoverModels = useCallback(
    async (providerId: string): Promise<boolean> => {
      try {
        const provider = providers.find((p) => p.id === providerId);
        if (!provider) {
          setError("Provider not found");
          return false;
        }

        const res = await fetch("/api/provider/discover", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            baseUrl: provider.baseUrl,
            apiKey: provider.apiKey,
          }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          setError(errData.message || `Discovery failed (${res.status})`);
          return false;
        }

        const { models } = await res.json();

        // Update provider with discovered models
        updateProviderModels(providerId, models);

        // Reload from localStorage
        const updated = loadProviders();
        setProviders(updated);
        const active = updated.find((p) => p.isActive) || null;
        setActiveProviderState(active);

        return true;
      } catch (e: any) {
        setError(e.message || "Failed to discover models");
        return false;
      }
    },
    [providers],
  );

  const refreshAllProvidersStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const results = await Promise.all(
      providers.map((p) => discoverModels(p.id)),
    );

    const anyFailed = results.some((r) => !r);
    if (anyFailed) {
      setError("Some providers could not be reached");
    }

    setIsLoading(false);
  }, [providers, discoverModels]);

  return (
    <ProviderContext.Provider
      value={{
        providers,
        activeProvider,
        isLoading,
        error,
        addProvider,
        removeProvider,
        setActiveProvider,
        setActiveModel,
        discoverModels,
        refreshAllProvidersStatus,
      }}
    >
      {children}
    </ProviderContext.Provider>
  );
}

export function useProviders(): ProviderContextType {
  const context = useContext(ProviderContext);
  if (!context) {
    throw new Error("useProviders must be used within a ProviderProvider");
  }
  return context;
}
