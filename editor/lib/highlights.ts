import type { Highlight, Word } from "./types";

/** Palabras clave (raíz en minúsculas, sin tildes) → emoji. */
const EMOJIS: [RegExp, string][] = [
  [/^(dinero|plata|pasta|euro|dolar|ganar|ingreso|venta|vend)/, "💰"],
  [/^(amor|quiero|encanta|corazon)/, "❤️"],
  [/^(fuego|brutal|increible|epico|locura)/, "🔥"],
  [/^(idea|truco|consejo|tip|secreto|clave)/, "💡"],
  [/^(tiempo|rapido|minuto|segundo|hora|hoy)/, "⏰"],
  [/^(problema|error|cuidado|peligro|nunca)/, "⚠️"],
  [/^(exito|logr|meta|objetivo|ganador)/, "🏆"],
  [/^(crec|subir|aument|mas)$/, "📈"],
  [/^(gratis|regalo)/, "🎁"],
  [/^(pensar|piensa|mente|cerebro)/, "🧠"],
  [/^(risa|gracioso|jaja)/, "😂"],
  [/^(mira|ojo|atencion)/, "👀"],
  [/^(musculo|fuerza|gym|entren)/, "💪"],
  [/^(cohete|lanz|empez)/, "🚀"],
];

/** Palabras que suelen marcar un momento de énfasis. */
const EMPHASIS = /^(nunca|siempre|nadie|todo|importante|secreto|clave|gratis|increible|brutal|mira|ojo|atencion|verdad|error)/;

const MIN_GAP = 2.5;

function normalize(text: string) {
  return text.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-zñ]/g, "");
}

/** Elige momentos destacados sin IA: palabras enfáticas, exclamaciones y palabras con emoji asociado. */
export function heuristicHighlights(words: Word[]): Highlight[] {
  const out: Highlight[] = [];
  let lastZoom = -Infinity;
  let lastEmoji = -Infinity;
  for (const w of words) {
    const n = normalize(w.text);
    const emoji = EMOJIS.find(([re]) => re.test(n))?.[1];
    const zoom = (EMPHASIS.test(n) || /!$/.test(w.text)) && w.start - lastZoom >= MIN_GAP;
    const withEmoji = emoji && w.start - lastEmoji >= MIN_GAP ? emoji : undefined;
    if (zoom) lastZoom = w.start;
    if (withEmoji) lastEmoji = w.start;
    if (zoom || withEmoji) out.push({ time: w.start, zoom, emoji: withEmoji });
  }
  return out;
}

/** Espacia los destacados que devuelve el LLM para que no se amontonen. */
export function spaceOut(highlights: Highlight[]): Highlight[] {
  const sorted = [...highlights].sort((a, b) => a.time - b.time);
  const out: Highlight[] = [];
  for (const h of sorted) {
    const prev = out[out.length - 1];
    if (!prev || h.time - prev.time >= MIN_GAP) out.push(h);
  }
  return out;
}

const ZOOM_IN = 0.12;
const ZOOM_HOLD = 0.9;
const ZOOM_OUT = 0.35;
const ZOOM_AMOUNT = 0.18;

/** Factor de zoom (≥ 1) en el instante t: entrada rápida, pausa y salida suave. */
export function zoomAt(highlights: Highlight[], t: number): number {
  for (const h of highlights) {
    if (!h.zoom) continue;
    const dt = t - h.time;
    if (dt < 0 || dt > ZOOM_IN + ZOOM_HOLD + ZOOM_OUT) continue;
    let k: number;
    if (dt < ZOOM_IN) k = easeOut(dt / ZOOM_IN);
    else if (dt < ZOOM_IN + ZOOM_HOLD) k = 1;
    else k = 1 - easeInOut((dt - ZOOM_IN - ZOOM_HOLD) / ZOOM_OUT);
    return 1 + ZOOM_AMOUNT * k;
  }
  return 1;
}

const EMOJI_DURATION = 1.3;

/** Emoji visible en t y su progreso (0–1) para animarlo. */
export function emojiAt(highlights: Highlight[], t: number): { emoji: string; progress: number } | undefined {
  const h = highlights.find((h) => h.emoji && t >= h.time && t < h.time + EMOJI_DURATION);
  return h && { emoji: h.emoji!, progress: (t - h.time) / EMOJI_DURATION };
}

const easeOut = (x: number) => 1 - (1 - x) ** 3;
const easeInOut = (x: number) => (x < 0.5 ? 4 * x ** 3 : 1 - (-2 * x + 2) ** 3 / 2);
