/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    // TODO: Add environment variables for API endpoints
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`,
      },
    ]
  },
  // Suppress hydration warnings for browser extension attributes
  reactStrictMode: true,
  webpack: (config) => {
    config.resolve.alias.canvas = false;

    // Copy PDF.js worker and standard fonts to public folder
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      path: false,
      stream: false,
      zlib: false,
    };

    return config;
  },
}

module.exports = nextConfig
