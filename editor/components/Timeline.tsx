"use client";

import { useEffect, useRef, useState } from "react";
import { gaps } from "@/lib/edit";
import type { Highlight, Segment } from "@/lib/types";

type Props = {
  /** Rango visible del video original (todo el video, o el de un clip). */
  start?: number;
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
  start = 0,
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
  const scrollRef = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<{
    index: number;
    time: number;
    moved: boolean;
  } | null>(null);
  // Zoom: 1 = todo el video a la vista. En videos largos empieza mostrando ~1 minuto.
  const [zoom, setZoom] = useState(1);
  const [viewWidth, setViewWidth] = useState(600);
  useEffect(() => setZoom(duration > 90 ? Math.min(MAX_ZOOM, duration / 60) : 1), [duration]);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setViewWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  // Desplaza la vista para que el cabezal no se salga.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !duration || drag) return;
    const x = ((currentTime - start) / duration) * el.scrollWidth;
    if (x < el.scrollLeft || x > el.scrollLeft + el.clientWidth - 20) el.scrollLeft = x - el.clientWidth * 0.2;
  }, [currentTime, start, duration, zoom, drag]);
  if (!duration) return null;

  const pct = (t: number) => `${((t - start) / duration) * 100}%`;
  const len = (d: number) => `${(d / duration) * 100}%`;
  const timeAt = (clientX: number) => {
    const r = ref.current!.getBoundingClientRect();
    return start + Math.min(duration, Math.max(0, ((clientX - r.left) / r.width) * duration));
  };
  // Marcas de la regla separadas al menos ~60 px.
  const pxPerSec = (viewWidth * zoom) / duration;
  const step = TICK_STEPS.find((s) => s * pxPerSec >= 60) ?? 600;
  const first = Math.ceil(start / step) * step;
  const ticks = Array.from({ length: Math.floor((start + duration - first) / step) + 1 }, (_, i) => first + i * step);

  return (
    <div className="tl-wrap">
      {duration > 30 && (
        <label className="tl-zoom">
          Zoom{" "}
          <input
            type="range"
            min={1}
            max={Math.max(1, Math.min(MAX_ZOOM, duration / 10))}
            step={0.5}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          />
        </label>
      )}
      <div className="tl-scroll" ref={scrollRef}>
        <div
          className="timeline"
          ref={ref}
          style={{ width: `${zoom * 100}%` }}
          onPointerDown={(e) => e.target === e.currentTarget && onSeek(timeAt(e.clientX))}
        >
          <div className="tl-ruler" onPointerDown={(e) => onSeek(timeAt(e.clientX))}>
            {ticks.map((t) => (
              <span key={t} style={{ left: pct(t) }}>
                {formatTime(t)}
              </span>
            ))}
          </div>

          <div className="tl-track">
            {segments.map((s, i) => (
              <button
                key={`s${i}`}
                className="tl-seg"
                style={{ left: pct(s.start), width: len(s.end - s.start) }}
                title={`Tramo ${s.start.toFixed(1)}–${s.end.toFixed(1)} s · clic para quitarlo`}
                onClick={() => onRemoveSegment(i)}
              />
            ))}
            {gaps(segments, start + duration, start).map((g) => (
              <button
                key={`g${g.start}`}
                className="tl-gap"
                style={{ left: pct(g.start), width: len(g.end - g.start) }}
                title={`Corte ${g.start.toFixed(1)}–${g.end.toFixed(1)} s · clic para recuperarlo`}
                onClick={() => onRestoreGap(g)}
              />
            ))}
          </div>

          <div className="tl-track tl-marks">
            {highlights.map((h, i) => {
              const time = drag?.index === i ? drag.time : h.time;
              if (time < start || time > start + duration) return null;
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
                    setDrag({
                      index: i,
                      time: t,
                      moved: drag.moved || Math.abs(t - h.time) > 0.05,
                    });
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

          {currentTime >= start && currentTime <= start + duration && (
            <div className="tl-playhead" style={{ left: pct(currentTime) }} />
          )}
        </div>
      </div>
    </div>
  );
}

const MAX_ZOOM = 60;
const TICK_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300];

function formatTime(t: number) {
  if (t < 60) return `${t}s`;
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
}
