import { withAuth } from "next-auth/middleware";
import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// 1. Export withAuth to protect dashboard and API routes
export default withAuth(
  async function middleware(req) {
    // Test-only bypass for Playwright e2e runs.
    if (process.env.PLAYWRIGHT_BYPASS_AUTH === "true") {
      return NextResponse.next();
    }

    const authHeader = req.headers.get("Authorization");
    
    const token = await getToken({ 
      req, 
      secret: process.env.NEXTAUTH_SECRET,
    });

    // 1. If we ALREADY have an Authorization header (from UserContext fetch), 
    // we don't need to block it or inject anything. Let the backend handle verification.
    if (authHeader?.startsWith("Bearer ")) {
       return NextResponse.next();
    }

    // 2. If it's a protected API route and we have NO token (cookie), then return 401 JSON
    if (
      !token && (
        req.nextUrl.pathname.startsWith("/api/v1/auth/me") ||
        (req.nextUrl.pathname.startsWith("/api/v1/") && !req.nextUrl.pathname.startsWith("/api/v1/auth/"))
      )
    ) {
      return new NextResponse(
        JSON.stringify({ 
          error: "Unauthorized", 
          message: "No valid session token found. Please log in again.",
          debug: { path: req.nextUrl.pathname, hasCookie: !!req.cookies.get("next-auth.session-token") || !!req.cookies.get("__Secure-next-auth.session-token") }
        }),
        { 
          status: 401, 
          headers: { 
            "Content-Type": "application/json",
            "X-FAIM-Debug": "Middleware-No-Token" 
          } 
        }
      );
    }

    // Intercept proxied API routes to inject Authorization header
    if (
      (req.nextUrl.pathname.startsWith("/api/v1/") ||
       req.nextUrl.pathname.startsWith("/api/ops/") ||
       req.nextUrl.pathname.startsWith("/api/billing/")) &&
      token?.accessToken
    ) {
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

        // Only require authorized=true for PAGES (dashboard)
        // API routes are handled manually above to return JSON
        if (req.nextUrl.pathname.startsWith("/api/")) return true;
        return !!token;
      },
    },
    pages: {
      signIn: "/auth/login",
    },
  }
);

// 2. Ensure it matches dashboard and protected API routes
export const config = {
  matcher: [
    "/dashboard",
    "/dashboard/:path*", 
    "/api/v1/auth/me", // Specifically protect /me
    "/api/v1/((?!auth/).*)", // Protect all other v1 except auth endpoints
    "/api/admin/:path*",
    "/api/ops/:path*", 
    "/api/billing/:path*"
  ],
};
