import { wordScore } from "./highlights";
import type { Word } from "./types";

export type Clip = { start: number; end: number; title: string; reason: string; score: number };
export type ClipOptions = { min: number; max: number; count: number };
export type Sentence = { start: number; end: number; text: string };
/** Lo que devuelve el LLM: índices de frase, inclusive. */
export type ClipCandidate = { start: number; end: number; title?: string; reason?: string; score?: number };

/** Agrupa las palabras en frases: corta en puntuación final, en pausas largas o cada 30 palabras. */
export function toSentences(words: Word[]): Sentence[] {
  const out: Sentence[] = [];
  let current: Word[] = [];
  const close = () => {
    if (!current.length) return;
    out.push({ start: current[0].start, end: current[current.length - 1].end, text: current.map((w) => w.text).join(" ") });
    current = [];
  };
  words.forEach((w, i) => {
    current.push(w);
    const next = words[i + 1];
    if (/[.!?…]$/.test(w.text) || (next && next.start - w.end > 0.8) || current.length >= 30) close();
  });
  close();
  return out;
}

/** Margen antes y después del clip, para que no empiece ni acabe en seco. */
const PAD_BEFORE = 0.15;
const PAD_AFTER = 0.35;

/**
 * Convierte candidatos (índices de frase) en clips válidos: dentro de la duración pedida
 * (con algo de tolerancia), sin solaparse y ordenados de mayor a menor puntuación.
 */
export function finalizeClips(candidates: ClipCandidate[], sentences: Sentence[], { min, max, count }: ClipOptions): Clip[] {
  const valid = candidates
    .filter((c) => sentences[c.start] && sentences[c.end] && c.end >= c.start)
    .map((c) => ({
      start: Math.max(0, sentences[c.start].start - PAD_BEFORE),
      end: sentences[c.end].end + PAD_AFTER,
      title: (c.title || sentences[c.start].text).slice(0, 80),
      reason: c.reason ?? "",
      score: Math.round(c.score ?? 50),
    }))
    .filter((c) => c.end - c.start >= min * 0.7 && c.end - c.start <= max * 1.3)
    .sort((a, b) => b.score - a.score);
  const chosen: Clip[] = [];
  for (const c of valid) {
    if (chosen.length >= count) break;
    if (chosen.every((o) => c.end <= o.start || c.start >= o.end)) chosen.push(c);
  }
  return chosen;
}

/**
 * Elige clips sin IA: ventanas de frases seguidas con la duración pedida, puntuadas por palabras
 * de énfasis, preguntas, exclamaciones y cifras; con un extra si la primera frase engancha.
 */
export function heuristicClips(sentences: Sentence[], opts: ClipOptions): Clip[] {
  const target = (opts.min + opts.max) / 2;
  const scores = sentences.map((s) => s.text.split(/\s+/).reduce((a, w) => a + wordScore(w), 0));
  const candidates: ClipCandidate[] = [];
  for (let i = 0; i < sentences.length; i++) {
    let j = i;
    while (j + 1 < sentences.length && sentences[j].end - sentences[i].start < target) j++;
    const dur = sentences[j].end - sentences[i].start;
    if (dur < opts.min || dur > opts.max) continue;
    let score = 0;
    for (let k = i; k <= j; k++) score += scores[k];
    const hook = /[?¿!¡]/.test(sentences[i].text) || scores[i] >= 1 ? 1.5 : 1;
    candidates.push({
      start: i,
      end: j,
      // Puntos de interés por segundo; se pasa a escala 1–99 más abajo.
      score: (score / dur) * hook,
      reason: hook > 1 ? "Empieza con gancho y tiene frases con énfasis" : "Tramo con frases con énfasis",
    });
  }
  // Puntuación relativa al mejor tramo del video: el mejor saca 99.
  const best = Math.max(...candidates.map((c) => c.score!), 1e-9);
  for (const c of candidates) c.score = Math.max(1, Math.round((c.score! / best) * 99));
  return finalizeClips(candidates, sentences, opts);
}
