import type { CaptionStyle, FaceBox, Word } from "./types";

const CAPTION_LOW = 0.72;
const CAPTION_HIGH = 0.2;

export type FrameOptions = {
  group?: Word[];
  t: number;
  style: CaptionStyle;
  face?: FaceBox;
  /** Factor de zoom de énfasis (1 = sin zoom). */
  zoom?: number;
  emoji?: { emoji: string; progress: number };
};

/**
 * Dibuja el fotograma en formato 9:16, los subtítulos y el emoji.
 * Con `face`, el recorte (y el zoom) sigue a la cara y los subtítulos se apartan si la taparían.
 */
export function drawFrame(
  ctx: CanvasRenderingContext2D,
  video: HTMLVideoElement,
  { group, t, style, face, zoom = 1, emoji }: FrameOptions,
) {
  const { width: W, height: H } = ctx.canvas;
  const vw = video.videoWidth;
  const vh = video.videoHeight;
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
    ctx.drawImage(video, x, y, dw, dh);

    if (face) {
      // Se decide con el encuadre sin zoom para que los subtítulos no salten durante el zoom.
      const base = place(baseScale);
      const faceTop = (base.y + (face.cy - face.h / 2) * base.dh) / H;
      const faceBottom = (base.y + (face.cy + face.h / 2) * base.dh) / H;
      const band = 0.08;
      if (faceBottom > CAPTION_LOW - band && faceTop < CAPTION_LOW + band) captionY = CAPTION_HIGH;
    }
  }
  if (group) drawCaption(ctx, group, t, style, captionY);
  if (emoji) drawEmoji(ctx, emoji.emoji, emoji.progress, captionY);
}

/** Emoji con rebote de entrada y desvanecido de salida, junto a los subtítulos. */
function drawEmoji(ctx: CanvasRenderingContext2D, emoji: string, progress: number, captionY: number) {
  const { width: W, height: H } = ctx.canvas;
  const pop = progress < 0.15 ? backOut(progress / 0.15) : 1;
  const fade = progress > 0.8 ? 1 - (progress - 0.8) / 0.2 : 1;
  const size = W * 0.16;
  const y = captionY === CAPTION_LOW ? H * (CAPTION_LOW - 0.1) : H * (CAPTION_HIGH + 0.1);
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

function drawCaption(
  ctx: CanvasRenderingContext2D,
  group: Word[],
  t: number,
  style: CaptionStyle,
  yRatio: number,
) {
  const { width: W, height: H } = ctx.canvas;
  const size = Math.round(W * (style === "minimal" ? 0.055 : 0.075));
  ctx.font = `900 ${size}px system-ui, sans-serif`;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.lineJoin = "round";

  const words = group.map((w) => (style === "minimal" ? w.text : w.text.toUpperCase()));
  const space = ctx.measureText(" ").width;
  const widths = words.map((w) => ctx.measureText(w).width);
  const total = widths.reduce((a, b) => a + b, 0) + space * (words.length - 1);

  // Pop de entrada al aparecer cada frase.
  const age = t - group[0].start;
  const pop = style === "tiktok" ? 1 + Math.max(0, 0.15 - age) * 1.5 : 1;
  const y = H * yRatio;

  ctx.save();
  ctx.translate(W / 2, y);
  ctx.scale(pop, pop);
  let x = -total / 2;
  words.forEach((text, i) => {
    const w = group[i];
    const active = t >= w.start && t <= w.end;
    ctx.lineWidth = size * 0.18;
    ctx.strokeStyle = "black";
    ctx.strokeText(text, x, 0);
    ctx.fillStyle =
      style === "karaoke" ? (t >= w.start ? "#ffe600" : "white")
      : style === "tiktok" && active ? "#ffe600"
      : "white";
    ctx.fillText(text, x, 0);
    x += widths[i] + space;
  });
  ctx.restore();
}
