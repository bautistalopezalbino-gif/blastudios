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
