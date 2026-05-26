import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";
const isVercel = !!process.env.VERCEL;

const apiUrl = process.env.API_URL || "http://localhost:8001";

const nextConfig: NextConfig = {
  distDir: isDev && !isVercel ? ".next-dev" : ".next",
  output: isVercel ? undefined : "standalone",
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
