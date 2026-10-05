import { FaceDetector, FilesetResolver } from "@mediapipe/tasks-vision";
import { ALL_FORMATS, BlobSource, CanvasSink, Input } from "mediabunny";
import type { FaceBox, FaceSample } from "./types";

// Servidos desde public/: el WASM lo copia scripts/copy-mediapipe.mjs al instalar.
const WASM_URL = "/mediapipe/wasm";
const MODEL_URL = "/mediapipe/blaze_face_short_range.tflite";

let detectorPromise: Promise<FaceDetector> | null = null;

function getDetector(): Promise<FaceDetector> {
  detectorPromise ??= FilesetResolver.forVisionTasks(WASM_URL).then((fileset) =>
    FaceDetector.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: MODEL_URL },
      runningMode: "IMAGE",
      minDetectionConfidence: 0.5,
    }),
  );
  return detectorPromise;
}

/**
 * Recorre el video cada `step` segundos y localiza la cara más grande.
 * Devuelve posiciones normalizadas (0–1) respecto al fotograma original, ya suavizadas.
 * Decodifica los fotogramas en orden y a baja resolución con WebCodecs (rápido también en videos largos);
 * si no se puede, salta por el video con un elemento <video>.
 */
export async function analyzeFaces(
  file: File,
  url: string,
  { step = 0.25, onProgress }: { step?: number; onProgress?: (p: number) => void } = {},
): Promise<FaceSample[]> {
  const detector = await getDetector();
  let samples: { t: number; box: FaceBox | null }[] | null = null;
  try {
    samples = await scanWithDecoder(file, step, detector, onProgress);
  } catch (e) {
    console.warn("Detección de caras con WebCodecs no disponible, se usa el <video>:", e);
  }
  samples ??= await scanWithVideo(url, step, detector, onProgress);
  return smooth(fillGaps(samples.map((s) => s.box))).map((box, i) => ({ t: samples![i].t, ...box }));
}

type Detector = Awaited<ReturnType<typeof getDetector>>;

function biggestFace(detector: Detector, image: HTMLCanvasElement | OffscreenCanvas, w: number, h: number) {
  const box = detector
    .detect(image as HTMLCanvasElement)
    .detections.map((d) => d.boundingBox!)
    .sort((a, b) => b.width * b.height - a.width * a.height)[0];
  return box ? { cx: (box.originX + box.width / 2) / w, cy: (box.originY + box.height / 2) / h, h: box.height / h } : null;
}

async function scanWithDecoder(file: File, step: number, detector: Detector, onProgress?: (p: number) => void) {
  const input = new Input({ source: new BlobSource(file), formats: ALL_FORMATS });
  try {
    const track = await input.getPrimaryVideoTrack();
    if (!track || typeof VideoDecoder === "undefined" || !(await track.canDecode())) return null;
    const duration = await track.computeDuration();
    const times = Array.from({ length: Math.floor(duration / step) + 1 }, (_, i) => i * step);
    // 480 px de ancho es de sobra para el detector (trabaja a 128 px) y decodificar es mucho más barato.
    const sink = new CanvasSink(track, { width: 480, poolSize: 1 });
    const out: { t: number; box: FaceBox | null }[] = [];
    let i = 0;
    for await (const wrapped of sink.canvasesAtTimestamps(times)) {
      const c = wrapped?.canvas;
      out.push({ t: times[i], box: c ? biggestFace(detector, c, c.width, c.height) : null });
      if (++i % 10 === 0) onProgress?.(i / times.length);
    }
    return out;
  } finally {
    input.dispose();
  }
}

async function scanWithVideo(url: string, step: number, detector: Detector, onProgress?: (p: number) => void) {
  const video = document.createElement("video");
  video.muted = true;
  video.playsInline = true;
  video.src = url;
  await new Promise((r) => (video.onloadeddata = r));

  // Se copia cada fotograma a un canvas: pasar el <video> directamente falla en algunos navegadores.
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d")!;

  const out: { t: number; box: FaceBox | null }[] = [];
  for (let t = 0; t < video.duration; t += step) {
    video.currentTime = t;
    await new Promise((r) => (video.onseeked = r));
    ctx.drawImage(video, 0, 0);
    out.push({ t, box: biggestFace(detector, canvas, canvas.width, canvas.height) });
    onProgress?.(Math.min(1, t / video.duration));
  }
  video.removeAttribute("src");
  return out;
}

/** Si no hay cara en un fotograma, mantiene la última posición conocida. Sin ninguna cara, devuelve []. */
function fillGaps(raw: (FaceBox | null)[]): FaceBox[] {
  const firstKnown = raw.find(Boolean);
  if (!firstKnown) return [];
  let last = firstKnown;
  return raw.map((b) => (last = b ?? last));
}

/** Media móvil para que el encuadre no tiemble. */
function smooth(boxes: FaceBox[], radius = 3): FaceBox[] {
  return boxes.map((_, i) => {
    const win = boxes.slice(Math.max(0, i - radius), i + radius + 1);
    const avg = (k: keyof FaceBox) => win.reduce((a, b) => a + b[k], 0) / win.length;
    return { cx: avg("cx"), cy: avg("cy"), h: avg("h") };
  });
}

/** Posición de la cara en el instante t, interpolando entre muestras. */
export function faceAt(track: FaceSample[], t: number): FaceBox | undefined {
  if (!track.length) return undefined;
  const i = track.findIndex((s) => s.t > t);
  if (i === -1) return track[track.length - 1];
  if (i === 0) return track[0];
  const a = track[i - 1];
  const b = track[i];
  const k = (t - a.t) / (b.t - a.t);
  return { cx: a.cx + (b.cx - a.cx) * k, cy: a.cy + (b.cy - a.cy) * k, h: a.h + (b.h - a.h) * k };
}
