import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

/**
 * Same-origin proxy for the FastAPI backend during local development.
 *
 * Browser → http://127.0.0.1:3000/backend/api/...
 * Next rewrite → http://127.0.0.1:8000/api/...
 *
 * Avoids relying on CORS for day-to-day frontend work. Backend CORS remains
 * configured for direct access if NEXT_PUBLIC_API_BASE_URL points at :8000.
 */
const backendOrigin = process.env.API_PROXY_TARGET?.replace(/\/$/, "") || "http://127.0.0.1:8000";
const configDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Avoid picking an unrelated parent lockfile as the workspace root.
  outputFileTracingRoot: configDir,
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendOrigin}/:path*`,
      },
    ];
  },
};

export default nextConfig;
