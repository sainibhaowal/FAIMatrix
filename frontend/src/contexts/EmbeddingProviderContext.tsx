"use client";

/**
 * Embedding Provider Context
 *
 * Manages the state of embedding providers: loading, creating, selecting, and managing models.
 * Stores all providers in localStorage via the embeddingProviders.ts library.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import {
  EmbeddingProvider,
  loadEmbeddingProviders,
  saveEmbeddingProviders,
  addEmbeddingProvider as addEmbeddingProviderLib,
  removeEmbeddingProvider as removeEmbeddingProviderLib,
  setActiveEmbeddingProvider as setActiveEmbeddingProviderLib,
  normalizeBaseUrl,
} from "@/lib/embeddingProviders";
import { testEmbeddingProvider, discoverEmbeddingModels } from "@/lib/embeddingProviderDiscovery";

interface EmbeddingProviderContextType {
  providers: EmbeddingProvider[];
  activeProvider: EmbeddingProvider | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  addEmbeddingProvider: (
    name: string,
    type: "local" | "openai" | "custom",
    baseUrl: string,
    apiKey?: string,
    model?: string,
    dimension?: number,
  ) => Promise<string | null>; // Returns provider ID on success, null on error
  removeEmbeddingProvider: (id: string) => void;
  setActiveEmbeddingProvider: (id: string) => void;
  testEmbeddingProvider: (providerId: string) => Promise<boolean>; // Returns success
  refreshAllProvidersStatus: () => Promise<void>;
}

const EmbeddingProviderContext = createContext<EmbeddingProviderContextType | undefined>(
  undefined,
);

export function EmbeddingProviderProvider({ children }: { children: React.ReactNode }) {
  const [providers, setProviders] = useState<EmbeddingProvider[]>([]);
  const [activeProvider, setActiveProviderState] = useState<EmbeddingProvider | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initial load from localStorage
  useEffect(() => {
    const loaded = loadEmbeddingProviders();
    setProviders(loaded);
    const active = loaded.find((p) => p.isActive) || null;
    setActiveProviderState(active);
    setIsLoading(false);
  }, []);

  const addEmbeddingProvider = useCallback(
    async (
      name: string,
      type: "local" | "openai" | "custom",
      baseUrl: string,
      apiKey?: string,
      model?: string,
      dimension?: number,
    ): Promise<string | null> => {
      setIsLoading(true);
      setError(null);

      try {
        // Create provider
        const newProvider: Omit<EmbeddingProvider, "id"> = {
          name,
          type,
          baseUrl: normalizeBaseUrl(baseUrl),
          apiKey,
          model,
          dimension,
          isActive: providers.length === 0,
          status: "untested",
        };

        const provider = addEmbeddingProviderLib(newProvider);

        // Reload from localStorage to get updated state
        const updated = loadEmbeddingProviders();
        setProviders(updated);
        const active = updated.find((p) => p.isActive) || null;
        setActiveProviderState(active);

        return provider.id;
      } catch (e: any) {
        setError(e.message || "Failed to add embedding provider");
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [providers.length],
  );

  const removeEmbeddingProvider = useCallback((id: string) => {
    try {
      removeEmbeddingProviderLib(id);
      const updated = loadEmbeddingProviders();
      setProviders(updated);
      const active = updated.find((p) => p.isActive) || null;
      setActiveProviderState(active);
    } catch (e: any) {
      setError(e.message || "Failed to remove embedding provider");
    }
  }, []);

  const setActiveEmbeddingProvider = useCallback((id: string) => {
    try {
      setActiveEmbeddingProviderLib(id);
      const updated = loadEmbeddingProviders();
      setProviders(updated);
      const active = updated.find((p) => p.isActive) || null;
      setActiveProviderState(active);
    } catch (e: any) {
      setError(e.message || "Failed to set active embedding provider");
    }
  }, []);

  const testEmbeddingProviderFn = useCallback(
    async (providerId: string): Promise<boolean> => {
      try {
        const provider = providers.find((p) => p.id === providerId);
        if (!provider) {
          setError("Provider not found");
          return false;
        }

        const success = await testEmbeddingProvider(provider);

        // Reload from localStorage to get updated status
        const updated = loadEmbeddingProviders();
        setProviders(updated);
        const active = updated.find((p) => p.isActive) || null;
        setActiveProviderState(active);

        return success;
      } catch (e: any) {
        setError(e.message || "Failed to test embedding provider");
        return false;
      }
    },
    [providers],
  );

  const refreshAllProvidersStatus = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const results = await Promise.all(
      providers.map((p) => testEmbeddingProviderFn(p.id)),
    );

    const anyFailed = results.some((r) => !r);
    if (anyFailed) {
      setError("Some providers could not be reached");
    }

    setIsLoading(false);
  }, [providers, testEmbeddingProviderFn]);

  return (
    <EmbeddingProviderContext.Provider
      value={{
        providers,
        activeProvider,
        isLoading,
        error,
        addEmbeddingProvider,
        removeEmbeddingProvider,
        setActiveEmbeddingProvider,
        testEmbeddingProvider: testEmbeddingProviderFn,
        refreshAllProvidersStatus,
      }}
    >
      {children}
    </EmbeddingProviderContext.Provider>
  );
}

export function useEmbeddingProviders(): EmbeddingProviderContextType {
  const context = useContext(EmbeddingProviderContext);
  if (!context) {
    throw new Error("useEmbeddingProviders must be used within an EmbeddingProviderProvider");
  }
  return context;
}