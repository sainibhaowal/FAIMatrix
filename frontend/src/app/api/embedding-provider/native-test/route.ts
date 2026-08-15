/**
 * FAIM-Native Embedding Test Endpoint (local models)
 *
 * POST /api/embedding-provider/native-test
 * Tests a pre-registered FAIM-native local embedding provider by encoding a
 * test text through the backend REST API (/api/v1/embedding-providers/{id}/test).
 *
 * FAIM-Native does NOT expose an OpenAI-compatible /embeddings HTTP endpoint,
 * so local models must be tested through this native REST route instead.
 *
 * Request:  { model?: string }
 * Response: { success: boolean, message: string, dimension?: number, latency_ms?: number }
 */

import { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const rawHost =
  process.env.API_HOST ||
  process.env.FAIM_BACKEND_URL ||
  process.env.NEXT_PUBLIC_FAIM_API_BASE ||
  "http://127.0.0.1:8000";

const BACKEND = (
  rawHost.startsWith("http://") || rawHost.startsWith("https://")
    ? rawHost
    : `http://${rawHost}`
).replace(/\/+$/, "");

interface NativeProviderItem {
  id?: string;
  name?: string;
  is_active?: boolean;
  status?: string;
}

async function authHeaders(
  req: NextRequest,
): Promise<{ xUser: string; xKey: string; auth: string }> {
  const xUser = req.headers.get("x-faim-user") || req.headers.get("x-user-id") || "";
  const xKey = req.headers.get("x-faim-key") || "";
  const auth = req.headers.get("authorization") || "";

  // If the browser did not attach a Bearer token, try to read one from the
  // session cookie so the backend's JWTAuthMiddleware accepts the request.
  if (!auth) {
    try {
      const token = await getToken({
        req,
        secret: process.env.NEXTAUTH_SECRET,
      });
      const access = (token as { accessToken?: string } | null)?.accessToken;
      if (access) return { xUser, xKey, auth: `Bearer ${access}` };
    } catch {}
  }

  return { xUser, xKey, auth };
}

async function listNativeProviders(
  ctx: { xUser: string; xKey: string; auth: string },
): Promise<{ items: NativeProviderItem[]; status: number; raw: unknown; activeBackend: string }> {
  const hosts = Array.from(new Set([BACKEND, "http://faim-api:8000", "http://api:8000", "http://127.0.0.1:8000", "http://localhost:8000"]));
  let lastErrStatus = 0;
  let lastRaw: unknown = {};

  for (const host of hosts) {
    try {
      const res = await fetch(`${host}/api/v1/embedding-providers`, {
        headers: {
          Accept: "application/json",
          "X-Tenant-Id": "default",
          "X-Api-Key": ctx.xKey || "default",
          ...(ctx.xUser ? { "X-FAIM-USER": ctx.xUser, "X-User-Id": ctx.xUser } : {}),
          ...(ctx.xKey ? { "X-FAIM-KEY": ctx.xKey } : {}),
          ...(ctx.auth ? { Authorization: ctx.auth } : {}),
        },
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        const items = Array.isArray(data?.items) ? (data.items as NativeProviderItem[]) : [];
        return { items, status: res.status, raw: data, activeBackend: host };
      }
      lastErrStatus = res.status;
      lastRaw = await res.json().catch(() => ({}));
    } catch {}
  }
  return { items: [], status: lastErrStatus, raw: lastRaw, activeBackend: BACKEND };
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const requestedModel: string | undefined =
    typeof body?.model === "string" ? body.model : undefined;

  const ctx = await authHeaders(req);

  try {
    const { items: providers, status: listStatus, raw, activeBackend } = await listNativeProviders(ctx);

    if (listStatus === 401 || listStatus === 403) {
      return Response.json(
        {
          success: false,
          message: "Auth required to reach FAIM-native embedding core.",
          _status: listStatus,
        },
        { status: 200 },
      );
    }
    if (listStatus >= 500 || providers.length === 0) {
      const reason =
        listStatus === 0
          ? "FAIM-native embedding core unreachable (backend not running?)."
          : `FAIM-native embedding core returned ${listStatus}.`;
      return Response.json(
        { success: false, message: reason, _status: listStatus, _raw: raw },
        { status: 200 },
      );
    }

    let provider: NativeProviderItem | undefined;
    if (requestedModel) {
      const norm = requestedModel.replace(/\//g, "-").toLowerCase();
      provider = providers.find((p) => {
        const pId = (p.id || "").toLowerCase();
        return pId === norm || pId === `local-${norm}` || (requestedModel.toLowerCase().includes("bge-m3") && pId === "bge-m3-local");
      });
      if (!provider) {
        provider = providers.find((p) => {
          const pId = (p.id || "").toLowerCase();
          const pName = (p.name || "").toLowerCase();
          return pId.includes(norm) || pName === norm || pName.includes(norm);
        });
      }
    }
    if (!provider) {
      provider = providers.find((p) => p.is_active) || providers.find((p) => p.status === "online") || providers[0];
    }

    if (!provider?.id) {
      return Response.json(
        {
          success: false,
          message: "No FAIM-native embedding provider registered.",
          _providers: providers.map((p) => p.id),
        },
        { status: 200 },
      );
    }

    const testRes = await fetch(
      `${activeBackend}/api/v1/embedding-providers/${encodeURIComponent(provider.id)}/test`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-Tenant-Id": "default",
          "X-Api-Key": ctx.xKey || "default",
          ...(ctx.xUser ? { "X-FAIM-USER": ctx.xUser, "X-User-Id": ctx.xUser } : {}),
          ...(ctx.xKey ? { "X-FAIM-KEY": ctx.xKey } : {}),
          ...(ctx.auth ? { Authorization: ctx.auth } : {}),
        },
        body: JSON.stringify({ provider_id: provider.id, test_text: "FAIM embedding test" }),
        cache: "no-store",
      },
    );

    const data = await testRes.json().catch(() => ({}));
    if (testRes.ok && data?.success) {
      return Response.json(
        {
          success: true,
          message:
            data.message ||
            `✓ Ping verified: ${provider.id} generated a test vector!`,
          dimension: data.dimension,
          latency_ms: data.latency_ms,
          provider_id: provider.id,
        },
        { status: 200 },
      );
    }
    if (testRes.status === 401 || testRes.status === 403) {
      return Response.json(
        { success: false, message: "Auth required to reach FAIM-native embedding core." },
        { status: 200 },
      );
    }
    return Response.json(
      {
        success: false,
        message: data?.message || `Ping failed for ${provider.id}`,
        _debug: { requestedModel, selectedProviderId: provider.id, activeBackend, testResStatus: testRes.status, data },
      },
      { status: 200 },
    );
  } catch (e: any) {
    return Response.json(
      { success: false, message: `FAIM-native embedding core unreachable: ${e.message}` },
      { status: 200 },
    );
  }
}
