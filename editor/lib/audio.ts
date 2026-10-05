import { ALL_FORMATS, AudioBufferSink, BlobSource, Input } from "mediabunny";

export const SAMPLE_RATE = 16000;

/**
 * Extrae el audio del video en mono a 16 kHz (lo que necesitan Whisper y la detección de silencios).
 * Lo decodifica por trozos con WebCodecs, así que un video largo no se carga entero en memoria:
 * 30 minutos ocupan ~115 MB. Sin WebCodecs, usa decodeAudioData (que sí carga el archivo entero).
 */
export async function extractAudio16k(file: File, onProgress?: (p: number) => void): Promise<Float32Array> {
  const input = new Input({ source: new BlobSource(file), formats: ALL_FORMATS });
  try {
    const track = await input.getPrimaryAudioTrack();
    if (!track) return new Float32Array(0);
    if (typeof AudioDecoder === "undefined" || !(await track.canDecode())) return await decodeWhole(file);

    const duration = await track.computeDuration();
    const out = new Float32Array(Math.ceil(duration * SAMPLE_RATE) + SAMPLE_RATE);
    let written = 0;
    let carry = new Float32Array(0);
    for await (const { buffer, timestamp } of new AudioBufferSink(track).buffers()) {
      const ratio = buffer.sampleRate / SAMPLE_RATE;
      const mono = concat(carry, toMono(buffer));
      // Promedia cada grupo de `ratio` muestras: diezmado con un filtro paso bajo sencillo.
      const n = Math.floor(mono.length / ratio);
      for (let j = 0; j < n && written < out.length; j++) {
        const a = Math.floor(j * ratio);
        const b = Math.max(a + 1, Math.floor((j + 1) * ratio));
        let sum = 0;
        for (let k = a; k < b; k++) sum += mono[k];
        out[written++] = sum / (b - a);
      }
      carry = mono.slice(Math.floor(n * ratio));
      onProgress?.(Math.min(1, (timestamp + buffer.duration) / duration));
    }
    return out.subarray(0, written);
  } finally {
    input.dispose();
  }
}

function toMono(buf: AudioBuffer): Float32Array {
  if (buf.numberOfChannels === 1) return buf.getChannelData(0);
  const out = new Float32Array(buf.length);
  for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < out.length; i++) out[i] += d[i] / buf.numberOfChannels;
  }
  return out;
}

function concat(a: Float32Array, b: Float32Array): Float32Array {
  if (!a.length) return b;
  const out = new Float32Array(a.length + b.length);
  out.set(a);
  out.set(b, a.length);
  return out;
}

async function decodeWhole(file: File): Promise<Float32Array> {
  const ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
  try {
    return toMono(await ctx.decodeAudioData(await file.arrayBuffer())).slice();
  } finally {
    await ctx.close();
  }
}

/** Codifica audio mono a WAV de 16 bits (para enviarlo al servidor). */
export function encodeWav(samples: Float32Array, sampleRate = SAMPLE_RATE): Blob {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const str = (o: number, s: string) => [...s].forEach((ch, i) => view.setUint8(o + i, ch.charCodeAt(0)));
  str(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVE");
  str(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  str(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([view.buffer], { type: "audio/wav" });
}
