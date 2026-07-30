/** @type {import('next').NextConfig} */
const nextConfig = {
  // Turbo rules if needed
  // Keep your current turbo + eslint behavior
  experimental: {
    turbo: { rules: {} },
  },
  // Output: Standard (Monolithic) for maximum stability
  // PORT MUST BE REMOVED! Next.js only checks hostname against this list.
  allowedDevOrigins: ["127.0.0.1", "0.0.0.0", "localhost"],
  transpilePackages: [
    "react-force-graph-3d",
    "react-force-graph-2d",
    "force-graph",
    "three",
  ],
  eslint: { ignoreDuringBuilds: true },

  // Force HMR client to use the correct port
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      config.infrastructureLogging = {
        level: "error",
      };
      // Explicitly tell the HMR client where to connect
      // This fixes the "ws://127.0.0.1:3000" default if the browser sees it differently
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  },

  // Proxy API calls to backend
  // In Docker: use 'api' hostname (container name) via API_HOST env var
  // Outside Docker: defaults to 127.0.0.1:8000
  async rewrites() {
    // Use API_HOST (runtime) not NEXT_PUBLIC_API_HOST (build-time)
    // Note: We bake 'api:8000' during Docker build via Dockerfile.
    const apiHost = process.env.API_HOST || "127.0.0.1:8000";
    const apiUrl = `http://${apiHost}`;

    return [
      {
        source: "/api/health",
        destination: `${apiUrl}/health`,
      },
      {
        source: "/api/ready",
        destination: `${apiUrl}/ready`,
      },
      {
        source: "/api/version",
        destination: `${apiUrl}/version`,
      },
      {
        source: "/api/v1/:path*",
        destination: `${apiUrl}/api/v1/:path*`,
      },
      {
        source: "/api/billing/:path*",
        destination: `${apiUrl}/api/billing/:path*`,
      },
      {
        source: "/api/ops/:path*",
        destination: `${apiUrl}/api/ops/:path*`,
      },
    ];
  },
};

export default nextConfig;
