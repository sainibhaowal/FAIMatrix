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

/** Validate upstream URLs before the server-side provider proxy fetches them. */
export function isSafeProviderUrl(value: string): boolean {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    if (url.username || url.password) return false;
    const hostname = url.hostname.toLowerCase();
    return hostname !== "169.254.169.254" && hostname !== "metadata.google.internal";
  } catch {
    return false;
  }
}

const LS_KEY = "faim.providers";

function normalizeReasoningLabel(value: string): string {
  return value
    .toLowerCase()
    .replace(/[_/.-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const REASONING_MODEL_NAMES = new Set(
  [
    "Big Pickle",
    "Stealth",
    "Claude Fable 5",
    "Claude Mythos 5",
    "Claude Mythos Preview",
    "Claude Haiku 4.5",
    "Claude Opus 4.1",
    "Claude Opus 4.5",
    "Claude Opus 4.6",
    "Claude Opus 4.7",
    "Claude Opus 4.8",
    "Claude Sonnet 4",
    "Claude Sonnet 4.5",
    "Claude Sonnet 4.6",
    "Claude Sonnet 5",
    "GPT 5",
    "GPT 5 Codex",
    "GPT 5 Nano",
    "GPT 5.1",
    "GPT 5.1 Codex",
    "GPT 5.1 Codex Max",
    "GPT 5.1 Codex Mini",
    "GPT 5.2",
    "GPT 5.2 Codex",
    "GPT 5.3 Codex",
    "GPT 5.3 Codex Spark",
    "GPT 5.4",
    "GPT 5.4 Mini",
    "GPT 5.4 Nano",
    "GPT 5.4 Pro",
    "GPT 5.5",
    "GPT 5.5 Thinking",
    "GPT 5.5 Pro",
    "GPT 5.6",
    "GPT 5.6 Sol",
    "GPT 5.6 Terra",
    "GPT 5.6 Luna",
    "Gemini 3 Flash",
    "Gemini 3 Flash Preview",
    "Gemini 3.1 Pro",
    "Gemini 3.1 Flash-Lite",
    "Gemini 3.5 Flash",
    "Gemini 3.1 Flash",
    "DeepSeek V4 Flash",
    "DeepSeek V4 Flash Free",
    "DeepSeek V4 Pro",
    "deepseek-chat",
    "deepseek-reasoner",
    "GLM 5",
    "GLM 5.1",
    "GLM 5.2",
    "GLM 5 Turbo",
    "Kimi K2.5",
    "Kimi K2.6",
    "Kimi K2.7 Code",
    "Qwen3.5 Plus",
    "Qwen3.6 Plus",
    "Qwen3.7 Plus",
    "Qwen3.7 Max",
    "Grok Build 0.1",
    "Grok 4.3",
    "grok-4.20-0309-reasoning",
    "grok-4.20-0309-non-reasoning",
    "grok-4.20-multi-agent-0309",
    "MiniMax M2.5",
    "MiniMax M2.7",
    "MiniMax M3",
    "MiMo V2.5",
    "MiMo V2.5 Free",
    "Nemotron 3 Ultra",
    "Nemotron 3 Ultra Free",
    "Nemotron 3 Ultra 550B-A55B",
    "Nemotron 3 Super 120B",
    "Nemotron 3 Super 120B-A12B",
    "Nemotron 3 Nano Omni",
    "Nemotron 3 Nano 30B A3B NVFP4",
    "North Mini Code",
    "North Mini Code Free",
  ].map((name) => normalizeReasoningLabel(name)),
);

const REASONING_FAMILY_MARKERS = [
  "openai",
  "anthropic",
  "claude",
  "gpt-5",
  "o1",
  "o3",
  "o4",
  "gemini",
  "deepseek",
  "deepseek v4",
  "qwen",
  "qwq",
  "kimi",
  "glm",
  "grok",
  "minimax",
  "mimo",
  "nemotron",
  "north mini",
];

const REASONING_MODEL_MARKERS = [
  "reason",
  "thinking",
  "deepseek-r1",
  "deepseek r1",
  "deepseek-v4",
  "deepseek v4",
  "qwen3",
  "qwq",
  "o1",
  "o3",
  "o4",
  "gpt-5",
  "claude-3.7",
  "claude-4",
  "claude opus 4",
  "claude sonnet 4",
  "claude sonnet 5",
  "claude haiku 4.5",
  "claude fable 5",
  "gemini-2.5",
  "gemini 3",
  "glm 5",
  "kimi k2",
  "grok build",
  "minimax m",
  "mimo v2.5",
  "nemotron 3 ultra",
  "north mini code",
  "r1",
];

export interface ReasoningCapability {
  supported: boolean;
  confidence: "exact" | "family" | "heuristic" | "unknown";
  matched?: string;
}

export function providerModelLooksReasoningCapable(
  provider: Pick<Provider, "type" | "name" | "activeModel"> | null | undefined,
): boolean {
  return providerReasoningCapability(provider).supported;
}

export function providerReasoningCapability(
  provider: Pick<Provider, "type" | "name" | "activeModel"> | null | undefined,
): ReasoningCapability {
  if (!provider) {
    return { supported: false, confidence: "unknown" };
  }
  const haystack = normalizeReasoningLabel(
    `${provider.type} ${provider.name} ${provider.activeModel}`,
  );
  const exactModel = normalizeReasoningLabel(provider.activeModel);
  const exactName = normalizeReasoningLabel(provider.name);

  if (REASONING_MODEL_NAMES.has(exactModel)) {
    return { supported: true, confidence: "exact", matched: provider.activeModel };
  }
  if (REASONING_MODEL_NAMES.has(exactName)) {
    return { supported: true, confidence: "exact", matched: provider.name };
  }

  const familyMatch = REASONING_FAMILY_MARKERS.find((marker) =>
    haystack.includes(marker),
  );
  if (familyMatch) {
    return {
      supported: true,
      confidence: "family",
      matched: familyMatch,
    };
  }

  const heuristicMatch = REASONING_MODEL_MARKERS.find((marker) =>
    haystack.includes(marker),
  );
  if (heuristicMatch) {
    return {
      supported: true,
      confidence: "heuristic",
      matched: heuristicMatch,
    };
  }

  return { supported: false, confidence: "unknown" };
}

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
export function loadProviders(): Provider[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const list: Provider[] = JSON.parse(raw);

    // Auto-deduplicate duplicate records by name/baseUrl
    const deduplicated: Provider[] = [];
    const seen = new Set<string>();

    for (const p of list) {
      const key = `${p.name.toLowerCase().trim()}_${normalizeBaseUrl(p.baseUrl)}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduplicated.push(p);
      } else {
        // If duplicate was active, make sure the retained item keeps active status
        if (p.isActive) {
          const existing = deduplicated.find((x) => `${x.name.toLowerCase().trim()}_${normalizeBaseUrl(x.baseUrl)}` === key);
          if (existing) existing.isActive = true;
        }
      }
    }

    if (deduplicated.length !== list.length) {
      saveProviders(deduplicated);
    }
    return deduplicated;
  } catch {
    console.error("Failed to load providers from localStorage");
    return [];
  }
}

export function saveProviders(providers: Provider[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(providers));
  } catch (e) {
    console.error("Failed to save providers to localStorage", e);
  }
}

/**
 * Add or update provider cleanly without creating duplicates
 */
export function addProvider(provider: Omit<Provider, "id">): Provider {
  const normUrl = normalizeBaseUrl(provider.baseUrl);
  const providers = loadProviders();

  // Find existing provider by name or normalized base URL
  const existingIndex = providers.findIndex(
    (p) =>
      p.name.toLowerCase().trim() === provider.name.toLowerCase().trim() ||
      normalizeBaseUrl(p.baseUrl) === normUrl
  );

  // Deactivate all others so only the target provider is active
  providers.forEach((p) => {
    p.isActive = false;
  });

  if (existingIndex >= 0) {
    // Update existing provider entry
    const existing = providers[existingIndex];
    const updatedProvider: Provider = {
      ...existing,
      ...provider,
      baseUrl: normUrl,
      isActive: true,
      id: existing.id,
    };
    providers[existingIndex] = updatedProvider;
    saveProviders(providers);
    return updatedProvider;
  } else {
    // Insert new provider entry
    const newProvider: Provider = {
      ...provider,
      baseUrl: normUrl,
      isActive: true,
      id: crypto.randomUUID(),
    };
    providers.push(newProvider);
    saveProviders(providers);
    return newProvider;
  }
}

export function removeProvider(id: string): void {
  const providers = loadProviders().filter((p) => p.id !== id);

  if (providers.length > 0 && !providers.some((p) => p.isActive)) {
    providers[0].isActive = true;
  }

  saveProviders(providers);
}

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

export function setActiveProvider(id: string): void {
  const providers = loadProviders();
  providers.forEach((p) => {
    p.isActive = p.id === id;
  });
  saveProviders(providers);
}

export function setActiveModel(providerId: string, model: string): void {
  const providers = loadProviders();
  const provider = providers.find((p) => p.id === providerId);

  if (provider) {
    provider.activeModel = model;
    saveProviders(providers);
  }
}

export function updateProviderModels(
  providerId: string,
  models: string[],
): void {
  const providers = loadProviders();
  const provider = providers.find((p) => p.id === providerId);

  if (provider) {
    provider.models = models;
    if (!models.includes(provider.activeModel)) {
      provider.activeModel = models[0] || "";
    }
    saveProviders(providers);
  }
}

export function updateProviderStatus(
  providerId: string,
  status: ProviderStatus,
): void {
  const providers = loadProviders();
  const provider = providers.find((p) => p.id === providerId);

  if (provider) {
    provider.status = status;
    provider.lastChecked = Date.now();
    saveProviders(providers);
  }
}

export function getActiveProvider(): Provider | null {
  const providers = loadProviders();
  return providers.find((p) => p.isActive) || null;
}
