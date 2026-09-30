import type { Segment, Word } from "./types";

export function editedDuration(segments: Segment[]): number {
  return segments.reduce((acc, s) => acc + (s.end - s.start), 0);
}

/** Índice del tramo que contiene el instante t del original, o -1 si cae en un corte. */
export function segmentAt(segments: Segment[], t: number): number {
  return segments.findIndex((s) => t >= s.start && t < s.end);
}

/** Agrupa palabras en frases cortas para los subtítulos (estilo TikTok: 3 palabras). */
export function groupWords(words: Word[], maxWords = 3): Word[][] {
  const groups: Word[][] = [];
  let current: Word[] = [];
  for (const w of words) {
    current.push(w);
    const endsSentence = /[.!?,]$/.test(w.text);
    if (current.length >= maxWords || endsSentence) {
      groups.push(current);
      current = [];
    }
  }
  if (current.length) groups.push(current);
  return groups;
}

export function groupAt(groups: Word[][], t: number): Word[] | undefined {
  return groups.find((g) => t >= g[0].start && t <= g[g.length - 1].end + 0.15);
}
