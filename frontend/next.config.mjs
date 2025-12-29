/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep your current turbo + eslint behavior
  experimental: { turbo: { rules: {} } },
  eslint: { ignoreDuringBuilds: true },

  // Allow these origins in dev (Next uses this for some dev features)
  allowedDevOrigins: [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://[::1]:3000",
  ],

  // Proxy API calls to backend (same-origin from browser)
  // IMPORTANT: Frontend calls /api/v1/* which maps to backend root
  async rewrites() {
    return [
      // Control plane routes (orgs, projects, api_keys, etc.) - backend has /v1 prefix
      {
        source: "/api/v1/orgs",
        destination: "http://127.0.0.1:8000/v1/orgs",
      },
      {
        source: "/api/v1/projects",
        destination: "http://127.0.0.1:8000/v1/projects",
      },
      {
        source: "/api/v1/api_keys",
        destination: "http://127.0.0.1:8000/v1/api_keys",
      },
      {
        source: "/api/v1/api_keys/:path*",
        destination: "http://127.0.0.1:8000/v1/api_keys/:path*",
      },
      {
        source: "/api/v1/me",
        destination: "http://127.0.0.1:8000/v1/me",
      },
      // Graph and core API routes - backend has /api/v1 prefix
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
      // Billing routes - backend has /api/billing prefix
      {
        source: "/api/billing/:path*",
        destination: "http://127.0.0.1:8000/api/billing/:path*",
      },
      // Admin/Ops routes - backend has /api prefix
      {
        source: "/api/admin/:path*",
        destination: "http://127.0.0.1:8000/api/admin/:path*",
      },
      {
        source: "/api/ops/:path*",
        destination: "http://127.0.0.1:8000/api/ops/:path*",
      },
    ];
  },

  // Optional but often helpful for local dev if images/assets are loaded from backend:
  // images: { remotePatterns: [{ protocol: "http", hostname: "127.0.0.1", port: "8000" }] },
};

export default nextConfig;
