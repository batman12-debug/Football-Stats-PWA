import type { LiveScoreSnapshot } from "./formatNotification";
import { formatCenterLinesForSnapshot } from "./formatNotification";
import type { PinEntry } from "./types";

const WIDTH = 720;
const HEIGHT = 280;
const BG = "#0c0c0c";
const MUTED = "#8a8a8a";
const WHITE = "#ffffff";
const FLAG_SIZE = 72;
const FLAG_RADIUS = 14;

function truncate(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let value = text;
  while (value.length > 1 && ctx.measureText(`${value}…`).width > maxWidth) {
    value = value.slice(0, -1);
  }
  return `${value}…`;
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

async function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function drawFlagPlaceholder(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  code: string | null,
  name: string
) {
  ctx.fillStyle = "#1a1a1a";
  roundRect(ctx, x, y, FLAG_SIZE, FLAG_SIZE, FLAG_RADIUS);
  ctx.fill();
  ctx.fillStyle = WHITE;
  ctx.font = "700 18px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const label = (code ?? name.slice(0, 3)).toUpperCase();
  ctx.fillText(label, x + FLAG_SIZE / 2, y + FLAG_SIZE / 2);
}

async function drawFlag(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  logo: string | null,
  code: string | null,
  name: string
) {
  ctx.save();
  roundRect(ctx, x, y, FLAG_SIZE, FLAG_SIZE, FLAG_RADIUS);
  ctx.clip();
  ctx.fillStyle = "#1a1a1a";
  ctx.fillRect(x, y, FLAG_SIZE, FLAG_SIZE);

  if (logo) {
    const img = await loadImage(logo);
    if (img) {
      ctx.drawImage(img, x, y, FLAG_SIZE, FLAG_SIZE);
      ctx.restore();
      return;
    }
  }

  ctx.restore();
  drawFlagPlaceholder(ctx, x, y, code, name);
}

/**
 * Rich notification preview matching the in-app match row:
 * stage · home flag · center kickoff · away flag.
 * Returns a PNG data URL, or null when canvas is unavailable.
 */
export async function buildPinNotificationCard(
  entry: PinEntry,
  snapshot: LiveScoreSnapshot | null,
  nowMs: number = Date.now()
): Promise<string | null> {
  if (typeof document === "undefined") return null;

  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;

  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  const stage = entry.stageLabel?.trim() || "CheckBoard";
  ctx.fillStyle = MUTED;
  ctx.font = "500 18px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(truncate(ctx, stage, WIDTH - 48), 28, 22);

  const flagY = 64;
  const leftX = 100;
  const rightX = WIDTH - 100 - FLAG_SIZE;
  const centerX = WIDTH / 2;

  await drawFlag(ctx, leftX, flagY, entry.homeLogo, entry.homeCode, entry.homeName);
  await drawFlag(ctx, rightX, flagY, entry.awayLogo, entry.awayCode, entry.awayName);

  const center = formatCenterLinesForSnapshot(entry, snapshot, nowMs);
  ctx.fillStyle = WHITE;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = "600 26px system-ui, -apple-system, sans-serif";
  ctx.fillText(center.primary, centerX, flagY + FLAG_SIZE / 2 - 14);
  ctx.font = "500 22px system-ui, -apple-system, sans-serif";
  ctx.fillText(center.secondary, centerX, flagY + FLAG_SIZE / 2 + 18);

  const nameY = flagY + FLAG_SIZE + 28;
  ctx.font = "600 20px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(truncate(ctx, entry.homeName, 200), leftX + FLAG_SIZE / 2, nameY);
  ctx.fillText(truncate(ctx, entry.awayName, 200), rightX + FLAG_SIZE / 2, nameY);

  try {
    return canvas.toDataURL("image/png");
  } catch {
    // Tainted canvas (CORS) — fall back without logos already handled per flag.
    return null;
  }
}
