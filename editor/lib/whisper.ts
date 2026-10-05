import type { Word } from "./types";

export type WhisperRequest = { audio: Float32Array; language: string };
export type WhisperResponse =
  | { type: "download"; progress: number }
  | { type: "transcribing" }
  | { type: "result"; words: Word[] }
  | { type: "error"; message: string };

let worker: Worker | null = null;

/**
 * Transcribe un bloque de audio (mono, 16 kHz) en el navegador con Whisper (Transformers.js).
 * Hay que indicar el idioma: sin él, Transformers.js asume inglés.
 */
export function transcribeBlockInBrowser(
  audio: Float32Array,
  language: string,
  onDownload?: (progress: number) => void,
): Promise<Word[]> {
  worker ??= new Worker(new URL("./whisper.worker.ts", import.meta.url), { type: "module" });
  const w = worker;
  return new Promise((resolve, reject) => {
    w.onmessage = (e: MessageEvent<WhisperResponse>) => {
      const msg = e.data;
      if (msg.type === "download") onDownload?.(msg.progress);
      else if (msg.type === "result") resolve(msg.words);
      else if (msg.type === "error") reject(new Error(msg.message));
    };
    // Se envía una copia: el bloque es una vista del audio completo, que se sigue usando.
    const copy = audio.slice();
    w.postMessage({ audio: copy, language } satisfies WhisperRequest, [copy.buffer]);
  });
}
