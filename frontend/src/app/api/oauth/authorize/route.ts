import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

function getBackendBaseUrl(): string {
  const apiHost = (process.env.API_HOST || "").trim();
  if (apiHost) {
    return apiHost.startsWith("http://") || apiHost.startsWith("https://")
      ? apiHost.replace(/\/+$/, "")
      : `http://${apiHost}`.replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8000";
}

export async function POST(req: NextRequest) {
  const token = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET,
  });

  const accessToken =
    typeof token?.accessToken === "string" ? token.accessToken : "";
  if (!token || !accessToken) {
    return NextResponse.json(
      { error: "Authentication required" },
      { status: 401 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = (await req.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const res = await fetch(`${getBackendBaseUrl()}/api/v1/oauth/code`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      client_id: body.client_id,
      redirect_uri: body.redirect_uri,
      code_challenge: body.code_challenge,
      code_challenge_method: body.code_challenge_method || "S256",
      scope: body.scope,
      state: body.state,
    }),
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      {
        error:
          data.detail || data.error || "Failed to issue authorization code",
      },
      { status: res.status },
    );
  }

  return NextResponse.json(data);
}
