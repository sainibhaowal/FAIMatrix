/**
 * FAIM-Native Embedding Discovery Endpoint
 *
 * POST /api/embedding-provider/native-discover
 * Lists auto-discovered local embedding models from the FAIM-native backend
 * (downloaded into faim_native/models/embeddings/).
 *
 * Response: { models: string[] }
 */

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND = (
  process.env.FAIM_BACKEND_URL ||
  process.env.NEXT_PUBLIC_FAIM_API_BASE ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export async function POST(): Promise<Response> {
  try {
    const upstream = await fetch(`${BACKEND}/api/v1/embedding-providers`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!upstream.ok) {
      return Response.json({ models: [] }, { status: 200 });
    }
    const data = await upstream.json().catch(() => ({}));
    const items = Array.isArray(data?.items) ? data.items : [];
    const models: string[] = [];
    for (const item of items) {
      const id = item?.id as string | undefined;
      if (typeof id === "string") models.push(id);
      const model = item?.model as string | undefined;
      if (typeof model === "string" && model && !models.includes(model)) {
        models.push(model);
      }
    }
    const deduped = Array.from(new Set(models)).filter((m) => m.includes("bge") || m.includes("e5"));
    const localModels = deduped.length > 0 ? deduped : Array.from(new Set(models));
    return Response.json({ models: localModels }, { status: 200 });
  } catch {
    return Response.json({ models: [] }, { status: 200 });
  }
}