import {
  ALL_FORMATS,
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
  type VideoCodec,
} from "mediabunny";
import { mixSfx, type SfxEvent } from "./sfx";
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
};

/**
 * Exporta el montaje a MP4 con WebCodecs, fotograma a fotograma y sin reproducir el video,
 * así que va más rápido que el tiempo real. Devuelve null si el navegador no puede codificar
 * ningún formato compatible (y hay que usar la exportación en tiempo real).
 */
export async function exportFast(file: File, options: Options) {
  const { width, height } = options;
  if (typeof VideoEncoder === "undefined") return null;
  const format = new Mp4OutputFormat({ fastStart: "in-memory" });
  const videoCodec = await getFirstEncodableVideoCodec(format.getSupportedVideoCodecs(), { width, height });
  if (!videoCodec) return null;

  const input = new Input({ source: new BlobSource(file), formats: ALL_FORMATS });
  try {
    return await encode(input, file, format, videoCodec, options);
  } finally {
    input.dispose();
  }
}

async function encode(
  input: Input,
  file: File,
  format: Mp4OutputFormat,
  videoCodec: VideoCodec,
  { segments, width, height, fps = 30, draw, onProgress, sfx }: Options,
) {
  const videoTrack = await input.getPrimaryVideoTrack();
  if (!videoTrack || !(await videoTrack.canDecode())) return null;

  const output = new Output({ format, target: new BufferTarget() });
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d")!;
  const videoSource = new CanvasSource(canvas, { codec: videoCodec, bitrate: QUALITY_HIGH });
  output.addVideoTrack(videoSource, { frameRate: fps });

  // Nº de fotogramas de cada tramo: el audio se corta con la misma duración para que no se desincronice.
  const frameCounts = segments.map((s) => Math.max(1, Math.round((s.end - s.start) * fps)));
  const totalFrames = frameCounts.reduce((a, b) => a + b, 0);

  let audio = await editedAudio(file, segments, frameCounts, fps);
  if (sfx?.events.length) {
    // Sin audio en el video, los efectos van sobre silencio.
    audio ??= new AudioBuffer({ length: Math.round((totalFrames / fps) * 48000), numberOfChannels: 2, sampleRate: 48000 });
    await mixSfx(audio, sfx.events, segments, sfx.volume);
  }
  const audioCodec = audio && (await getFirstEncodableAudioCodec(format.getSupportedAudioCodecs()));
  const audioSource = audioCodec ? new AudioBufferSource({ codec: audioCodec, bitrate: QUALITY_HIGH }) : null;
  if (audioSource) output.addAudioTrack(audioSource);

  await output.start();

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
    if (i % 10 === 0) onProgress?.(i / totalFrames);
  }

  if (audioSource && audio) await audioSource.add(audio);
  await output.finalize();
  onProgress?.(1);
  return new Blob([output.target.buffer!], { type: format.mimeType });
}

/** Decodifica el audio y concatena solo los tramos conservados. Null si el video no tiene audio. */
async function editedAudio(file: File, segments: Segment[], frameCounts: number[], fps: number) {
  const ctx = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await ctx.decodeAudioData(await file.arrayBuffer());
  } catch {
    return null;
  } finally {
    await ctx.close();
  }
  const sr = decoded.sampleRate;
  const lengths = frameCounts.map((n) => Math.round((n / fps) * sr));
  const out = new AudioBuffer({
    length: lengths.reduce((a, b) => a + b, 0),
    numberOfChannels: decoded.numberOfChannels,
    sampleRate: sr,
  });
  for (let c = 0; c < decoded.numberOfChannels; c++) {
    const src = decoded.getChannelData(c);
    const dst = out.getChannelData(c);
    let offset = 0;
    segments.forEach((s, i) => {
      const from = Math.round(s.start * sr);
      dst.set(src.subarray(from, Math.min(src.length, from + lengths[i])), offset);
      offset += lengths[i];
    });
  }
  return out;
}
