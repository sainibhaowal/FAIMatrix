/**
 * Embedding Provider Management Library
 *
 * Handles CRUD operations for embedding providers (local, OpenAI, custom endpoints)
 * with localStorage persistence and URL normalization.
 */

export type EmbeddingProviderType = "local" | "openai" | "custom";
export type EmbeddingProviderStatus = "untested" | "online" | "offline" | "error";

export interface EmbeddingProvider {
  id: string;
  name: string;
  type: EmbeddingProviderType;
  baseUrl: string; // normalized: no trailing slash, has /v1
  apiKey?: string;
  model?: string;
  dimension?: number;
  isActive: boolean;
  status: EmbeddingProviderStatus;
  lastChecked?: number; // timestamp
}

const LS_KEY = "faim.embeddingProviders";

export function normalizeBaseUrl(url: string): string {
  let normalized = url.trim().replace(/\/$/, "");
  if (!normalized.endsWith("/v1")) {
    normalized = normalized + "/v1";
  }
  return normalized;
}

/**
 * Load all providers from localStorage (with auto-deduplication by name/baseUrl)
 */
export function loadEmbeddingProviders(): EmbeddingProvider[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const list: EmbeddingProvider[] = JSON.parse(raw);

    const deduplicated: EmbeddingProvider[] = [];
    const seen = new Set<string>();

    for (const p of list) {
      const key = `${p.name.toLowerCase().trim()}_${normalizeBaseUrl(p.baseUrl)}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduplicated.push(p);
      } else {
        if (p.isActive) {
          const existing = deduplicated.find((x) => `${x.name.toLowerCase().trim()}_${normalizeBaseUrl(x.baseUrl)}` === key);
          if (existing) existing.isActive = true;
        }
      }
    }

    if (deduplicated.length !== list.length) {
      saveEmbeddingProviders(deduplicated);
    }
    return deduplicated;
  } catch {
    console.error("Failed to load embedding providers from localStorage");
    return [];
  }
}

export function saveEmbeddingProviders(providers: EmbeddingProvider[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(providers));
  } catch (e) {
    console.error("Failed to save embedding providers to localStorage", e);
  }
}

/**
 * Add or update embedding provider cleanly without creating duplicates
 */
export function addEmbeddingProvider(provider: Omit<EmbeddingProvider, "id">): EmbeddingProvider {
  const normUrl = normalizeBaseUrl(provider.baseUrl);
  const providers = loadEmbeddingProviders();

  const existingIndex = providers.findIndex(
    (p) =>
      p.name.toLowerCase().trim() === provider.name.toLowerCase().trim() ||
      normalizeBaseUrl(p.baseUrl) === normUrl
  );

  providers.forEach((p) => {
    p.isActive = false;
  });

  if (existingIndex >= 0) {
    const existing = providers[existingIndex];
    const updatedProvider: EmbeddingProvider = {
      ...existing,
      ...provider,
      baseUrl: normUrl,
      isActive: true,
      id: existing.id,
    };
    providers[existingIndex] = updatedProvider;
    saveEmbeddingProviders(providers);
    return updatedProvider;
  } else {
    const newProvider: EmbeddingProvider = {
      ...provider,
      baseUrl: normUrl,
      isActive: true,
      id: crypto.randomUUID(),
    };
    providers.push(newProvider);
    saveEmbeddingProviders(providers);
    return newProvider;
  }
}

export function removeEmbeddingProvider(id: string): void {
  const providers = loadEmbeddingProviders().filter((p) => p.id !== id);

  if (providers.length > 0 && !providers.some((p) => p.isActive)) {
    providers[0].isActive = true;
  }

  saveEmbeddingProviders(providers);
}

export function updateEmbeddingProvider(
  id: string,
  updates: Partial<EmbeddingProvider>,
): EmbeddingProvider | null {
  const providers = loadEmbeddingProviders();
  const index = providers.findIndex((p) => p.id === id);

  if (index === -1) return null;

  providers[index] = { ...providers[index], ...updates };
  saveEmbeddingProviders(providers);
  return providers[index];
}

export function setActiveEmbeddingProvider(id: string): void {
  const providers = loadEmbeddingProviders();
  providers.forEach((p) => {
    p.isActive = p.id === id;
  });
  saveEmbeddingProviders(providers);
}

export function getActiveEmbeddingProvider(): EmbeddingProvider | null {
  const providers = loadEmbeddingProviders();
  return providers.find((p) => p.isActive) || null;
}