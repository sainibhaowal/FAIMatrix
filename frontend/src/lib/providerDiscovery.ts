import { normalizeBaseUrl } from "@/lib/providers";
import { readJsonSafely } from "@/lib/safeFetch";

type DiscoverSuccess = {
  models?: unknown;
};

type DiscoverError = {
  message?: string;
};

function extractModels(payload: DiscoverSuccess | unknown): string[] {
  if (!payload || typeof payload !== "object") return [];
  const models = (payload as DiscoverSuccess).models;
  return Array.isArray(models)
    ? models.map((m) => String(m)).filter(Boolean)
    : [];
}

export async function discoverProviderModels(
  baseUrl: string,
  apiKey?: string,
): Promise<{ models: string[] }> {
  const res = await fetch("/api/provider/discover", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      baseUrl: normalizeBaseUrl(baseUrl),
      apiKey,
    }),
  });

  if (!res.ok) {
    const errData = (await readJsonSafely<DiscoverError>(res)) ?? {};
    throw new Error(errData.message || `Discovery failed (${res.status})`);
  }

  const data = (await readJsonSafely<DiscoverSuccess>(res)) ?? {};
  const models = extractModels(data);
  if (!models.length) {
    throw new Error("No models found from provider");
  }

  return { models };
}
