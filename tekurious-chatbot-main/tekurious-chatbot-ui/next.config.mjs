/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output for smaller Docker images on Cloud Run
  output: 'standalone',
};

export default nextConfig;
