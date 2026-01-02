// frontend/src/app/api/v1/stream/route.ts
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function backendBase(): string {
  // Server-only env vars: API_HOST (Docker), FAIM_BACKEND_URL, or NEXT_PUBLIC_FAIM_API_BASE
  const apiHost = process.env.API_HOST;
  if (apiHost) return `http://${apiHost}`.replace(/\/+$/, "");
  
  const b = process.env.FAIM_BACKEND_URL || process.env.NEXT_PUBLIC_FAIM_API_BASE;
  if (b) return b.replace(/\/+$/, "");
  
  return "http://127.0.0.1:8000";
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);

  // IMPORTANT: graph_id is OPTIONAL. Backend can derive universe from X-FAIM-USER.
  const graphId = url.searchParams.get("graph_id");

  const upstream = new URL(`${backendBase()}/api/v1/stream`);
  if (graphId) upstream.searchParams.set("graph_id", graphId);

  const xUser = req.headers.get("x-faim-user") || req.headers.get("x-user-id") || "";
  const xKey = req.headers.get("x-faim-key") || "";
  const auth = req.headers.get("authorization") || "";

  const upstreamResp = await fetch(upstream.toString(), {
    headers: {
      Accept: "text/event-stream",
      ...(xUser ? { "X-FAIM-USER": xUser } : {}),
      ...(xKey ? { "X-FAIM-KEY": xKey } : {}),
      ...(auth ? { Authorization: auth } : {}),
    },
    cache: "no-store",
  });

  if (!upstreamResp.ok || !upstreamResp.body) {
    const txt = await upstreamResp.text().catch(() => "");
    return new Response(txt || "Upstream stream failed", {
      status: upstreamResp.status || 502,
    });
  }

  // Stream passthrough
  const { readable, writable } = new TransformStream();
  upstreamResp.body.pipeTo(writable).catch(() => {});

  return new Response(readable, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
