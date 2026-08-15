import { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function backendBase(): string {
  const apiHost = process.env.API_HOST;
  if (apiHost) return `http://${apiHost}`.replace(/\/+$/, "");

  const b = process.env.FAIM_BACKEND_URL || process.env.NEXT_PUBLIC_FAIM_API_BASE;
  if (b) return b.replace(/\/+$/, "");

  return "http://127.0.0.1:8000";
}

async function resolveAuth(req: NextRequest): Promise<{
  xUser: string;
  xKey: string;
  auth: string;
}> {
  const xUser = req.headers.get("x-faim-user") || req.headers.get("x-user-id") || "";
  const xKey = req.headers.get("x-faim-key") || "";
  const auth = req.headers.get("authorization") || "";

  // If the browser did not attach a Bearer token, read one from the session
  // cookie so the backend's JWTAuthMiddleware accepts the request.
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

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { xUser, xKey, auth } = await resolveAuth(req);

  try {
    const upstream = await fetch(`${backendBase()}/api/v1/reranker/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Tenant-Id": req.headers.get("x-tenant-id") || "default",
        "X-FAIM-USER": xUser || "default",
        ...(xKey ? { "X-FAIM-KEY": xKey } : {}),
        ...(auth ? { Authorization: auth } : {}),
      },
      body: JSON.stringify({
        query: body.query || undefined,
        candidates: body.candidates || undefined,
      }),
      cache: "no-store",
    });
    const data = await upstream.json().catch(() => ({}));
    // Surface the true success/offline status to the page even if the backend
    // returns a non-200 (e.g. 401 auth rejection) so we don't mask the problem.
    return Response.json(
      { ...data, _status: upstream.status },
      { status: upstream.ok ? 200 : upstream.status },
    );
  } catch (e: any) {
    return Response.json(
      {
        success: false,
        message: `Reranker backend unreachable: ${e.message}`,
        model: "faim-reranker-v2",
      },
      { status: 200 },
    );
  }
}
