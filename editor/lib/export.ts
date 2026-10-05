import {
  ALL_FORMATS,
  AudioBufferSink,
  AudioBufferSource,
  BlobSource,
  BufferTarget,
  CanvasSink,
  CanvasSource,
  getFirstEncodableAudioCodec,
  getFirstEncodableVideoCodec,
  Input,
  Mp4OutputFormat,
  Output,
  QUALITY_HIGH,
  StreamTarget,
  type StreamTargetChunk,
  type VideoCodec,
} from "mediabunny";
import { renderSfx, type SfxEvent } from "./sfx";
import type { Segment } from "./types";

export type SourceFrame = { image: CanvasImageSource; width: number; height: number };

type Options = {
  segments: Segment[];
  width: number;
  height: number;
  fps?: number;
  /** Dibuja el fotograma de salida a partir del fotograma original en el instante `t` (del original). */
  draw: (ctx: CanvasRenderingContext2D, frame: SourceFrame, t: number) => void;
  onProgress?: (p: number) => void;
  /** Efectos de sonido que se mezclan con el audio. */
  sfx?: { events: SfxEvent[]; volume: number };
  /** Archivo en disco donde escribir el MP4 (videos largos); si no, se genera en memoria. */
  saveTo?: FileSystemWritableFileStream;
};

/**
 * Exporta el montaje a MP4 con WebCodecs, fotograma a fotograma y sin reproducir el video,
 * así que va más rápido que el tiempo real. El audio se decodifica y se codifica por trozos, intercalado
 * con el video, y con `saveTo` el resultado va directo a disco: la memoria no crece con la duración.
 * Devuelve el MP4 (o "saved" si se escribió en `saveTo`), o null si el navegador no puede codificar
 * ningún formato compatible (y hay que usar la exportación en tiempo real).
 */
export async function exportFast(file: File, options: Options): Promise<Blob | "saved" | null> {
  const { width, height, saveTo } = options;
  if (typeof VideoEncoder === "undefined") return null;
  const format = new Mp4OutputFormat({ fastStart: saveTo ? false : "in-memory" });
  const videoCodec = await getFirstEncodableVideoCodec(format.getSupportedVideoCodecs(), { width, height });
  if (!videoCodec) return null;

  const input = new Input({ source: new BlobSource(file), formats: ALL_FORMATS });
  try {
    return await encode(input, format, videoCodec, options);
  } finally {
    input.dispose();
  }
}

async function encode(
  input: Input,
  format: Mp4OutputFormat,
  videoCodec: VideoCodec,
  { segments, width, height, fps = 30, draw, onProgress, sfx, saveTo }: Options,
): Promise<Blob | "saved" | null> {
  const videoTrack = await input.getPrimaryVideoTrack();
  if (!videoTrack || !(await videoTrack.canDecode())) return null;

  const target = saveTo
    ? new StreamTarget(saveTo as unknown as WritableStream<StreamTargetChunk>, { chunked: true })
    : new BufferTarget();
  const output = new Output({ format, target });
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d")!;
  const videoSource = new CanvasSource(canvas, { codec: videoCodec, bitrate: QUALITY_HIGH });
  output.addVideoTrack(videoSource, { frameRate: fps });

  // Nº de fotogramas de cada tramo: el audio se corta con la misma duración para que no se desincronice.
  const frameCounts = segments.map((s) => Math.max(1, Math.round((s.end - s.start) * fps)));
  const totalFrames = frameCounts.reduce((a, b) => a + b, 0);

  const audio = await editedAudio(input, segments, frameCounts, fps, sfx);
  const audioCodec = audio && (await getFirstEncodableAudioCodec(format.getSupportedAudioCodecs()));
  const audioSource = audioCodec ? new AudioBufferSource({ codec: audioCodec, bitrate: QUALITY_HIGH }) : null;
  if (audioSource) output.addAudioTrack(audioSource);

  await output.start();

  // El audio se añade a la par que el video: si se añadiera al final, el MP4 tendría que guardar todo el video en memoria.
  let audioIter = audioSource && audio ? audio[Symbol.asyncIterator]() : null;
  let audioTime = 0;
  const feedAudioUntil = async (t: number) => {
    while (audioIter && audioTime < t) {
      const next = await audioIter.next();
      if (next.done) {
        audioIter = null;
        break;
      }
      await audioSource!.add(next.value);
      audioTime += next.value.duration;
    }
  };

  const timestamps = segments.flatMap((s, i) =>
    Array.from({ length: frameCounts[i] }, (_, k) => s.start + k / fps),
  );
  const sink = new CanvasSink(videoTrack, { poolSize: 2 });
  let i = 0;
  let last: SourceFrame | null = null;
  for await (const wrapped of sink.canvasesAtTimestamps(timestamps)) {
    if (wrapped) last = { image: wrapped.canvas, width: wrapped.canvas.width, height: wrapped.canvas.height };
    if (last) draw(ctx, last, timestamps[i]);
    await videoSource.add(i / fps, 1 / fps);
    i++;
    await feedAudioUntil(i / fps + 0.5);
    if (i % 10 === 0) onProgress?.(i / totalFrames);
  }
  await feedAudioUntil(Infinity);

  await output.finalize();
  onProgress?.(1);
  if (target instanceof BufferTarget) return new Blob([target.buffer!], { type: format.mimeType });
  return "saved";
}

/**
 * Audio del montaje en trozos de ~1 s: solo los tramos conservados, con los efectos de sonido mezclados.
 * Null si el video no tiene audio (o no se puede decodificar) y no hay efectos.
 */
async function editedAudio(
  input: Input,
  segments: Segment[],
  frameCounts: number[],
  fps: number,
  sfx: Options["sfx"],
): Promise<AsyncIterable<AudioBuffer> | null> {
  const track = await input.getPrimaryAudioTrack();
  const decodable = !!track && typeof AudioDecoder !== "undefined" && (await track.canDecode());
  const events = sfx?.events ?? [];
  if (!decodable && !events.length) return null;

  const sr = decodable ? track!.sampleRate : 48000;
  const channels = decodable ? Math.min(2, track!.numberOfChannels) : 2;
  const lengths = frameCounts.map((n) => Math.round((n / fps) * sr));

  // Efectos colocados en su muestra de salida (con la misma regla de tramos que el video).
  const segStarts: number[] = [];
  lengths.reduce((acc, n) => (segStarts.push(acc), acc + n), 0);
  const placed: { at: number; buffer: AudioBuffer }[] = [];
  for (const e of events) {
    const k = segments.findIndex((s) => e.time >= s.start && e.time < s.end);
    if (k === -1) continue;
    placed.push({ at: segStarts[k] + Math.round((e.time - segments[k].start) * sr), buffer: await renderSfx(e.kind, sr) });
  }

  const sink = decodable ? new AudioBufferSink(track!) : null;
  const volume = sfx?.volume ?? 0;

  async function* chunks(): AsyncGenerator<AudioBuffer> {
    const writer = new ChunkWriter(channels, sr, placed, volume);
    for (const [k, seg] of segments.entries()) {
      const need = lengths[k];
      let filled = 0;
      if (sink) {
        for await (const { buffer, timestamp } of sink.buffers(seg.start, seg.start + need / sr + 0.05)) {
          const offset = Math.round((timestamp - seg.start) * sr);
          for (let j = Math.max(0, -offset, filled - offset); j < buffer.length && offset + j < need; ) {
            // Rellena con silencio si hay un hueco entre trozos de audio.
            if (offset + j > filled) {
              yield* writer.silence(offset + j - filled);
              filled = offset + j;
            }
            const n = Math.min(buffer.length - j, need - filled);
            yield* writer.write(buffer, j, n);
            filled += n;
            j += n;
          }
          if (filled >= need) break;
        }
      }
      yield* writer.silence(need - filled);
    }
    yield* writer.flush();
  }
  return chunks();
}

/** Acumula muestras en trozos de 1 s, mezcla los efectos que caen en cada trozo y los entrega como AudioBuffer. */
class ChunkWriter {
  private data: Float32Array[];
  private used = 0;
  private position = 0;

  constructor(
    private channels: number,
    private sr: number,
    private sfx: { at: number; buffer: AudioBuffer }[],
    private volume: number,
  ) {
    this.data = Array.from({ length: channels }, () => new Float32Array(sr));
  }

  *write(src: AudioBuffer, from: number, count: number): Generator<AudioBuffer> {
    while (count > 0) {
      const n = Math.min(count, this.sr - this.used);
      for (let c = 0; c < this.channels; c++) {
        const ch = src.getChannelData(Math.min(c, src.numberOfChannels - 1));
        this.data[c].set(ch.subarray(from, from + n), this.used);
      }
      this.used += n;
      from += n;
      count -= n;
      if (this.used === this.sr) yield this.emit();
    }
  }

  *silence(count: number): Generator<AudioBuffer> {
    while (count > 0) {
      const n = Math.min(count, this.sr - this.used);
      for (const d of this.data) d.fill(0, this.used, this.used + n);
      this.used += n;
      count -= n;
      if (this.used === this.sr) yield this.emit();
    }
  }

  *flush(): Generator<AudioBuffer> {
    if (this.used > 0) yield this.emit();
  }

  private emit(): AudioBuffer {
    const len = this.used;
    const out = new AudioBuffer({ length: len, numberOfChannels: this.channels, sampleRate: this.sr });
    for (let c = 0; c < this.channels; c++) {
      const dst = this.data[c].slice(0, len);
      for (const { at, buffer } of this.sfx) {
        const src = buffer.getChannelData(Math.min(c, buffer.numberOfChannels - 1));
        const from = Math.max(0, this.position - at);
        const to = Math.min(src.length, this.position + len - at);
        for (let i = from; i < to; i++) {
          const v = dst[at + i - this.position] + src[i] * this.volume;
          dst[at + i - this.position] = v > 1 ? 1 : v < -1 ? -1 : v;
        }
      }
      out.copyToChannel(dst, c);
    }
    this.position += len;
    this.used = 0;
    return out;
  }
}
