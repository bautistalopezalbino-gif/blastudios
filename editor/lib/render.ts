import type { CaptionStyle, FaceBox, Word } from "./types";

const CAPTION_LOW = 0.72;
const CAPTION_HIGH = 0.2;

/**
 * Dibuja el fotograma en formato 9:16 y los subtítulos.
 * Con `face`, el recorte sigue a la cara y los subtítulos se apartan si la taparían.
 */
export function drawFrame(
  ctx: CanvasRenderingContext2D,
  video: HTMLVideoElement,
  group: Word[] | undefined,
  t: number,
  style: CaptionStyle,
  face?: FaceBox,
) {
  const { width: W, height: H } = ctx.canvas;
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  let captionY = CAPTION_LOW;
  if (vw && vh) {
    const scale = Math.max(W / vw, H / vh);
    const dw = vw * scale;
    const dh = vh * scale;
    // Centra la cara (o el centro del video) y limita para no dejar bordes negros.
    const x = clamp(W / 2 - (face?.cx ?? 0.5) * dw, W - dw, 0);
    const y = clamp(H * 0.4 - (face?.cy ?? 0.5) * dh, H - dh, 0);
    ctx.drawImage(video, x, y, dw, dh);

    if (face) {
      const faceTop = (y + (face.cy - face.h / 2) * dh) / H;
      const faceBottom = (y + (face.cy + face.h / 2) * dh) / H;
      const band = 0.08;
      if (faceBottom > CAPTION_LOW - band && faceTop < CAPTION_LOW + band) captionY = CAPTION_HIGH;
    }
  }
  if (group) drawCaption(ctx, group, t, style, captionY);
}

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
