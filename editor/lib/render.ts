import type { CaptionStyle, Word } from "./types";

/** Dibuja el fotograma en formato 9:16 recortando al centro, más los subtítulos. */
export function drawFrame(
  ctx: CanvasRenderingContext2D,
  video: HTMLVideoElement,
  group: Word[] | undefined,
  t: number,
  style: CaptionStyle,
) {
  const { width: W, height: H } = ctx.canvas;
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (vw && vh) {
    const scale = Math.max(W / vw, H / vh);
    const dw = vw * scale;
    const dh = vh * scale;
    ctx.drawImage(video, (W - dw) / 2, (H - dh) / 2, dw, dh);
  }
  if (group) drawCaption(ctx, group, t, style);
}

function drawCaption(ctx: CanvasRenderingContext2D, group: Word[], t: number, style: CaptionStyle) {
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
  const y = H * 0.72;

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
