/**
 * URL and input validation helpers.
 */

const SAFE_IMAGE_HOSTS = new Set([
  "media.api-sports.io",
  "e0.365dm.com",
  "e1.365dm.com",
  "e2.365dm.com",
  "e3.365dm.com",
  "ichef.bbci.co.uk",
  "newsimg.bbc.co.uk",
  "a.espncdn.com",
  "a1.espncdn.com",
  "a2.espncdn.com",
  "a3.espncdn.com",
  "a4.espncdn.com",
  "cdn.espn.com",
  "assets.guim.co.uk",
  "media.guim.co.uk",
  "i.guim.co.uk",
  "icdn.football-italia.net",
  "flagcdn.com",
  "r2.thesportsdb.com",
  "www.thesportsdb.com",
]);

/** Allow only http(s) links from external feeds. */
export function safeExternalUrl(url: string): string | null {
  if (!url || typeof url !== "string") {
    return null;
  }

  try {
    const parsed = new URL(url.trim());
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

/** Allow https images from known CDN hosts only. */
export function safeImageUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }

  try {
    const parsed = new URL(url.trim());
    if (parsed.protocol !== "https:") {
      return null;
    }
    if (!SAFE_IMAGE_HOSTS.has(parsed.hostname)) {
      return null;
    }
    return parsed.href;
  } catch {
    return null;
  }
}

/** OpenFootball / stable team fixture IDs are positive integers. */
export function isValidFixtureId(id: string): boolean {
  return /^\d{1,9}$/.test(id);
}
