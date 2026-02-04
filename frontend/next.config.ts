import type { NextConfig } from 'next';
import path from 'path';

const nextConfig: NextConfig = {
  /* config options here */
  turbopack: {
    // Ensure Turbopack resolves the workspace root correctly in monorepos
    // or when multiple lockfiles exist on the machine.
    root: path.join(__dirname),
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
