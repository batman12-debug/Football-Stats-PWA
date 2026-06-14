import { readFileSync } from "node:fs";
import { join } from "node:path";

const cache = new Map<string, string>();

type BlobSceneMode = "hero" | "panel" | "tomorrow";

/** Haikei blob scene with animated corner groups. */
export function getBlobSceneSvg(
  filename: string,
  mode: BlobSceneMode = "hero",
  panelSvgClass = "matches-blob__svg",
): string {
  const cacheKey = `${mode}:${panelSvgClass}:${filename}`;
  const cached = cache.get(cacheKey);
  if (cached) return cached;

  const svgClass = mode === "hero" ? "hero-blob__svg" : panelSvgClass;
  const preserveAspectRatio =
    mode === "hero" || mode === "tomorrow" ? "xMidYMin slice" : "none";

  let svg = readFileSync(join(process.cwd(), "public", filename), "utf8");

  if (mode === "panel" || mode === "tomorrow") {
    svg = svg.replace(/<rect x="0" y="0" width="900" height="600" fill="#000000"><\/rect>/, "");
  }

  svg = svg
    .replace(
      '<svg id="visual"',
      `<svg class="${svgClass}" preserveAspectRatio="${preserveAspectRatio}" aria-hidden="true" focusable="false"`,
    )
    .replace(
      '<g transform="translate(900, 0)">',
      '<g transform="translate(900, 0)"><g class="hero-blob__group hero-blob__group--tr">',
    )
    .replace(
      '</g><g transform="translate(0, 600)">',
      '</g></g><g transform="translate(0, 600)"><g class="hero-blob__group hero-blob__group--bl">',
    )
    .replace("</g></svg>", "</g></g></svg>");

  cache.set(cacheKey, svg);
  return svg;
}
