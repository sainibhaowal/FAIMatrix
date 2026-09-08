import { normalizeBaseUrl } from "@/lib/embeddingProviders";
import { readJsonSafely } from "@/lib/safeFetch";

type DiscoverSuccess = {
  models?: unknown;
  dimension?: number;
};

type DiscoverError = {
  message?: string;
};

function extractModels(payload: DiscoverSuccess | unknown): { models: string[]; dimension?: number } {
  if (!payload || typeof payload !== "object") return { models: [] };
  const data = payload as DiscoverSuccess;
  const models = data.models;
  const modelList = Array.isArray(models)
    ? models.map((m) => String(m)).filter(Boolean)
    : [];
  return { models: modelList, dimension: data.dimension };
}

export async function discoverEmbeddingModels(
  baseUrl: string,
  apiKey?: string,
): Promise<{ models: string[]; dimension?: number }> {
  const res = await fetch("/api/embedding-provider/discover", {
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
  const { models, dimension } = extractModels(data);
  if (!models.length) {
    throw new Error("No models found from provider");
  }

  return { models, dimension };
}

export async function testEmbeddingProvider(
  provider: { baseUrl: string; apiKey?: string; model?: string; dimension?: number },
): Promise<boolean> {
  try {
    const res = await fetch("/api/embedding-provider/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseUrl: normalizeBaseUrl(provider.baseUrl),
        apiKey: provider.apiKey,
        model: provider.model,
        dimension: provider.dimension,
        testText: "FAIM embedding test",
      }),
    });

    if (!res.ok) {
      return false;
    }

    const data = await res.json();
    return data.success === true;
  } catch {
    return false;
  }
}