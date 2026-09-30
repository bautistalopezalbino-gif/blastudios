import { FaceDetector, FilesetResolver } from "@mediapipe/tasks-vision";
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
 */
export async function analyzeFaces(
  url: string,
  { step = 0.25, onProgress }: { step?: number; onProgress?: (p: number) => void } = {},
): Promise<FaceSample[]> {
  const detector = await getDetector();
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

  const raw: (FaceBox | null)[] = [];
  const times: number[] = [];
  for (let t = 0; t < video.duration; t += step) {
    video.currentTime = t;
    await new Promise((r) => (video.onseeked = r));
    ctx.drawImage(video, 0, 0);
    const faces = detector.detect(canvas).detections;
    const biggest = faces
      .map((d) => d.boundingBox!)
      .sort((a, b) => b.width * b.height - a.width * a.height)[0];
    raw.push(
      biggest
        ? {
            cx: (biggest.originX + biggest.width / 2) / video.videoWidth,
            cy: (biggest.originY + biggest.height / 2) / video.videoHeight,
            h: biggest.height / video.videoHeight,
          }
        : null,
    );
    times.push(t);
    onProgress?.(Math.min(1, t / video.duration));
  }
  video.removeAttribute("src");
  return smooth(fillGaps(raw)).map((box, i) => ({ t: times[i], ...box }));
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
