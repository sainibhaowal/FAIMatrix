import { getServerSession } from "next-auth/next";
import { NextRequest, NextResponse } from "next/server";
import { authOptions } from "@/lib/auth";

const BACKEND_URL = (
  process.env.API_HOST
    ? `http://${process.env.API_HOST}`
    : process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"
).replace(/\/+$/, "");

function adminProxyUrl(pathSegments: string[], requestUrl: URL): string {
  const backendPath = `/api/v1/admin/${pathSegments.join("/")}`.replace(
    /\/+$/,
    "",
  );
  const url = new URL(`${BACKEND_URL}${backendPath}`);
  requestUrl.searchParams.forEach((value, key) => {
    url.searchParams.append(key, value);
  });
  return url.toString();
}

async function handleProxy(
  request: NextRequest,
  params: { path?: string[] },
): Promise<NextResponse> {
  const session = await getServerSession(authOptions);
  if (!session?.isAdmin) {
    return NextResponse.json(
      { error: "Forbidden", message: "Admin access required." },
      { status: 403 },
    );
  }

  const accessToken = (session as { accessToken?: string }).accessToken;
  if (!accessToken) {
    return NextResponse.json(
      { error: "Unauthorized", message: "Missing admin session token." },
      { status: 401 },
    );
  }

  const pathSegments = params.path ?? [];
  const targetPath =
    pathSegments.length === 0 ? ["status"] : pathSegments.map((p) => String(p));
  const target = adminProxyUrl(targetPath, new URL(request.url));

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("accept", "application/json");
  headers.set("authorization", `Bearer ${accessToken}`);

  const adminKey = process.env.FAIM_ADMIN_KEY || "";
  if (!adminKey) {
    return NextResponse.json(
      { error: "Server misconfigured", message: "FAIM_ADMIN_KEY missing." },
      { status: 500 },
    );
  }
  headers.set("x-admin-key", adminKey);

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.text();
  }

  const upstream = await fetch(target, init);
  const body = await upstream.text();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") || "application/json; charset=utf-8",
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: { path?: string[] } },
) {
  return handleProxy(request, context.params);
}

export async function POST(
  request: NextRequest,
  context: { params: { path?: string[] } },
) {
  return handleProxy(request, context.params);
}

export async function PUT(
  request: NextRequest,
  context: { params: { path?: string[] } },
) {
  return handleProxy(request, context.params);
}

export async function DELETE(
  request: NextRequest,
  context: { params: { path?: string[] } },
) {
  return handleProxy(request, context.params);
}
