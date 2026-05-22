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
