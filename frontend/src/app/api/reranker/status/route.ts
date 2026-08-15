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

export async function GET(req: NextRequest) {
  const { xUser, xKey, auth } = await resolveAuth(req);

  try {
    const upstream = await fetch(`${backendBase()}/api/v1/reranker/status`, {
      headers: {
        Accept: "application/json",
        ...(xUser ? { "X-FAIM-USER": xUser } : {}),
        ...(xKey ? { "X-FAIM-KEY": xKey } : {}),
        ...(auth ? { Authorization: auth } : {}),
      },
      cache: "no-store",
    });
    const data = await upstream.json().catch(() => ({}));
    return Response.json({ ...data, _status: upstream.status }, { status: upstream.ok ? 200 : upstream.status });
  } catch (e: any) {
    return Response.json(
      {
        available: false,
        name: "faim-reranker-v2",
        message: `Backend unreachable: ${e.message}`,
      },
      { status: 200 },
    );
  }
}
