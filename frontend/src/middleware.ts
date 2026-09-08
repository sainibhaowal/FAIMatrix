import { withAuth } from "next-auth/middleware";
import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PLAYWRIGHT_BYPASS_SUB = "playwright-benchmark";
const PLAYWRIGHT_BYPASS_EMAIL = "playwright@faim.local";
const PLAYWRIGHT_BYPASS_NAME = "Playwright Benchmark";

const PUBLIC_API_PATHS = new Set([
  "/api/v1/health",
  "/api/v1/ready",
  "/api/v1/version",
  "/api/health",
  "/api/ready",
  "/api/version",
]);

function isApiCall(pathname: string): boolean {
  return (
    pathname.startsWith("/api/v1/") ||
    pathname.startsWith("/api/ops/") ||
    pathname.startsWith("/api/billing/")
    || pathname.startsWith("/api/provider/")
  );
}

function toBase64Url(value: string | Uint8Array | ArrayBuffer): string {
  const bytes =
    typeof value === "string"
      ? new TextEncoder().encode(value)
      : value instanceof Uint8Array
        ? value
        : new Uint8Array(value);

  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    for (let offset = 0; offset < chunk.length; offset += 1) {
      binary += String.fromCharCode(chunk[offset]);
    }
  }

  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

async function mintPlaywrightJwt(secret: string): Promise<string> {
  const issuedAt = Math.floor(Date.now() / 1000);
  const header = { alg: "HS256", typ: "JWT" };
  const payload = {
    sub: PLAYWRIGHT_BYPASS_SUB,
    userId: PLAYWRIGHT_BYPASS_SUB,
    email: PLAYWRIGHT_BYPASS_EMAIL,
    name: PLAYWRIGHT_BYPASS_NAME,
    iat: issuedAt,
    exp: issuedAt + 60 * 60 * 12,
  };

  const encodedHeader = toBase64Url(JSON.stringify(header));
  const encodedPayload = toBase64Url(JSON.stringify(payload));
  const signingInput = `${encodedHeader}.${encodedPayload}`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(signingInput),
  );

  return `${signingInput}.${toBase64Url(signature)}`;
}

// 1. Export withAuth to protect dashboard and API routes
export default withAuth(
  async function middleware(req) {
    if (PUBLIC_API_PATHS.has(req.nextUrl.pathname)) {
      return NextResponse.next();
    }

    // Test-only bypass for Playwright e2e runs.
    // For proxied FAIM API calls, inject a synthetic JWT so the backend's JWTAuthMiddleware
    // accepts the request without requiring X-Tenant-Id / X-Api-Key headers.
    if (process.env.PLAYWRIGHT_BYPASS_AUTH === "true") {
      if (isApiCall(req.nextUrl.pathname)) {
        const e2eJwt =
          process.env.PLAYWRIGHT_E2E_JWT ||
          (await mintPlaywrightJwt(process.env.NEXTAUTH_SECRET || ""));
        const requestHeaders = new Headers(req.headers);
        requestHeaders.set("Authorization", `Bearer ${e2eJwt}`);
        return NextResponse.next({ request: { headers: requestHeaders } });
      }
      return NextResponse.next();
    }

    const authHeader = req.headers.get("Authorization");

    let token = null;
    try {
      token = await getToken({
        req,
        secret: process.env.NEXTAUTH_SECRET,
      });
    } catch (error) {
      console.warn(
        `[Middleware] Failed to parse auth token for ${req.nextUrl.pathname}: ${
          error instanceof Error ? error.message : String(error)
        }`,
      );
    }

    // 1. If we ALREADY have an Authorization header (from UserContext fetch),
    // we don't need to block it or inject anything. Let the backend handle verification.
    if (authHeader?.startsWith("Bearer ")) {
      return NextResponse.next();
    }



    // 2. If it's a protected API route and we have NO token (cookie), then return 401 JSON
    if (
      !token &&
      (req.nextUrl.pathname.startsWith("/api/v1/auth/me") ||
          ((req.nextUrl.pathname.startsWith("/api/v1/") ||
            req.nextUrl.pathname.startsWith("/api/provider/")) &&
          !req.nextUrl.pathname.startsWith("/api/v1/auth/")))
    ) {
      return new NextResponse(
        JSON.stringify({
          error: "Unauthorized",
          message: "No valid session token found. Please log in again.",
        }),
        {
          status: 401,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    }

    // Intercept proxied API routes to inject Authorization header
    if (isApiCall(req.nextUrl.pathname) && token?.accessToken) {
      const requestHeaders = new Headers(req.headers);
      requestHeaders.set("Authorization", `Bearer ${token.accessToken}`);

      return NextResponse.next({
        request: {
          headers: requestHeaders,
        },
      });
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        if (process.env.PLAYWRIGHT_BYPASS_AUTH === "true") return true;

        if (req.nextUrl.pathname.startsWith("/api/")) return true;
        return !!token;
      },
    },
    pages: {
      signIn: "/auth/login",
    },
  },
);

// 2. Ensure it matches dashboard and protected API routes
export const config = {
  matcher: [
    "/dashboard",
    "/dashboard/:path*",
    "/api/v1/auth/me", // Specifically protect /me
    "/api/v1/((?!auth/).*)", // Protect all other v1 except auth endpoints
    "/api/ops/:path*",
    "/api/billing/:path*",
    "/api/provider/:path*",
  ],
};
