import { imageHosts } from './image-hosts.config.js';

/** @type {import('next').NextConfig} */
const nextConfig = {
  productionBrowserSourceMaps: true,
  distDir: process.env.DIST_DIR || '.next',

  typescript: {
      ignoreBuildErrors: true,
    },

  eslint: {
    ignoreDuringBuilds: true,
  },

  images: {
    remotePatterns: imageHosts,
  },

  async redirects() {
    return [
      {
        source: '/',
        destination: '/migrate-dashboard',
        permanent: false,
      },
    ];
  }
};

export default nextConfig;
