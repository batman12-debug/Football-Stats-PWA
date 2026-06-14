/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === "production";

const securityHeaders = [
  { key: "X-DNS-Prefetch-Control", value: "on" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=()",
  },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "object-src 'self'",
      "font-src 'self' data:",
      "connect-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
  ...(isProd
    ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }]
    : []),
];

const nextConfig = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 86400,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "media.api-sports.io",
        pathname: "/football/**",
      },
      {
        protocol: "https",
        hostname: "e0.365dm.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "e1.365dm.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "e2.365dm.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "e3.365dm.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "ichef.bbci.co.uk",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "newsimg.bbc.co.uk",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "a.espncdn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "a1.espncdn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "a2.espncdn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "a3.espncdn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "a4.espncdn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "cdn.espn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "icdn.football-italia.net",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "assets.guim.co.uk",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "media.guim.co.uk",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "i.guim.co.uk",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "flagcdn.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "r2.thesportsdb.com",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "www.thesportsdb.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
