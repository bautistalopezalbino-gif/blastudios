import type { SourceFrame } from "./export";
import { drawCaption, type CaptionPreset } from "./captions";
import type { FaceBox, Word } from "./types";

const CAPTION_LOW = 0.72;
const CAPTION_HIGH = 0.2;

export type FrameOptions = {
  group?: Word[];
  t: number;
  caption: { preset: CaptionPreset; colors: { text: string; accent: string } };
  face?: FaceBox;
  /** Factor de zoom de énfasis (1 = sin zoom). */
  zoom?: number;
  emoji?: { emoji: string; progress: number };
  /** Título de enganche al principio del clip; `progress` va de 0 a 1 durante el tiempo que se muestra. */
  title?: { text: string; progress: number };
};

/**
 * Dibuja el fotograma en formato 9:16, los subtítulos y el emoji.
 * Con `face`, el recorte (y el zoom) sigue a la cara y los subtítulos se apartan si la taparían.
 */
export function drawFrame(
  ctx: CanvasRenderingContext2D,
  frame: SourceFrame,
  { group, t, caption, face, zoom = 1, emoji, title }: FrameOptions,
) {
  const { width: W, height: H } = ctx.canvas;
  const vw = frame.width;
  const vh = frame.height;
  let captionY = CAPTION_LOW;
  if (vw && vh) {
    const baseScale = Math.max(W / vw, H / vh);
    const place = (scale: number) => {
      const dw = vw * scale;
      const dh = vh * scale;
      // Centra la cara (o el centro del video) y limita para no dejar bordes negros.
      const x = clamp(W / 2 - (face?.cx ?? 0.5) * dw, W - dw, 0);
      const y = clamp(H * (face ? 0.4 : 0.5) - (face?.cy ?? 0.5) * dh, H - dh, 0);
      return { x, y, dw, dh };
    };
    const { x, y, dw, dh } = place(baseScale * zoom);
    ctx.drawImage(frame.image, x, y, dw, dh);

    if (face) {
      // Se decide con el encuadre sin zoom para que los subtítulos no salten durante el zoom.
      const base = place(baseScale);
      const faceTop = (base.y + (face.cy - face.h / 2) * base.dh) / H;
      const faceBottom = (base.y + (face.cy + face.h / 2) * base.dh) / H;
      const band = 0.08;
      if (faceBottom > CAPTION_LOW - band && faceTop < CAPTION_LOW + band) captionY = CAPTION_HIGH;
    }
  }
  // Con el título arriba, los subtítulos que irían arriba bajan justo debajo de él.
  const titleLayout = title ? layoutTitle(ctx, title.text, caption) : null;
  if (titleLayout && captionY === CAPTION_HIGH) {
    captionY = TITLE_Y + titleLayout.boxH / ctx.canvas.height + caption.preset.size * 0.9;
  }
  if (group) drawCaption(ctx, group, t, caption.preset, captionY, caption.colors);
  if (emoji) drawEmoji(ctx, emoji.emoji, emoji.progress, captionY, caption.preset.size);
  if (title && titleLayout) drawTitle(ctx, titleLayout, title.progress, caption);
}

const TITLE_Y = 0.1;

type TitleLayout = { font: string; lines: string[]; size: number; lineH: number; boxW: number; boxH: number };

function layoutTitle(ctx: CanvasRenderingContext2D, text: string, caption: FrameOptions["caption"]): TitleLayout {
  const { preset } = caption;
  const W = ctx.canvas.width;
  const size = Math.round(W * 0.06);
  const font = `${preset.italic ? "italic " : ""}${Math.max(700, preset.weight)} ${size}px "${preset.font}", system-ui, sans-serif`;
  ctx.save();
  ctx.font = font;
  const lines = wrap(ctx, preset.uppercase ? text.toUpperCase() : text, W * 0.8).slice(0, 3);
  const boxW = Math.max(...lines.map((l) => ctx.measureText(l).width)) + size * 1.2;
  ctx.restore();
  const lineH = size * 1.25;
  return { font, lines, size, lineH, boxW, boxH: lines.length * lineH + size * 0.7 };
}

/** Título en una caja del color de resaltado, arriba; entra deslizándose y se desvanece al final. */
function drawTitle(ctx: CanvasRenderingContext2D, l: TitleLayout, progress: number, caption: FrameOptions["caption"]) {
  const { width: W, height: H } = ctx.canvas;
  const { colors } = caption;
  ctx.save();
  ctx.font = l.font;
  const enter = Math.min(1, progress / 0.12);
  const exit = progress > 0.85 ? 1 - (progress - 0.85) / 0.15 : 1;
  ctx.globalAlpha = Math.min(enter, exit);
  ctx.translate(W / 2, H * TITLE_Y + (1 - enter) * -l.size);
  ctx.fillStyle = colors.accent;
  ctx.shadowColor = "rgba(0,0,0,0.4)";
  ctx.shadowBlur = l.size * 0.4;
  ctx.beginPath();
  ctx.roundRect(-l.boxW / 2, 0, l.boxW, l.boxH, l.size * 0.35);
  ctx.fill();
  ctx.shadowColor = "transparent";
  ctx.fillStyle = isLight(colors.accent) ? "#111111" : "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  l.lines.forEach((line, i) => ctx.fillText(line, 0, l.size * 0.35 + l.lineH * (i + 0.5)));
  ctx.restore();
}

function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const test = line ? `${line} ${word}` : word;
    if (line && ctx.measureText(test).width > maxWidth) {
      lines.push(line);
      line = word;
    } else line = test;
  }
  if (line) lines.push(line);
  return lines;
}

function isLight(hex: string) {
  const n = parseInt(hex.replace("#", "").padEnd(6, "0").slice(0, 6), 16);
  return 0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255) > 150;
}

/** Emoji con rebote de entrada y desvanecido de salida, junto a los subtítulos. */
function drawEmoji(ctx: CanvasRenderingContext2D, emoji: string, progress: number, captionY: number, captionSize: number) {
  const { width: W, height: H } = ctx.canvas;
  const pop = progress < 0.15 ? backOut(progress / 0.15) : 1;
  const fade = progress > 0.8 ? 1 - (progress - 0.8) / 0.2 : 1;
  const size = W * 0.16;
  // Separación según el tamaño de los subtítulos (que pueden ocupar dos líneas).
  const gap = 0.06 + captionSize * 0.9;
  const y = captionY === CAPTION_LOW ? H * (CAPTION_LOW - gap) : H * (CAPTION_HIGH + gap);
  ctx.save();
  ctx.globalAlpha = fade;
  ctx.translate(W / 2, y);
  ctx.rotate((1 - pop) * 0.4);
  ctx.scale(pop, pop);
  ctx.font = `${size}px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(emoji, 0, 0);
  ctx.restore();
}

const backOut = (x: number) => 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2;

function clamp(v: number, min: number, max: number) {
  return Math.min(max, Math.max(min, v));
}
