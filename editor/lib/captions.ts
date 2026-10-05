import type { Word } from "./types";

/** Cómo se marca la palabra que se está diciendo. */
type Highlight = "color" | "box" | "karaoke" | "none";
/** Animación de entrada de cada frase. */
type Animation = "pop" | "word-pop" | "slide" | "none";

export type CaptionPreset = {
  id: string;
  label: string;
  font: string;
  weight: number;
  italic?: boolean;
  /** Tamaño de letra relativo al ancho del video. */
  size: number;
  uppercase: boolean;
  /** Palabras por frase en pantalla. */
  maxWords: number;
  text: string;
  accent: string;
  /** Grosor del borde relativo al tamaño de letra. */
  stroke?: { color: string; width: number };
  /** Sombra; `glow` usa el color de resaltado. */
  shadow?: { color: string | "glow"; blur: number; y: number };
  highlight: Highlight;
  animation: Animation;
  /** Inclinación alterna de cada frase, en radianes. */
  tilt?: number;
};

export const CAPTION_PRESETS: CaptionPreset[] = [
  {
    id: "tiktok",
    label: "TikTok",
    font: "Montserrat",
    weight: 900,
    size: 0.075,
    uppercase: true,
    maxWords: 3,
    text: "#ffffff",
    accent: "#ffe600",
    stroke: { color: "#000000", width: 0.18 },
    highlight: "color",
    animation: "pop",
  },
  {
    id: "hormozi",
    label: "Hormozi",
    font: "Montserrat",
    weight: 900,
    size: 0.085,
    uppercase: true,
    maxWords: 3,
    text: "#ffffff",
    accent: "#2bff5c",
    stroke: { color: "#000000", width: 0.16 },
    shadow: { color: "rgba(0,0,0,0.6)", blur: 0.15, y: 0.08 },
    highlight: "color",
    animation: "word-pop",
  },
  {
    id: "mrbeast",
    label: "MrBeast",
    font: "Bangers",
    weight: 400,
    size: 0.115,
    uppercase: true,
    maxWords: 2,
    text: "#ffffff",
    accent: "#ffd400",
    stroke: { color: "#000000", width: 0.22 },
    shadow: { color: "rgba(0,0,0,0.7)", blur: 0.1, y: 0.1 },
    highlight: "color",
    animation: "word-pop",
    tilt: 0.05,
  },
  {
    id: "box",
    label: "Caja",
    font: "Poppins",
    weight: 800,
    size: 0.07,
    uppercase: true,
    maxWords: 3,
    text: "#ffffff",
    accent: "#7c3aed",
    shadow: { color: "rgba(0,0,0,0.55)", blur: 0.2, y: 0.06 },
    highlight: "box",
    animation: "pop",
  },
  {
    id: "karaoke",
    label: "Karaoke",
    font: "Montserrat",
    weight: 900,
    size: 0.075,
    uppercase: true,
    maxWords: 4,
    text: "#ffffff",
    accent: "#ffe600",
    stroke: { color: "#000000", width: 0.18 },
    highlight: "karaoke",
    animation: "none",
  },
  {
    id: "neon",
    label: "Neón",
    font: "Anton",
    weight: 400,
    size: 0.09,
    uppercase: true,
    maxWords: 3,
    text: "#ffffff",
    accent: "#00e5ff",
    shadow: { color: "glow", blur: 0.45, y: 0 },
    highlight: "color",
    animation: "pop",
  },
  {
    id: "editorial",
    label: "Editorial",
    font: "Playfair Display",
    weight: 700,
    italic: true,
    size: 0.062,
    uppercase: false,
    maxWords: 5,
    text: "#ffffff",
    accent: "#ffd8a8",
    shadow: { color: "rgba(0,0,0,0.65)", blur: 0.35, y: 0.05 },
    highlight: "color",
    animation: "slide",
  },
  {
    id: "minimal",
    label: "Minimal",
    font: "Poppins",
    weight: 600,
    size: 0.052,
    uppercase: false,
    maxWords: 4,
    text: "#ffffff",
    accent: "#ffffff",
    shadow: { color: "rgba(0,0,0,0.7)", blur: 0.3, y: 0.04 },
    highlight: "none",
    animation: "none",
  },
];

export function getPreset(id: string): CaptionPreset {
  return CAPTION_PRESETS.find((p) => p.id === id) ?? CAPTION_PRESETS[0];
}

function fontString(p: CaptionPreset, px: number) {
  return `${p.italic ? "italic " : ""}${p.weight} ${px}px "${p.font}", system-ui, sans-serif`;
}

/** Carga la fuente del estilo antes de dibujar en el canvas (si no, usaría la de sistema). */
export async function ensureFont(p: CaptionPreset) {
  try {
    await document.fonts.load(fontString(p, 40), "AÁÑ");
  } catch {
    // Si falla, se dibuja con la fuente de respaldo.
  }
}

/** Palabra activa: desde que empieza hasta que empieza la siguiente, para que no parpadee entre palabras. */
function isActive(group: Word[], i: number, t: number) {
  const w = group[i];
  const until = Math.max(w.end, group[i + 1]?.start ?? w.end);
  return t >= w.start && t < until;
}

const easeOut = (x: number) => 1 - (1 - Math.min(1, Math.max(0, x))) ** 3;

/** Dibuja una frase de subtítulos centrada en `yRatio` (proporción del alto). */
export function drawCaption(
  ctx: CanvasRenderingContext2D,
  group: Word[],
  t: number,
  preset: CaptionPreset,
  yRatio: number,
  colors: { text: string; accent: string },
) {
  const { width: W, height: H } = ctx.canvas;
  const size = Math.round(W * preset.size);
  ctx.font = fontString(preset, size);
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.lineJoin = "round";

  const words = group.map((w) => (preset.uppercase ? w.text.toUpperCase() : w.text));
  // Más separación si la palabra activa crece o lleva caja, para que no pise a las vecinas.
  const space = ctx.measureText(" ").width * (preset.animation === "word-pop" || preset.highlight === "box" ? 1.6 : 1);
  const widths = words.map((w) => ctx.measureText(w).width);
  const lines = splitLines(widths, space, W * 0.88);
  const lineWidth = (l: number[]) => l.reduce((a, i) => a + widths[i], 0) + space * (l.length - 1);
  const maxWidth = Math.max(...lines.map(lineWidth));
  const lineHeight = size * 1.2;
  // Si la frase no cabe en el 90 % del ancho, se reduce para que no se salga.
  const fit = Math.min(1, (W * 0.9) / maxWidth);

  const age = t - group[0].start;
  let scale = fit;
  let alpha = 1;
  let dy = 0;
  if (preset.animation === "pop") scale *= 1 + (1 - easeOut(age / 0.15)) * 0.2;
  if (preset.animation === "slide") {
    alpha = easeOut(age / 0.25);
    dy = (1 - easeOut(age / 0.25)) * size * 0.6;
  }

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(W / 2, H * yRatio + dy);
  if (preset.tilt) ctx.rotate(Math.round(group[0].start * 10) % 2 ? preset.tilt : -preset.tilt);
  ctx.scale(scale, scale);

  lines.forEach((line, li) => {
    const y = (li - (lines.length - 1) / 2) * lineHeight;
    let x = -lineWidth(line) / 2;
    for (const i of line) {
      drawWord(ctx, words[i], widths[i], x, y, size, preset, colors, isActive(group, i, t), t >= group[i].start);
      x += widths[i] + space;
    }
  });
  ctx.restore();
}

function drawWord(
  ctx: CanvasRenderingContext2D,
  text: string,
  width: number,
  x: number,
  y: number,
  size: number,
  p: CaptionPreset,
  colors: { text: string; accent: string },
  active: boolean,
  spoken: boolean,
) {
  ctx.save();
  if (p.animation === "word-pop" && active) {
    const cx = x + width / 2;
    ctx.translate(cx, y);
    ctx.scale(1.12, 1.12);
    ctx.translate(-cx, -y);
  }

  if (p.highlight === "box" && active) {
    const padX = size * 0.18;
    const padY = size * 0.12;
    ctx.fillStyle = colors.accent;
    ctx.beginPath();
    ctx.roundRect(x - padX, y - size * 0.55 - padY, width + padX * 2, size * 1.1 + padY * 2, size * 0.2);
    ctx.fill();
  }

  const fill =
    (p.highlight === "color" && active) || (p.highlight === "karaoke" && spoken) ? colors.accent : colors.text;

  if (p.shadow) {
    ctx.shadowColor = p.shadow.color === "glow" ? colors.accent : p.shadow.color;
    ctx.shadowBlur = size * p.shadow.blur;
    ctx.shadowOffsetY = size * p.shadow.y;
  }
  if (p.stroke) {
    ctx.lineWidth = size * p.stroke.width;
    ctx.strokeStyle = p.stroke.color;
    ctx.strokeText(text, x, y);
    // La sombra solo en el borde, para que el relleno quede limpio.
    ctx.shadowColor = "transparent";
  }
  ctx.fillStyle = fill;
  ctx.fillText(text, x, y);
  ctx.restore();
}

/** Reparte las palabras en una o dos líneas equilibradas según el ancho disponible. */
function splitLines(widths: number[], space: number, maxWidth: number): number[][] {
  const all = widths.map((_, i) => i);
  const total = widths.reduce((a, b) => a + b, 0) + space * (widths.length - 1);
  if (total <= maxWidth || widths.length < 2) return [all];
  let best = 1;
  let bestDiff = Infinity;
  for (let k = 1; k < widths.length; k++) {
    const a = widths.slice(0, k).reduce((s, w) => s + w, 0) + space * (k - 1);
    const b = total - a - space;
    if (Math.abs(a - b) < bestDiff) {
      bestDiff = Math.abs(a - b);
      best = k;
    }
  }
  return [all.slice(0, best), all.slice(best)];
}
