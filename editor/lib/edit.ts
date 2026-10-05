import type { Segment } from "./types";

/** Duración mínima de un trozo al cortar, para no crear tramos imposibles de ver. */
const MIN_PIECE = 0.1;

/** Parte en dos el tramo que contiene t. Si t está en un corte o muy cerca de un borde, no cambia nada. */
export function splitAt(segments: Segment[], t: number): Segment[] {
  return segments.flatMap((s) =>
    t - s.start >= MIN_PIECE && s.end - t >= MIN_PIECE
      ? [
          { start: s.start, end: t },
          { start: t, end: s.end },
        ]
      : [s],
  );
}

/** Quita un tramo del montaje (pasa a ser un corte). */
export function removeSegment(segments: Segment[], index: number): Segment[] {
  return segments.filter((_, i) => i !== index);
}

/** Vuelve a incluir un corte; se une con los tramos vecinos si se tocan. */
export function restoreGap(segments: Segment[], gap: Segment): Segment[] {
  return mergeTouching([...segments, gap]);
}

/** Cortes (partes del original que no salen en el montaje) entre `from` y `to`. */
export function gaps(segments: Segment[], to: number, from = 0): Segment[] {
  const out: Segment[] = [];
  let cursor = from;
  for (const s of [...segments].sort((a, b) => a.start - b.start)) {
    if (s.start - cursor > 0.01) out.push({ start: cursor, end: s.start });
    cursor = Math.max(cursor, s.end);
  }
  if (to - cursor > 0.01) out.push({ start: cursor, end: to });
  return out;
}

function mergeTouching(segments: Segment[]): Segment[] {
  const sorted = [...segments].sort((a, b) => a.start - b.start);
  const out: Segment[] = [];
  for (const s of sorted) {
    const last = out[out.length - 1];
    if (last && s.start <= last.end + 0.001) last.end = Math.max(last.end, s.end);
    else out.push({ ...s });
  }
  return out;
}

/** Los tramos recortados al rango [start, end) (para editar un clip). */
export function clipTo(segments: Segment[], start: number, end: number): Segment[] {
  return segments
    .map((s) => ({ start: Math.max(s.start, start), end: Math.min(s.end, end) }))
    .filter((s) => s.end - s.start > 0.05);
}

/** Instante del montaje que corresponde a t del original, o null si cae en un corte. */
export function outputTime(segments: Segment[], t: number): number | null {
  let offset = 0;
  for (const s of segments) {
    if (t >= s.start && t < s.end) return offset + (t - s.start);
    offset += s.end - s.start;
  }
  return null;
}
