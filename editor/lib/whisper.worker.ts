/// <reference lib="webworker" />
import { pipeline, type AutomaticSpeechRecognitionPipeline } from "@huggingface/transformers";
import type { Word } from "./types";
import type { WhisperRequest, WhisperResponse } from "./whisper";

type Chunk = { text: string; timestamp: [number, number | null] };

// Whisper base con marcas de tiempo por palabra, ~77 MB cuantizado. Se descarga una vez y queda en caché.
const MODEL = "onnx-community/whisper-base_timestamped";

let asr: Promise<AutomaticSpeechRecognitionPipeline> | null = null;
const loaded = new Map<string, { loaded: number; total: number }>();

const post = (msg: WhisperResponse) => self.postMessage(msg);

function load() {
  asr ??= (async () => {
    const gpu = (navigator as Navigator & { gpu?: { requestAdapter(): Promise<unknown> } }).gpu;
    const webgpu = !!(gpu && (await gpu.requestAdapter().catch(() => null)));
    return pipeline("automatic-speech-recognition", MODEL, {
      device: webgpu ? "webgpu" : "wasm",
      dtype: webgpu ? { encoder_model: "fp32", decoder_model_merged: "q4" } : "q8",
      progress_callback: (p) => {
        if (p.status !== "progress") return;
        loaded.set(p.file, { loaded: p.loaded, total: p.total });
        const all = [...loaded.values()];
        post({
          type: "download",
          progress: all.reduce((a, f) => a + f.loaded, 0) / Math.max(1, all.reduce((a, f) => a + f.total, 0)),
        });
      },
    }) as Promise<AutomaticSpeechRecognitionPipeline>;
  })();
  return asr;
}

self.onmessage = async (e: MessageEvent<WhisperRequest>) => {
  try {
    const transcriber = await load();
    post({ type: "transcribing" });
    const out = await transcriber(e.data.audio, {
      return_timestamps: "word",
      chunk_length_s: 30,
      stride_length_s: 5,
      language: e.data.language,
      task: "transcribe",
    });
    const chunks = ((Array.isArray(out) ? out[0] : out).chunks ?? []) as Chunk[];
    post({
      type: "result",
      words: chunks
        .map((c) => ({
          text: c.text.trim(),
          start: c.timestamp[0],
          end: c.timestamp[1] ?? c.timestamp[0] + 0.3,
        }))
        .filter((w: Word) => w.text),
    });
  } catch (err) {
    asr = null;
    post({ type: "error", message: (err as Error).message });
  }
};
