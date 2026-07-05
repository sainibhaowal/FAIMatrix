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

/**
 * Best-effort detector for providers/models that advertise native reasoning.
 *
 * FAIM Cortex thinking does not depend on this; Cortex reasoning is always on.
 * This helper is only for UI copy/status because every provider exposes
 * reasoning controls and streamed thinking tokens differently.
 */
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
