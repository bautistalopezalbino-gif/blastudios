export type Word = { text: string; start: number; end: number };

/** Tramo del video original que se conserva en el montaje final. */
export type Segment = { start: number; end: number };

export type CaptionStyle = "tiktok" | "minimal" | "karaoke";

/** Decisiones de edición: el motor de render solo aplica esto al video. */
export type Timeline = {
  segments: Segment[];
  words: Word[];
  style: CaptionStyle;
};

/** Cara detectada, en coordenadas normalizadas (0–1) del fotograma original. */
export type FaceBox = { cx: number; cy: number; h: number };

export type FaceSample = FaceBox & { t: number };

/** Momento destacado: zoom de énfasis y/o emoji, anclado al inicio de una palabra. */
export type Highlight = { time: number; zoom: boolean; emoji?: string };
