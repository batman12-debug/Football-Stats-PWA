/**
 * Runtime API proxy helpers for Netlify / Next.js route handlers.
 * SSR uses API_URL directly; browser requests use same-origin /api/* proxy.
 */

const LOCAL_BACKEND = "http://localhost:8000";

export function getBackendBaseUrl(): string {
  const raw =
    process.env.API_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    LOCAL_BACKEND;

  return raw.replace(/\/$/, "");
}

export function buildBackendApiUrl(pathSegments: string[], search: string): string | null {
  const base = getBackendBaseUrl();

  try {
    const baseUrl = new URL(base);
    const isLocalHost =
      baseUrl.hostname === "localhost" || baseUrl.hostname === "127.0.0.1";

    if (process.env.NETLIFY === "true" && baseUrl.protocol !== "https:" && !isLocalHost) {
      return null;
    }

    const path = pathSegments.map(encodeURIComponent).join("/");
    const url = new URL(`/api/${path}${search}`, baseUrl);
    return url.href;
  } catch {
    return null;
  }
}

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

export function filterProxyResponseHeaders(headers: Headers): Headers {
  const filtered = new Headers();
  headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      filtered.set(key, value);
    }
  });
  return filtered;
}

export function filterProxyRequestHeaders(headers: Headers): Headers {
  const filtered = new Headers();
  headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "host" || lower === "connection" || HOP_BY_HOP.has(lower)) {
      return;
    }
    filtered.set(key, value);
  });
  return filtered;
}
