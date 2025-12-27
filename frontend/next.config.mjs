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
  // IMPORTANT: use /api/v1 to match your frontend contract and SSE stream route.
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },

      // Optional: if you still have any old calls to /api/*
      // keep this as a backward-compatible proxy.
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },

  // Optional but often helpful for local dev if images/assets are loaded from backend:
  // images: { remotePatterns: [{ protocol: "http", hostname: "127.0.0.1", port: "8000" }] },
};

export default nextConfig;
