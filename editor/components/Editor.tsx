"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { analyzeFaces, faceAt } from "@/lib/face";
import { emojiAt, zoomAt } from "@/lib/highlights";
import { exportFast, type SourceFrame } from "@/lib/export";
import { playSfx, sfxEvents } from "@/lib/sfx";
import { detectSpeechSegments } from "@/lib/silence";
import { transcribeInBrowser } from "@/lib/whisper";
import { drawFrame } from "@/lib/render";
import { editedDuration, groupAt, groupWords, segmentAt } from "@/lib/timeline";
import type { CaptionStyle, FaceSample, Highlight, Segment, Word } from "@/lib/types";

const OUT_W = 720;
const OUT_H = 1280;
const MAX_SECONDS = 180;

export default function Editor() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const audioDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const rafRef = useRef<number>(0);

  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState<string>("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [words, setWords] = useState<Word[]>([]);
  const [style, setStyle] = useState<CaptionStyle>("tiktok");
  const [language, setLanguage] = useState("spanish");
  const [cutSilences, setCutSilences] = useState(true);
  const [faceTrack, setFaceTrack] = useState<FaceSample[]>([]);
  const [followFace, setFollowFace] = useState(true);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [useZooms, setUseZooms] = useState(true);
  const [useEmojis, setUseEmojis] = useState(true);
  const [useSfx, setUseSfx] = useState(true);
  const [sfxVolume, setSfxVolume] = useState(0.6);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [exportUrl, setExportUrl] = useState("");
  const [exportExt, setExportExt] = useState("mp4");

  const groups = useMemo(() => groupWords(words), [words]);
  const duration = videoRef.current?.duration ?? 0;
  const activeSegments = useMemo(
    () => (cutSilences && segments.length ? segments : [{ start: 0, end: duration }]),
    [cutSilences, segments, duration],
  );

  // Refs para que el bucle de render lea siempre el estado actual.
  const track = followFace ? faceTrack : [];
  const activeHighlights = useMemo(
    () =>
      highlights
        .map((h) => ({ ...h, zoom: useZooms && h.zoom, emoji: useEmojis ? h.emoji : undefined }))
        .filter((h) => h.zoom || h.emoji),
    [highlights, useZooms, useEmojis],
  );
  const sfx = useMemo(
    () => (useSfx ? sfxEvents(activeHighlights, activeSegments) : []),
    [useSfx, activeHighlights, activeSegments],
  );
  const live = useRef({ groups, style, activeSegments, track, activeHighlights, sfx, sfxVolume });
  live.current = { groups, style, activeSegments, track, activeHighlights, sfx, sfxVolume };

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);
  // Redibuja al cambiar ajustes con el video en pausa.
  useEffect(() => renderCurrent(), [groups, style, track, activeHighlights]);

  async function handleFile(f: File) {
    setExportUrl("");
    setWords([]);
    setSegments([]);
    setFaceTrack([]);
    setHighlights([]);
    setFile(f);
    const objectUrl = URL.createObjectURL(f);
    setUrl(objectUrl);

    const video = videoRef.current!;
    video.src = objectUrl;
    await new Promise((r) => (video.onloadedmetadata = r));
    if (video.duration > MAX_SECONDS) {
      setStatus(`El video dura más de ${MAX_SECONDS} s. Recórtalo antes de subirlo.`);
      return;
    }
    video.currentTime = 0;
    video.onseeked = () => renderCurrent();

    setBusy(true);
    try {
      setStatus("Detectando silencios…");
      setSegments(await detectSpeechSegments(f));

      setStatus("Transcribiendo…");
      const transcript = await transcribe(f);
      setWords(transcript);

      setStatus("Buscando momentos clave…");
      const hl = await fetch("/api/highlights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ words: transcript }),
      }).then((r) => r.json());
      setHighlights(hl.highlights ?? []);

      try {
        setFaceTrack(
          await analyzeFaces(objectUrl, {
            onProgress: (p) => setStatus(`Detectando la cara… ${Math.round(p * 100)} %`),
          }),
        );
      } catch (e) {
        console.error(e);
      }
      setStatus(transcript.length ? "Listo." : "Listo (no se ha detectado voz).");
    } catch (e) {
      setStatus(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  /** Usa Whisper de OpenAI en el servidor si está configurado; si no, Whisper en el navegador. */
  async function transcribe(f: File) {
    const body = new FormData();
    body.append("file", f);
    const res = await fetch("/api/transcribe", { method: "POST", body });
    if (res.ok) return (await res.json()).words as Word[];
    const data = await res.json().catch(() => ({}));
    if (res.status !== 501) throw new Error(data.error ?? `Error ${res.status} al transcribir`);
    return transcribeInBrowser(f, { language, onStatus: setStatus });
  }

  function renderCurrent() {
    const video = videoRef.current;
    const ctx = canvasRef.current?.getContext("2d");
    if (!video || !ctx) return;
    drawAt(ctx, { image: video, width: video.videoWidth, height: video.videoHeight }, video.currentTime);
  }

  /** Dibuja el fotograma de salida para el instante t del original (vista previa y exportación). */
  function drawAt(ctx: CanvasRenderingContext2D, frame: SourceFrame, t: number) {
    const { groups, style, track, activeHighlights: hl } = live.current;
    drawFrame(ctx, frame, {
      group: groupAt(groups, t),
      t,
      style,
      face: faceAt(track, t),
      zoom: zoomAt(hl, t),
      emoji: emojiAt(hl, t),
    });
  }

  /** Reproduce el montaje saltando los cortes. Resuelve cuando termina. */
  function playEdited(): Promise<void> {
    const video = videoRef.current!;
    const ctx = audioCtx();
    let prevT = -1;
    return new Promise((resolve) => {
      const tick = () => {
        const { activeSegments: segs, sfx, sfxVolume } = live.current;
        const t = video.currentTime;
        // Dispara los efectos cuyo instante se acaba de pasar.
        for (const e of sfx) {
          if (e.time > prevT && e.time <= t) {
            playSfx(ctx, e.kind, sfxVolume, [ctx.destination, ...(audioDestRef.current ? [audioDestRef.current] : [])]);
          }
        }
        prevT = t;
        if (segmentAt(segs, t) === -1) {
          const next = segs.find((s) => s.start > t);
          if (!next || video.ended) {
            video.pause();
            renderCurrent();
            setPlaying(false);
            return resolve();
          }
          video.currentTime = next.start;
          prevT = next.start - 0.001;
        }
        renderCurrent();
        rafRef.current = requestAnimationFrame(tick);
      };
      video.currentTime = live.current.activeSegments[0]?.start ?? 0;
      prevT = video.currentTime - 0.001;
      if (ctx.state === "suspended") ctx.resume();
      setPlaying(true);
      video.play().then(tick);
    });
  }

  function stop() {
    cancelAnimationFrame(rafRef.current);
    videoRef.current?.pause();
    setPlaying(false);
  }

  function audioCtx() {
    audioCtxRef.current ??= new AudioContext();
    return audioCtxRef.current;
  }

  function audioStream(): MediaStream {
    // Enruta el audio del <video> por Web Audio para poder grabarlo (y seguir oyéndolo).
    if (!audioDestRef.current) {
      const ctx = audioCtx();
      const source = ctx.createMediaElementSource(videoRef.current!);
      const dest = ctx.createMediaStreamDestination();
      source.connect(dest);
      source.connect(ctx.destination);
      audioDestRef.current = dest;
    }
    return audioDestRef.current.stream;
  }

  async function exportVideo() {
    setBusy(true);
    setExportUrl("");
    const started = performance.now();
    try {
      setStatus("Exportando…");
      const blob = await exportFast(file!, {
        segments: live.current.activeSegments,
        width: OUT_W,
        height: OUT_H,
        draw: drawAt,
        onProgress: (p) => setStatus(`Exportando… ${Math.round(p * 100)} %`),
        sfx: { events: live.current.sfx, volume: live.current.sfxVolume },
      });
      if (blob) {
        setExportUrl(URL.createObjectURL(blob));
        setExportExt("mp4");
        setStatus(`Exportación lista en ${((performance.now() - started) / 1000).toFixed(1)} s.`);
        setBusy(false);
        return;
      }
    } catch (e) {
      console.error("Exportación rápida fallida, se usa la de tiempo real:", e);
    }
    await exportRealtime();
  }

  /** Alternativa para navegadores sin WebCodecs: graba el canvas mientras se reproduce. */
  async function exportRealtime() {
    const canvas = canvasRef.current!;
    const stream = new MediaStream([
      ...canvas.captureStream(30).getVideoTracks(),
      ...audioStream().getAudioTracks(),
    ]);
    const mimeType = ["video/mp4;codecs=avc1", "video/webm;codecs=vp9,opus", "video/webm"].find((m) =>
      MediaRecorder.isTypeSupported(m),
    );
    const recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 6_000_000 });
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);

    setBusy(true);
    setStatus("Exportando… (se graba en tiempo real)");
    recorder.start();
    await playEdited();
    recorder.stop();
    await new Promise((r) => (recorder.onstop = r));
    setExportUrl(URL.createObjectURL(new Blob(chunks, { type: recorder.mimeType })));
    setExportExt(recorder.mimeType.startsWith("video/mp4") ? "mp4" : "webm");
    setStatus("Exportación lista.");
    setBusy(false);
  }


  return (
    <div className="editor">
      <div>
        <canvas ref={canvasRef} width={OUT_W} height={OUT_H} />
        <video ref={videoRef} playsInline hidden crossOrigin="anonymous" />
      </div>

      <div className="panel">
        {!url && (
          <label>
            Idioma del video{" "}
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="spanish">Español</option>
              <option value="english">Inglés</option>
              <option value="portuguese">Portugués</option>
              <option value="french">Francés</option>
              <option value="italian">Italiano</option>
            </select>
          </label>
        )}
        {!url && (
          <label className="drop">
            Haz clic para subir un video (MP4, máx. {MAX_SECONDS} s)
            <input
              type="file"
              accept="video/*"
              hidden
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
          </label>
        )}

        {url && (
          <>
            <div className="row">
              <label>
                Estilo{" "}
                <select value={style} onChange={(e) => setStyle(e.target.value as CaptionStyle)}>
                  <option value="tiktok">TikTok</option>
                  <option value="karaoke">Karaoke</option>
                  <option value="minimal">Minimal</option>
                </select>
              </label>
              <label>
                <input type="checkbox" checked={cutSilences} onChange={(e) => setCutSilences(e.target.checked)} />{" "}
                Recortar silencios
              </label>
              <label>
                <input type="checkbox" checked={followFace} onChange={(e) => setFollowFace(e.target.checked)} />{" "}
                Seguir la cara
              </label>
              <label>
                <input type="checkbox" checked={useZooms} onChange={(e) => setUseZooms(e.target.checked)} /> Zooms
              </label>
              <label>
                <input type="checkbox" checked={useEmojis} onChange={(e) => setUseEmojis(e.target.checked)} /> Emojis
              </label>
              <label>
                <input type="checkbox" checked={useSfx} onChange={(e) => setUseSfx(e.target.checked)} /> Efectos de
                sonido
              </label>
              {useSfx && (
                <label>
                  Volumen{" "}
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={sfxVolume}
                    onChange={(e) => setSfxVolume(Number(e.target.value))}
                  />
                </label>
              )}
            </div>

            <div className="status">
              Duración: {duration.toFixed(1)} s → {editedDuration(activeSegments).toFixed(1)} s ·{" "}
              {segments.length} tramos con voz · {faceTrack.length ? "cara detectada" : "sin datos de cara"} ·{" "}
              {highlights.filter((h) => h.zoom).length} zooms · {highlights.filter((h) => h.emoji).length} emojis · {sfx.length} efectos de sonido
            </div>

            <div className="row">
              {playing ? (
                <button onClick={stop}>Pausar</button>
              ) : (
                <button onClick={playEdited} disabled={busy}>Vista previa</button>
              )}
              <button className="primary" onClick={exportVideo} disabled={busy || playing}>
                Exportar
              </button>
              <button
                onClick={() => {
                  stop();
                  setUrl("");
                  setFile(null);
                  setStatus("");
                }}
                disabled={busy}
              >
                Otro video
              </button>
            </div>

            {exportUrl && (
              <a href={exportUrl} download={`editado.${exportExt}`}>
                <button className="primary">Descargar video</button>
              </a>
            )}

            {words.length > 0 && (
              <div className="words">
                {words.map((w, i) => (
                  <input
                    key={i}
                    value={w.text}
                    title={`${w.start.toFixed(2)} – ${w.end.toFixed(2)} s`}
                    size={Math.max(2, w.text.length)}
                    onChange={(e) =>
                      setWords((ws) => ws.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))
                    }
                  />
                ))}
              </div>
            )}
          </>
        )}

        <div className="status">{status}</div>
      </div>
    </div>
  );
}
