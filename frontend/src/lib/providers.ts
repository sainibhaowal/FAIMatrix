/**
 * Provider Management Library
 *
 * Handles CRUD operations for LLM providers (local, OpenAI, custom endpoints)
 * with localStorage persistence and URL normalization.
 */

export type ProviderType = "local" | "openai" | "custom";
export type ProviderStatus = "untested" | "online" | "offline" | "error";

export interface Provider {
  id: string;
  name: string;
  type: ProviderType;
  baseUrl: string; // normalized: no trailing slash, has /v1
  apiKey?: string;
  models: string[];
  activeModel: string;
  isActive: boolean;
  status: ProviderStatus;
  lastChecked?: number; // timestamp
}

const LS_KEY = "faim.providers";

/**
 * Normalize a provider base URL
 * - Strips trailing slashes
 * - Adds /v1 if missing
 * Examples:
 *   "http://localhost:1234" → "http://localhost:1234/v1"
 *   "http://localhost:1234/" → "http://localhost:1234/v1"
 *   "http://localhost:1234/v1" → "http://localhost:1234/v1"
 */
export function normalizeBaseUrl(url: string): string {
  let normalized = url.trim().replace(/\/$/, "");
  if (!normalized.endsWith("/v1")) {
    normalized = normalized + "/v1";
  }
  return normalized;
}

/**
 * Load all providers from localStorage
 */
export function loadProviders(): Provider[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    console.error("Failed to load providers from localStorage");
    return [];
  }
}

/**
 * Save providers to localStorage
 */
export function saveProviders(providers: Provider[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(providers));
  } catch (e) {
    console.error("Failed to save providers to localStorage", e);
  }
}

/**
 * Add a new provider
 */
export function addProvider(provider: Omit<Provider, "id">): Provider {
  const newProvider: Provider = {
    ...provider,
    id: crypto.randomUUID(),
  };
  const providers = loadProviders();

  // If this is the first provider, make it active
  if (providers.length === 0) {
    newProvider.isActive = true;
  } else {
    newProvider.isActive = false;
  }

  providers.push(newProvider);
  saveProviders(providers);
  return newProvider;
}

/**
 * Remove a provider by ID
 */
export function removeProvider(id: string): void {
  const providers = loadProviders().filter((p) => p.id !== id);

  // If the removed provider was active, activate the first one
  if (providers.length > 0 && !providers.some((p) => p.isActive)) {
    providers[0].isActive = true;
  }

  saveProviders(providers);
}

/**
 * Update a provider (merge with existing)
 */
export function updateProvider(
  id: string,
  updates: Partial<Provider>,
): Provider | null {
  const providers = loadProviders();
  const index = providers.findIndex((p) => p.id === id);

  if (index === -1) return null;

  providers[index] = { ...providers[index], ...updates };
  saveProviders(providers);
  return providers[index];
}

/**
 * Set a provider as active (deactivate others)
 */
export function setActiveProvider(id: string): void {
  const providers = loadProviders();
  providers.forEach((p) => {
    p.isActive = p.id === id;
  });
  saveProviders(providers);
}

/**
 * Get the active provider
 */
export function getActiveProvider(): Provider | null {
  const providers = loadProviders();
  return providers.find((p) => p.isActive) || null;
}

/**
 * Set the active model for a provider
 */
export function setActiveModel(providerId: string, model: string): void {
  const providers = loadProviders();
  const provider = providers.find((p) => p.id === providerId);
  if (provider && provider.models.includes(model)) {
    provider.activeModel = model;
    saveProviders(providers);
  }
}

/**
 * Update models for a provider (e.g., after discovery)
 */
export function updateProviderModels(
  providerId: string,
  models: string[],
): void {
  const provider = updateProvider(providerId, {
    models,
    activeModel: models[0] || "",
    status: models.length > 0 ? "online" : "offline",
    lastChecked: Date.now(),
  });

  // If activeModel is not in the new list, pick the first
  if (provider && !models.includes(provider.activeModel)) {
    setActiveModel(providerId, models[0] || "");
  }
}
