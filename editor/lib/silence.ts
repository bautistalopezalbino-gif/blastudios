import type { Segment } from "./types";

type Options = {
  /** Volumen (RMS) por debajo del cual se considera silencio. */
  threshold?: number;
  /** Duración mínima de una pausa para recortarla, en segundos. */
  minSilence?: number;
  /** Margen que se deja antes y después de la voz, en segundos. */
  padding?: number;
};

/** Decodifica el audio del archivo y devuelve los tramos con voz. */
export async function detectSpeechSegments(
  file: File,
  { threshold = 0.02, minSilence = 0.4, padding = 0.1 }: Options = {},
): Promise<Segment[]> {
  const ctx = new AudioContext();
  const audio = await ctx.decodeAudioData(await file.arrayBuffer());
  await ctx.close();

  const data = audio.getChannelData(0);
  const windowSize = Math.floor(audio.sampleRate * 0.02);
  const windowSec = windowSize / audio.sampleRate;

  const loud: Segment[] = [];
  let current: Segment | null = null;
  for (let i = 0; i < data.length; i += windowSize) {
    let sum = 0;
    const end = Math.min(i + windowSize, data.length);
    for (let j = i; j < end; j++) sum += data[j] * data[j];
    const rms = Math.sqrt(sum / (end - i));
    const t = i / audio.sampleRate;
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
      end: Math.min(audio.duration, s.end + padding),
    };
    const last = merged[merged.length - 1];
    if (last && padded.start <= last.end) last.end = Math.max(last.end, padded.end);
    else merged.push(padded);
  }
  return merged.length ? merged : [{ start: 0, end: audio.duration }];
}
