import type { Highlight, Segment } from "./types";

/**
 * Efectos de sonido generados con Web Audio (sin archivos ni licencias):
 * "whoosh" antes de cada zoom y "pop" al aparecer cada emoji.
 */
export type SfxKind = "whoosh" | "pop";
export type SfxEvent = { time: number; kind: SfxKind };

/** El whoosh empieza un poco antes del zoom para que suene como la entrada. */
const WHOOSH_LEAD = 0.18;

/** Efectos de los destacados que caen en tramos conservados, en tiempo del original. */
export function sfxEvents(highlights: Highlight[], segments: Segment[]): SfxEvent[] {
  const events: SfxEvent[] = [];
  for (const h of highlights) {
    const seg = segments.find((s) => h.time >= s.start && h.time < s.end);
    if (!seg) continue;
    // Si la anticipación del whoosh cae en un corte, empieza al principio del tramo del zoom.
    if (h.zoom) events.push({ time: Math.max(seg.start, h.time - WHOOSH_LEAD), kind: "whoosh" });
    if (h.emoji) events.push({ time: h.time, kind: "pop" });
  }
  return events.sort((a, b) => a.time - b.time);
}

const cache = new Map<string, Promise<AudioBuffer>>();

/** Genera (y guarda en caché) el sonido a la frecuencia de muestreo indicada. */
export function renderSfx(kind: SfxKind, sampleRate: number): Promise<AudioBuffer> {
  const key = `${kind}@${sampleRate}`;
  let buf = cache.get(key);
  if (!buf) {
    buf = (kind === "whoosh" ? renderWhoosh(sampleRate) : renderPop(sampleRate)).then(normalize);
    cache.set(key, buf);
  }
  return buf;
}

/** Lleva el pico a 0,9 para que todos los efectos suenen a un volumen parecido. */
function normalize(buf: AudioBuffer) {
  let peak = 0;
  for (let c = 0; c < buf.numberOfChannels; c++) for (const x of buf.getChannelData(c)) peak = Math.max(peak, Math.abs(x));
  if (peak > 0) for (let c = 0; c < buf.numberOfChannels; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < d.length; i++) d[i] *= 0.9 / peak;
  }
  return buf;
}

/** Ruido filtrado con un barrido de frecuencia que sube y baja. */
function renderWhoosh(sampleRate: number) {
  const duration = 0.5;
  const ctx = new OfflineAudioContext(2, Math.ceil(duration * sampleRate), sampleRate);
  const noise = ctx.createBuffer(1, ctx.length, sampleRate);
  const data = noise.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;

  const src = ctx.createBufferSource();
  src.buffer = noise;
  const filter = ctx.createBiquadFilter();
  filter.type = "bandpass";
  filter.Q.value = 1.2;
  filter.frequency.setValueAtTime(250, 0);
  filter.frequency.exponentialRampToValueAtTime(3500, duration * 0.55);
  filter.frequency.exponentialRampToValueAtTime(600, duration);
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.0001, 0);
  gain.gain.exponentialRampToValueAtTime(0.9, duration * 0.5);
  gain.gain.exponentialRampToValueAtTime(0.0001, duration);

  src.connect(filter).connect(gain).connect(ctx.destination);
  src.start();
  return ctx.startRendering();
}

/** Tono corto que cae de frecuencia, como una burbuja. */
function renderPop(sampleRate: number) {
  const duration = 0.18;
  const ctx = new OfflineAudioContext(2, Math.ceil(duration * sampleRate), sampleRate);
  const osc = ctx.createOscillator();
  osc.type = "sine";
  osc.frequency.setValueAtTime(1100, 0);
  osc.frequency.exponentialRampToValueAtTime(320, 0.09);
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.0001, 0);
  gain.gain.exponentialRampToValueAtTime(0.8, 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, duration);
  osc.connect(gain).connect(ctx.destination);
  osc.start();
  osc.stop(duration);
  return ctx.startRendering();
}

/** Reproduce los efectos en directo (vista previa y exportación en tiempo real). */
export async function playSfx(ctx: AudioContext, kind: SfxKind, volume: number, destinations: AudioNode[]) {
  const src = ctx.createBufferSource();
  src.buffer = await renderSfx(kind, ctx.sampleRate);
  const gain = ctx.createGain();
  gain.gain.value = volume;
  src.connect(gain);
  for (const d of destinations) gain.connect(d);
  src.start();
}
