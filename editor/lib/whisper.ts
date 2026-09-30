import type { Word } from "./types";

export type WhisperRequest = { audio: Float32Array; language: string };
export type WhisperResponse =
  | { type: "download"; progress: number }
  | { type: "transcribing" }
  | { type: "result"; words: Word[] }
  | { type: "error"; message: string };

let worker: Worker | null = null;

/**
 * Transcribe en el navegador con Whisper (Transformers.js), sin servidor ni clave.
 * Hay que indicar el idioma: sin él, Transformers.js asume inglés.
 */
export async function transcribeInBrowser(
  file: File,
  { language = "spanish", onStatus }: { language?: string; onStatus?: (s: string) => void } = {},
): Promise<Word[]> {
  const audio = await decodeMono16k(file);
  worker ??= new Worker(new URL("./whisper.worker.ts", import.meta.url), { type: "module" });
  const w = worker;
  return new Promise((resolve, reject) => {
    w.onmessage = (e: MessageEvent<WhisperResponse>) => {
      const msg = e.data;
      if (msg.type === "download")
        onStatus?.(`Descargando el modelo de transcripción (solo la primera vez)… ${Math.round(msg.progress * 100)} %`);
      else if (msg.type === "transcribing") onStatus?.("Transcribiendo en tu navegador…");
      else if (msg.type === "result") resolve(msg.words);
      else reject(new Error(msg.message));
    };
    w.postMessage({ audio, language } satisfies WhisperRequest, [audio.buffer]);
  });
}

/** Whisper espera audio mono a 16 kHz. */
async function decodeMono16k(file: File): Promise<Float32Array> {
  const ctx = new AudioContext({ sampleRate: 16000 });
  try {
    const buf = await ctx.decodeAudioData(await file.arrayBuffer());
    if (buf.numberOfChannels === 1) return buf.getChannelData(0).slice();
    const out = new Float32Array(buf.length);
    for (let c = 0; c < buf.numberOfChannels; c++) {
      const data = buf.getChannelData(c);
      for (let i = 0; i < out.length; i++) out[i] += data[i] / buf.numberOfChannels;
    }
    return out;
  } finally {
    await ctx.close();
  }
}
