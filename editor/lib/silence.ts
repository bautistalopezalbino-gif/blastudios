import type { Segment } from "./types";

type Options = {
  /** Volumen (RMS) por debajo del cual se considera silencio. */
  threshold?: number;
  /** Duración mínima de una pausa para recortarla, en segundos. */
  minSilence?: number;
  /** Margen que se deja antes y después de la voz, en segundos. */
  padding?: number;
};

/** Devuelve los tramos con voz a partir del audio mono (ver extractAudio16k). */
export function detectSpeechSegments(
  data: Float32Array,
  sampleRate: number,
  { threshold = 0.02, minSilence = 0.4, padding = 0.1 }: Options = {},
): Segment[] {
  const duration = data.length / sampleRate;
  const windowSize = Math.floor(sampleRate * 0.02);
  const windowSec = windowSize / sampleRate;

  const loud: Segment[] = [];
  let current: Segment | null = null;
  for (let i = 0; i < data.length; i += windowSize) {
    let sum = 0;
    const end = Math.min(i + windowSize, data.length);
    for (let j = i; j < end; j++) sum += data[j] * data[j];
    const rms = Math.sqrt(sum / (end - i));
    const t = i / sampleRate;
    if (rms >= threshold) {
      if (current) current.end = t + windowSec;
      else current = { start: t, end: t + windowSec };
    } else if (current && t - current.end >= minSilence) {
      loud.push(current);
      current = null;
    }
  }
  if (current) loud.push(current);

  // Añade margen y fusiona tramos que se solapan.
  const merged: Segment[] = [];
  for (const s of loud) {
    const padded = {
      start: Math.max(0, s.start - padding),
      end: Math.min(duration, s.end + padding),
    };
    const last = merged[merged.length - 1];
    if (last && padded.start <= last.end) last.end = Math.max(last.end, padded.end);
    else merged.push(padded);
  }
  return merged.length ? merged : [{ start: 0, end: duration }];
}
