import { encodeWav, SAMPLE_RATE } from "./audio";
import type { Segment, Word } from "./types";
import { transcribeBlockInBrowser } from "./whisper";

/** Bloques de como mucho 2 minutos: así el WAV de cada uno (~3,8 MB) cabe en el límite de Vercel (4,5 MB). */
const MAX_BLOCK = 120;
const MIN_BLOCK = 30;

/**
 * Divide el audio en bloques, cortando en mitad de un silencio para no partir palabras.
 * Si hay más de 2 minutos de voz seguida, corta a los 2 minutos.
 */
export function planBlocks(duration: number, speech: Segment[]): Segment[] {
  const pauses = speech.slice(1).map((s, i) => (speech[i].end + s.start) / 2);
  const blocks: Segment[] = [];
  let start = 0;
  while (duration - start > 0.01) {
    const limit = start + MAX_BLOCK;
    let end = duration;
    if (limit < duration) {
      const pause = pauses.filter((p) => p > start + MIN_BLOCK && p <= limit).pop();
      end = pause ?? limit;
    }
    blocks.push({ start, end });
    start = end;
  }
  return blocks;
}

/**
 * Transcribe el audio completo por bloques: con Whisper de OpenAI en el servidor si está configurado
 * y, si no, con Whisper en el navegador. Las marcas de tiempo se devuelven respecto al video.
 */
export async function transcribe(
  audio: Float32Array,
  speech: Segment[],
  { language, onStatus }: { language: string; onStatus: (s: string) => void },
): Promise<Word[]> {
  const duration = audio.length / SAMPLE_RATE;
  const blocks = planBlocks(duration, speech);
  let useServer = true;
  const words: Word[] = [];

  for (const [i, block] of blocks.entries()) {
    const label = blocks.length > 1 ? ` (bloque ${i + 1} de ${blocks.length})` : "";
    const samples = audio.subarray(Math.floor(block.start * SAMPLE_RATE), Math.floor(block.end * SAMPLE_RATE));
    let blockWords: Word[] | null = null;

    if (useServer) {
      onStatus(`Transcribiendo${label}…`);
      blockWords = await transcribeOnServer(samples);
      if (!blockWords) useServer = false;
    }
    if (!blockWords) {
      onStatus(`Transcribiendo en tu navegador${label}…`);
      blockWords = await transcribeBlockInBrowser(samples, language, (p) =>
        onStatus(`Descargando el modelo de transcripción (solo la primera vez)… ${Math.round(p * 100)} %`),
      );
    }
    words.push(...blockWords.map((w) => ({ ...w, start: w.start + block.start, end: w.end + block.start })));
  }
  return words;
}

/** Whisper de OpenAI vía /api/transcribe. Devuelve null si el servidor no tiene clave. */
async function transcribeOnServer(samples: Float32Array): Promise<Word[] | null> {
  const body = new FormData();
  body.append("file", encodeWav(samples), "audio.wav");
  const res = await fetch("/api/transcribe", { method: "POST", body });
  if (res.status === 501) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? `Error ${res.status} al transcribir`);
  return data.words as Word[];
}
