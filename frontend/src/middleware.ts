import { withAuth } from "next-auth/middleware";
import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// 1. Export withAuth to protect dashboard and API routes
export default withAuth(
  async function middleware(req) {
    const token = req.nextauth.token;

    // Intercept proxied API routes to inject Authorization header
    if (
      req.nextUrl.pathname.startsWith("/api/v1/") ||
      req.nextUrl.pathname.startsWith("/api/ops/") ||
      req.nextUrl.pathname.startsWith("/api/billing/")
    ) {
      if (token?.accessToken) {
        const requestHeaders = new Headers(req.headers);
        requestHeaders.set("Authorization", `Bearer ${token.accessToken}`);

        return NextResponse.next({
          request: {
            headers: requestHeaders,
          },
        });
      }
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      // Return true if the user is authorized
      authorized: ({ token }) => !!token,
    },
    pages: {
      signIn: "/auth/login",
    },
  }
);

// 2. Ensure it matches dashboard and protected API routes
export const config = {
  matcher: [
    "/dashboard/:path*", 
    "/api/v1/:path*", 
    "/api/ops/:path*", 
    "/api/billing/:path*"
  ],
};
