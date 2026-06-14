import { readFileSync } from "node:fs";
import { join } from "node:path";

let cachedSvg: string | null = null;

/** Circle scatter SVG with per-circle stagger indices for scroll reveal. */
export function getCircleScatterSvg(): string {
  if (cachedSvg) return cachedSvg;

  let index = 0;
  cachedSvg = readFileSync(
    join(process.cwd(), "public/circle-scatter-haikei.svg"),
    "utf8",
  )
    .replace(
      '<svg id="visual"',
      '<svg class="circle-scatter__svg" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false"',
    )
    .replace(/<rect x="0" y="0" width="900" height="600" fill="#000000"><\/rect>/, "")
    .replace(/<g fill="#ffffff">/, '<g>')
    .replace(/<circle /g, () => {
      const i = index;
      index += 1;
      return `<circle class="circle-scatter__dot" style="--scatter-i:${i}" `;
    });

  return cachedSvg;
}
