"use client";

import { useRef, useState } from "react";
import { gaps } from "@/lib/edit";
import type { Highlight, Segment } from "@/lib/types";

type Props = {
  duration: number;
  segments: Segment[];
  highlights: Highlight[];
  currentTime: number;
  selected: number | null;
  onSeek: (t: number) => void;
  onSelect: (index: number | null) => void;
  onRemoveSegment: (index: number) => void;
  onRestoreGap: (gap: Segment) => void;
  /** Se llama al soltar un marcador arrastrado. */
  onMoveHighlight: (index: number, time: number) => void;
};

/** Línea de tiempo del video original: tramos conservados y cortes, momentos clave y cabezal. */
export default function Timeline({
  duration,
  segments,
  highlights,
  currentTime,
  selected,
  onSeek,
  onSelect,
  onRemoveSegment,
  onRestoreGap,
  onMoveHighlight,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<{ index: number; time: number; moved: boolean } | null>(null);
  if (!duration) return null;

  const pct = (t: number) => `${(t / duration) * 100}%`;
  const timeAt = (clientX: number) => {
    const r = ref.current!.getBoundingClientRect();
    return Math.min(duration, Math.max(0, ((clientX - r.left) / r.width) * duration));
  };
  const step = duration > 60 ? 10 : duration > 20 ? 5 : 1;
  const ticks = Array.from({ length: Math.floor(duration / step) + 1 }, (_, i) => i * step);

  return (
    <div className="timeline" ref={ref} onPointerDown={(e) => e.target === e.currentTarget && onSeek(timeAt(e.clientX))}>
      <div className="tl-ruler" onPointerDown={(e) => onSeek(timeAt(e.clientX))}>
        {ticks.map((t) => (
          <span key={t} style={{ left: pct(t) }}>
            {t}s
          </span>
        ))}
      </div>

      <div className="tl-track">
        {segments.map((s, i) => (
          <button
            key={`s${i}`}
            className="tl-seg"
            style={{ left: pct(s.start), width: pct(s.end - s.start) }}
            title={`Tramo ${s.start.toFixed(1)}–${s.end.toFixed(1)} s · clic para quitarlo`}
            onClick={() => onRemoveSegment(i)}
          />
        ))}
        {gaps(segments, duration).map((g) => (
          <button
            key={`g${g.start}`}
            className="tl-gap"
            style={{ left: pct(g.start), width: pct(g.end - g.start) }}
            title={`Corte ${g.start.toFixed(1)}–${g.end.toFixed(1)} s · clic para recuperarlo`}
            onClick={() => onRestoreGap(g)}
          />
        ))}
      </div>

      <div className="tl-track tl-marks">
        {highlights.map((h, i) => {
          const time = drag?.index === i ? drag.time : h.time;
          return (
            <button
              key={i}
              className={`tl-mark${h.zoom ? " zoom" : ""}${selected === i ? " selected" : ""}`}
              style={{ left: pct(time) }}
              title={`${time.toFixed(2)} s${h.zoom ? " · zoom" : ""}${h.emoji ? ` · ${h.emoji}` : ""} · arrastra para mover`}
              onPointerDown={(e) => {
                e.currentTarget.setPointerCapture(e.pointerId);
                setDrag({ index: i, time: h.time, moved: false });
              }}
              onPointerMove={(e) => {
                if (drag?.index !== i) return;
                const t = timeAt(e.clientX);
                setDrag({ index: i, time: t, moved: drag.moved || Math.abs(t - h.time) > 0.05 });
                onSeek(t);
              }}
              onPointerUp={() => {
                if (drag?.index !== i) return;
                if (drag.moved) onMoveHighlight(i, drag.time);
                onSelect(i);
                setDrag(null);
              }}
            >
              {h.emoji ?? "🔍"}
            </button>
          );
        })}
      </div>

      <div className="tl-playhead" style={{ left: pct(currentTime) }} />
    </div>
  );
}
