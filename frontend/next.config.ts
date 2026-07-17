import type { NextConfig } from 'next';
import path from 'path';

const nextConfig: NextConfig = {
  /* config options here */
  turbopack: {
    root: path.join(__dirname),
    resolveAlias: {
      '@': path.join(__dirname, 'src'),
    },
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.join(__dirname, 'src'),
    };
    return config;
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  // Local-dev cookie proxy. Set NEXT_PUBLIC_USE_API_PROXY=true so the browser
  // only ever talks to the Next.js origin — the httpOnly auth cookie becomes
  // host-only on :3000 and the middleware can read it. In prod the frontend and
  // API share a parent domain (*.trytone.ai) so no proxy is needed (leave it
  // unset and point NEXT_PUBLIC_BACKEND_URL at the API host).
  async rewrites() {
    if (process.env.NEXT_PUBLIC_USE_API_PROXY !== 'true') return [];
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }];
  },
  async redirects() {
    return [
      { source: '/auth/login', destination: '/login', permanent: false },
      { source: '/auth/signup', destination: '/signup', permanent: false },
      { source: '/auth/forgot-password', destination: '/forgot-password', permanent: false },
      { source: '/auth/forgotpassword', destination: '/forgot-password', permanent: false },
      { source: '/auth/reset-password', destination: '/reset-password', permanent: false },
      { source: '/auth/verify-email', destination: '/verify-email', permanent: false },
      { source: '/auth/verify_signup', destination: '/verify-email', permanent: false },
      { source: '/verify/user_to_workspace', destination: '/accept-invite', permanent: false },
    ];
  },
};

export default nextConfig;
