import { withAuth } from "next-auth/middleware";
import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export default async function middleware(req: NextRequest) {
  // 1. Only intercept /api/v1/* (proxied to backend)
  if (req.nextUrl.pathname.startsWith("/api/v1/")) {
    console.log("[MIDDLEWARE] Intercepting request:", req.nextUrl.pathname);
    const token = await getToken({ req });
    console.log("[MIDDLEWARE] Token found?", !!token);

    // 2. If we have a token, inject Authorization header headers mutation
    if (token?.accessToken) {
      const requestHeaders = new Headers(req.headers);
      requestHeaders.set("Authorization", `Bearer ${token.accessToken}`);

      // Return response with modified headers for the rewrite to pick up?
      // Next.js middleware header modification operates on the *downstream* request.
      return NextResponse.next({
        request: {
          headers: requestHeaders,
        },
      });
    }
  }

  // 3. Fallback check for session (optional, usually handled by matching)
  return NextResponse.next();
}

// Ensure it matches only API routes we care about
export const config = {
  matcher: ["/api/v1/:path*"],
};
