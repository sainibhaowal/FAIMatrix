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
    "http://0.0.0.0:3000",
  ],

  // Proxy API calls to backend
  // In Docker: use 'api' hostname (container name) via API_HOST env var
  // Outside Docker: defaults to 127.0.0.1:8000
  async rewrites() {
    // Use API_HOST (runtime) not NEXT_PUBLIC_API_HOST (build-time)
    const apiHost = process.env.API_HOST || "127.0.0.1:8000";
    const apiUrl = `http://${apiHost}`;

    return [
      // Control plane routes (orgs, projects, api_keys, etc.) - backend has /v1 prefix
      {
        source: "/api/v1/orgs",
        destination: `${apiUrl}/v1/orgs`,
      },
      {
        source: "/api/v1/projects",
        destination: `${apiUrl}/v1/projects`,
      },
      {
        source: "/api/v1/api_keys",
        destination: `${apiUrl}/v1/api_keys`,
      },
      {
        source: "/api/v1/api_keys/:path*",
        destination: `${apiUrl}/v1/api_keys/:path*`,
      },
      {
        source: "/api/v1/me",
        destination: `${apiUrl}/v1/me`,
      },
      // Graph and core API routes - backend has /api/v1 prefix
      {
        source: "/api/v1/:path*",
        destination: `${apiUrl}/api/v1/:path*`,
      },
      // Billing routes - backend has /api/billing prefix
      {
        source: "/api/billing/:path*",
        destination: `${apiUrl}/api/billing/:path*`,
      },
      // Admin/Ops routes - backend has /api prefix
      {
        source: "/api/admin/:path*",
        destination: `${apiUrl}/api/admin/:path*`,
      },
      {
        source: "/api/ops/:path*",
        destination: `${apiUrl}/api/ops/:path*`,
      },
    ];
  },
};

export default nextConfig;
