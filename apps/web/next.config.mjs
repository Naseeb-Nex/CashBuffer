/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: '/ingress',
        destination: '/settings',
        permanent: false,
      },
      {
        source: '/ingress/:path*',
        destination: '/settings',
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const rawBackendUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const backendUrl = rawBackendUrl.replace(/\/$/, '').replace(/\/api\/v1$/, '');
    return [
      {
        source: '/api/backend/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
