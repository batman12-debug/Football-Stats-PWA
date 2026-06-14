import { safeImageUrl } from "@/lib/security";

const CATEGORY_FALLBACKS: Record<string, string> = {
  "World Cup": "/news-fallback-world-cup.svg",
  "Premier League": "/news-fallback-premier-league.svg",
  "La Liga": "/news-fallback-la-liga.svg",
  "Serie A": "/news-fallback-serie-a.svg",
  Bundesliga: "/news-fallback-bundesliga.svg",
  "Ligue 1": "/news-fallback-ligue-1.svg",
  Transfers: "/news-fallback-transfers.svg",
  Football: "/news-fallback-football.svg",
};

const DEFAULT_FALLBACK = "/news-fallback-football.svg";

/** Request sharp card images from known news CDNs. */
export function enhanceNewsImageUrl(url: string): string {
  let upgraded = url.trim();

  upgraded = upgraded.replace(/\/ace\/standard\/\d+\//, "/ace/standard/976/");
  upgraded = upgraded.replace(/\/images\/ic\/\d+x\d+\//, "/images/ic/976x549/");

  if (upgraded.includes("i.guim.co.uk")) {
    try {
      const parsed = new URL(upgraded);
      parsed.searchParams.set("width", "1200");
      parsed.searchParams.set("quality", "85");
      parsed.searchParams.set("auto", "format");
      parsed.searchParams.set("fit", "max");
      upgraded = parsed.toString();
    } catch {
      // Keep original URL if parsing fails.
    }
  }

  upgraded = upgraded.replace(
    /-(\d+)x(\d+)(\.(?:jpe?g|png|webp|gif))(?=\?|$)/i,
    "$3",
  );

  if (/espncdn\.com\/combiner\/i/i.test(upgraded) && !/[?&]w=/i.test(upgraded)) {
    upgraded += upgraded.includes("?") ? "&w=1280" : "?w=1280";
  }

  return upgraded;
}

export function getNewsFallbackImage(category: string): string {
  return CATEGORY_FALLBACKS[category] ?? DEFAULT_FALLBACK;
}

export function resolveNewsImage(
  imageUrl: string | null | undefined,
  category: string,
): string {
  const safe = safeImageUrl(imageUrl);
  if (!safe) {
    return getNewsFallbackImage(category);
  }
  return enhanceNewsImageUrl(safe);
}

export function resolveTransferImage(
  imageUrl: string | null | undefined,
): string {
  const safe = safeImageUrl(imageUrl);
  if (!safe) {
    return "/news-fallback-transfers.svg";
  }
  return enhanceNewsImageUrl(safe);
}
