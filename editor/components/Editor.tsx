"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CAPTION_PRESETS, ensureFont, getPreset } from "@/lib/captions";
import type { Clip } from "@/lib/clips";
import { clipTo, outputTime, removeSegment, restoreGap, splitAt } from "@/lib/edit";
import { analyzeFaces, faceAt } from "@/lib/face";
import { emojiAt, zoomAt } from "@/lib/highlights";
import { exportFast, type SourceFrame } from "@/lib/export";
import { playSfx, sfxEvents } from "@/lib/sfx";
import { extractAudio16k, SAMPLE_RATE } from "@/lib/audio";
import { detectSpeechSegments } from "@/lib/silence";
import { transcribe } from "@/lib/transcribe";
import Timeline from "./Timeline";
import WordList from "./WordList";
import { drawFrame } from "@/lib/render";
import { editedDuration, groupAt, groupWords, segmentAt } from "@/lib/timeline";
import type { FaceSample, Highlight, Segment, Word } from "@/lib/types";

const OUT_W = 720;
const OUT_H = 1280;
const MAX_SECONDS = 30 * 60;
/** A partir de esta duración, la exportación se escribe directamente en disco (si el navegador lo permite). */
const SAVE_TO_DISK_FROM = 3 * 60;
const BRAND_KEY = "blastudios-editor-estilo";
const QUICK_EMOJIS = ["🔥", "💡", "💰", "⚠️", "😂", "👀", "🚀", "❤️", "🏆", "✅", "🤯", "👇"];

type EditState = { segments: Segment[]; highlights: Highlight[] };
/** Un clip sugerido, con su edición propia (si se ha abierto) y su exportación. */
type ClipItem = Clip & { edit?: EditState; exportUrl?: string };
const TITLE_SECONDS = 3;
const CLIP_LENGTHS: Record<string, [number, number]> = { corto: [15, 30], medio: [30, 60], largo: [60, 90] };

type CaptionSettings = { presetId: string; text: string; accent: string };

function defaultsFor(presetId: string): CaptionSettings {
  const p = getPreset(presetId);
  return { presetId: p.id, text: p.text, accent: p.accent };
}

/** Estilo y colores de marca guardados en este navegador (si se puede). */
function loadSaved(): CaptionSettings {
  try {
    const saved = JSON.parse(localStorage.getItem(BRAND_KEY) ?? "null") as CaptionSettings | null;
    if (saved?.presetId) return { ...defaultsFor(saved.presetId), ...saved };
  } catch {
    // Sin almacenamiento disponible: se usan los valores por defecto.
  }
  return defaultsFor("tiktok");
}

export default function Editor() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const audioDestRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const rafRef = useRef<number>(0);
  const detectedRef = useRef<Segment[]>([]);
  const historyRef = useRef<EditState[]>([]);
  /** Edición del video completo mientras se edita un clip. */
  const fullRef = useRef<EditState | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState<string>("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [words, setWords] = useState<Word[]>([]);
  const [caption, setCaption] = useState<CaptionSettings>(() => defaultsFor("tiktok"));
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
  const [currentTime, setCurrentTime] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [clips, setClips] = useState<ClipItem[]>([]);
  const [activeClip, setActiveClip] = useState<number | null>(null);
  const [clipLength, setClipLength] = useState("medio");
  const [clipCount, setClipCount] = useState(5);
  const [showTitle, setShowTitle] = useState(true);

  const preset = getPreset(caption.presetId);
  const groups = useMemo(() => groupWords(words, preset.maxWords), [words, preset.maxWords]);
  const captionStyle = useMemo(
    () => ({ preset, colors: { text: caption.text, accent: caption.accent } }),
    [preset, caption.text, caption.accent],
  );
  const duration = videoRef.current?.duration ?? 0;
  const activeSegments = useMemo(
    () => (segments.length ? segments : [{ start: 0, end: duration }]),
    [segments, duration],
  );

  // Refs para que el bucle de render lea siempre el estado actual.
  const track = followFace ? faceTrack : [];
  /** Momentos clave con las casillas de zooms y emojis aplicadas. */
  const applyToggles = useCallback(
    (hs: Highlight[]) =>
      hs
        .map((h) => ({ ...h, zoom: useZooms && h.zoom, emoji: useEmojis ? h.emoji : undefined }))
        .filter((h) => h.zoom || h.emoji),
    [useZooms, useEmojis],
  );
  const activeHighlights = useMemo(() => applyToggles(highlights), [applyToggles, highlights]);
  const sfx = useMemo(
    () => (useSfx ? sfxEvents(activeHighlights, activeSegments) : []),
    [useSfx, activeHighlights, activeSegments],
  );
  const clip = activeClip !== null ? clips[activeClip] : null;
  const title = clip && showTitle ? clip.title : "";
  const live = useRef({ groups, captionStyle, activeSegments, track, activeHighlights, sfx, sfxVolume, title });
  live.current = { groups, captionStyle, activeSegments, track, activeHighlights, sfx, sfxVolume, title };

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);
  // Atajos: Supr borra el momento seleccionado y Ctrl+Z deshace (salvo escribiendo en un campo).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, select, textarea")) return;
      if ((e.key === "Delete" || e.key === "Backspace") && selected !== null) {
        e.preventDefault();
        deleteSelected();
      } else if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        undo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  // Redibuja al cambiar ajustes con el video en pausa.
  useEffect(() => renderCurrent(), [groups, captionStyle, track, activeHighlights, title]);
  // Recupera el estilo guardado al abrir el editor.
  useEffect(() => setCaption(loadSaved()), []);
  // Al cambiar de estilo, carga su fuente, redibuja y lo recuerda.
  useEffect(() => {
    ensureFont(preset).then(() => renderCurrent());
    try {
      localStorage.setItem(BRAND_KEY, JSON.stringify(caption));
    } catch {
      // Sin almacenamiento disponible: no se recuerda.
    }
  }, [caption, preset]);

  async function handleFile(f: File) {
    setExportUrl("");
    setWords([]);
    setSegments([]);
    setFaceTrack([]);
    setHighlights([]);
    setSelected(null);
    setClips([]);
    setActiveClip(null);
    fullRef.current = null;
    historyRef.current = [];
    setCanUndo(false);
    setFile(f);
    const objectUrl = URL.createObjectURL(f);
    setUrl(objectUrl);

    const video = videoRef.current!;
    video.src = objectUrl;
    await new Promise((r) => (video.onloadedmetadata = r));
    if (video.duration > MAX_SECONDS) {
      setStatus(`El video dura más de ${MAX_SECONDS / 60} minutos. Recórtalo antes de subirlo.`);
      return;
    }
    video.currentTime = 0;
    video.onseeked = () => {
      setCurrentTime(video.currentTime);
      renderCurrent();
    };

    setBusy(true);
    try {
      setStatus("Detectando silencios…");
      const audio = await extractAudio16k(f, (p) => setStatus(`Leyendo el audio… ${Math.round(p * 100)} %`));
      setStatus("Detectando silencios…");
      const speech = audio.length ? detectSpeechSegments(audio, SAMPLE_RATE) : [];
      detectedRef.current = speech.length ? speech : [{ start: 0, end: video.duration }];
      setSegments(cutSilences ? detectedRef.current : [{ start: 0, end: video.duration }]);

      const transcript = audio.length ? await transcribe(audio, speech, { language, onStatus: setStatus }) : [];
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
          await analyzeFaces(f, objectUrl, {
            // En videos largos basta con mirar la cara cada medio segundo.
            step: video.duration > 180 ? 0.5 : 0.25,
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

  /** Aplica un cambio de edición guardando el estado anterior para poder deshacerlo. */
  function commit(next: Partial<EditState>) {
    historyRef.current.push({ segments, highlights });
    if (historyRef.current.length > 100) historyRef.current.shift();
    setCanUndo(true);
    if (next.segments) setSegments(next.segments);
    if (next.highlights) setHighlights(next.highlights);
  }

  function undo() {
    const prev = historyRef.current.pop();
    if (!prev) return;
    setSegments(prev.segments);
    setHighlights(prev.highlights);
    setSelected(null);
    setCanUndo(historyRef.current.length > 0);
  }

  function seek(t: number) {
    const video = videoRef.current;
    if (!video || playing) return;
    video.currentTime = t;
    setCurrentTime(t);
  }

  function cutHere() {
    const next = splitAt(activeSegments, currentTime);
    if (next.length === activeSegments.length) {
      setStatus("El cabezal está en un corte o en el borde de un tramo: muévelo dentro de un tramo verde.");
      return;
    }
    commit({ segments: next });
    setStatus("Tramo dividido: haz clic en uno de los trozos para quitarlo.");
  }

  // Versiones estables para la lista de palabras (que está memorizada).
  const seekRef = useRef(seek);
  seekRef.current = seek;
  const stableSeek = useCallback((t: number) => seekRef.current(t), []);
  const changeWord = useCallback(
    (index: number, text: string) => setWords((ws) => ws.map((w, i) => (i === index ? { ...w, text } : w))),
    [],
  );

  function addHighlight(h: Partial<Highlight>) {
    const next = [...highlights, { time: currentTime, zoom: false, ...h }];
    commit({ highlights: next });
    setSelected(next.length - 1);
  }

  function updateSelected(patch: Partial<Highlight>) {
    if (selected === null) return;
    commit({ highlights: highlights.map((h, i) => (i === selected ? { ...h, ...patch } : h)) });
  }

  function deleteSelected() {
    if (selected === null) return;
    commit({ highlights: highlights.filter((_, i) => i !== selected) });
    setSelected(null);
  }

  /** Edición inicial de un clip: los tramos y momentos clave del video completo dentro de su rango. */
  function defaultClipEdit(c: Clip): EditState {
    const full = fullRef.current ?? { segments: activeSegments, highlights };
    return {
      segments: clipTo(full.segments, c.start, c.end),
      highlights: full.highlights.filter((h) => h.time >= c.start && h.time < c.end),
    };
  }

  /** Guarda la edición actual en el clip abierto (si hay uno). */
  function withCurrentClipSaved(list: ClipItem[]): ClipItem[] {
    if (activeClip === null) return list;
    return list.map((c, i) => (i === activeClip ? { ...c, edit: { segments: activeSegments, highlights } } : c));
  }

  async function findClips() {
    const [min, max] = CLIP_LENGTHS[clipLength];
    setBusy(true);
    setStatus("Buscando los mejores clips…");
    try {
      const res = await fetch("/api/clips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ words, min, max, count: clipCount }),
      });
      const data = await res.json();
      setClips(data.clips ?? []);
      setStatus(
        data.clips?.length
          ? `${data.clips.length} clips encontrados${data.source === "heuristic" ? " (sin IA: por palabras clave)" : ""}.`
          : "No se han encontrado fragmentos con esa duración.",
      );
    } catch (e) {
      setStatus(`Error al buscar clips: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  function openClip(i: number) {
    stop();
    const list = withCurrentClipSaved(clips);
    if (activeClip === null) fullRef.current = { segments: activeSegments, highlights };
    const edit = list[i].edit ?? defaultClipEdit(list[i]);
    setClips(list);
    setActiveClip(i);
    setSegments(edit.segments);
    setHighlights(edit.highlights);
    setSelected(null);
    historyRef.current = [];
    setCanUndo(false);
    seek(edit.segments[0]?.start ?? list[i].start);
  }

  function closeClip() {
    stop();
    setClips(withCurrentClipSaved(clips));
    setActiveClip(null);
    if (fullRef.current) {
      setSegments(fullRef.current.segments);
      setHighlights(fullRef.current.highlights);
    }
    fullRef.current = null;
    setSelected(null);
    historyRef.current = [];
    setCanUndo(false);
  }

  /** Exporta los clips indicados uno tras otro y deja un enlace de descarga en cada uno. */
  async function exportClips(indices: number[]) {
    stop();
    let list = withCurrentClipSaved(clips);
    setBusy(true);
    try {
      for (const [n, i] of indices.entries()) {
        const c = list[i];
        setStatus(`Exportando clip ${i + 1}${indices.length > 1 ? ` (${n + 1} de ${indices.length})` : ""}…`);
        const result = await runExport(c.edit ?? defaultClipEdit(c), showTitle ? c.title : "");
        if (!(result instanceof Blob)) {
          setStatus("Tu navegador no permite exportar clips. Prueba con Chrome o Edge.");
          return;
        }
        list = list.map((x, j) => (j === i ? { ...x, exportUrl: URL.createObjectURL(result) } : x));
        setClips(list);
      }
      setStatus(indices.length > 1 ? "Clips exportados: descárgalos desde la lista." : "Clip exportado.");
    } catch (e) {
      setStatus(`Error al exportar: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  function renderCurrent() {
    const video = videoRef.current;
    const ctx = canvasRef.current?.getContext("2d");
    if (!video || !ctx) return;
    const { activeHighlights: hl, activeSegments: segs, title } = live.current;
    drawer(hl, segs, title)(ctx, { image: video, width: video.videoWidth, height: video.videoHeight }, video.currentTime);
  }

  /**
   * Función que dibuja el fotograma de salida para el instante t del original, con unos momentos clave,
   * tramos y título concretos (los de la edición actual, o los de un clip al exportarlo).
   */
  function drawer(hl: Highlight[], segs: Segment[], titleText: string) {
    return (ctx: CanvasRenderingContext2D, frame: SourceFrame, t: number) => {
      const { groups, captionStyle, track } = live.current;
      const out = titleText ? outputTime(segs, t) : null;
      drawFrame(ctx, frame, {
        group: groupAt(groups, t),
        t,
        caption: captionStyle,
        face: faceAt(track, t),
        zoom: zoomAt(hl, t),
        emoji: emojiAt(hl, t),
        title: out !== null && out < TITLE_SECONDS ? { text: titleText, progress: out / TITLE_SECONDS } : undefined,
      });
    };
  }

  /** Reproduce el montaje saltando los cortes. Resuelve cuando termina. */
  function playEdited(): Promise<void> {
    const video = videoRef.current!;
    const ctx = audioCtx();
    let prevT = -1;
    let lastShown = -1;
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
        // El cabezal de la línea de tiempo se actualiza ~10 veces por segundo, no en cada fotograma.
        if (Math.abs(t - lastShown) > 0.1) setCurrentTime((lastShown = t));
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

  /** Exporta una edición concreta con WebCodecs. Devuelve el MP4, "saved" si se escribió en disco, o null si no se puede. */
  async function runExport(edit: EditState, titleText: string, saveTo?: FileSystemWritableFileStream) {
    await ensureFont(preset);
    const hl = applyToggles(edit.highlights);
    return exportFast(file!, {
      segments: edit.segments,
      width: OUT_W,
      height: OUT_H,
      draw: drawer(hl, edit.segments, titleText),
      onProgress: (p) => setStatus(`Exportando… ${Math.round(p * 100)} %`),
      sfx: { events: useSfx ? sfxEvents(hl, edit.segments) : [], volume: sfxVolume },
      saveTo,
    });
  }

  async function exportVideo() {
    // En montajes largos, el MP4 se escribe directamente en un archivo para no llenar la memoria.
    // El selector de archivo tiene que abrirse antes de cualquier espera, mientras dura el clic.
    let saveTo: FileSystemWritableFileStream | undefined;
    let savedName = "";
    const picker = (window as Window & { showSaveFilePicker?: (o: object) => Promise<FileSystemFileHandle> })
      .showSaveFilePicker;
    if (editedDuration(live.current.activeSegments) > SAVE_TO_DISK_FROM && picker) {
      try {
        const handle = await picker({
          suggestedName: "editado.mp4",
          types: [{ description: "Video MP4", accept: { "video/mp4": [".mp4"] } }],
        });
        savedName = handle.name;
        saveTo = await handle.createWritable();
      } catch {
        setStatus("Exportación cancelada.");
        return;
      }
    }

    setBusy(true);
    setExportUrl("");
    const started = performance.now();
    try {
      setStatus("Exportando…");
      const result = await runExport({ segments: activeSegments, highlights }, title, saveTo);
      if (result) {
        const secs = ((performance.now() - started) / 1000).toFixed(1);
        if (result === "saved") {
          setStatus(`Exportación lista en ${secs} s: guardada como "${savedName}".`);
        } else {
          setExportUrl(URL.createObjectURL(result));
          setExportExt("mp4");
          setStatus(`Exportación lista en ${secs} s.`);
        }
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
            Haz clic para subir un video (MP4, hasta {MAX_SECONDS / 60} minutos)
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
            {clip && (
              <div className="clip-banner">
                <div className="row">
                  <strong>
                    Clip {activeClip! + 1} de {clips.length}
                  </strong>
                  <span className="status">
                    {formatTime(clip.start)}–{formatTime(clip.end)}
                  </span>
                  <button onClick={closeClip} disabled={busy}>
                    ← Volver al video completo
                  </button>
                </div>
                <div className="row">
                  <input
                    className="clip-title"
                    value={clip.title}
                    onChange={(e) =>
                      setClips((cs) => cs.map((c, i) => (i === activeClip ? { ...c, title: e.target.value } : c)))
                    }
                  />
                  <label>
                    <input type="checkbox" checked={showTitle} onChange={(e) => setShowTitle(e.target.checked)} />{" "}
                    Título al inicio
                  </label>
                </div>
              </div>
            )}
            <div className="row">
              <label>
                Estilo{" "}
                <select value={caption.presetId} onChange={(e) => setCaption(defaultsFor(e.target.value))}>
                  {CAPTION_PRESETS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Texto{" "}
                <input
                  type="color"
                  value={caption.text}
                  onChange={(e) => setCaption((c) => ({ ...c, text: e.target.value }))}
                />
              </label>
              <label>
                Resaltado{" "}
                <input
                  type="color"
                  value={caption.accent}
                  onChange={(e) => setCaption((c) => ({ ...c, accent: e.target.value }))}
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={cutSilences}
                  onChange={(e) => {
                    setCutSilences(e.target.checked);
                    commit({ segments: e.target.checked ? detectedRef.current : [{ start: 0, end: duration }] });
                  }}
                />{" "}
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
              {clip ? "Clip" : "Duración"}: {(clip ? clip.end - clip.start : duration).toFixed(1)} s → {editedDuration(activeSegments).toFixed(1)} s ·{" "}
              {segments.length} tramos · {faceTrack.length ? "cara detectada" : "sin datos de cara"} ·{" "}
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

            <Timeline
              start={clip?.start ?? 0}
              duration={clip ? clip.end - clip.start : duration}
              segments={activeSegments}
              highlights={highlights}
              currentTime={currentTime}
              selected={selected}
              onSeek={seek}
              onSelect={setSelected}
              onRemoveSegment={(i) => commit({ segments: removeSegment(activeSegments, i) })}
              onRestoreGap={(g) => commit({ segments: restoreGap(activeSegments, g) })}
              onMoveHighlight={(i, time) =>
                commit({ highlights: highlights.map((h, j) => (j === i ? { ...h, time } : h)) })
              }
            />

            <div className="row">
              <button onClick={cutHere} disabled={playing}>
                ✂ Cortar aquí
              </button>
              <button onClick={() => addHighlight({ zoom: true })} disabled={playing}>
                + Zoom aquí
              </button>
              <button onClick={() => addHighlight({ emoji: "🔥" })} disabled={playing}>
                + Emoji aquí
              </button>
              <button onClick={undo} disabled={!canUndo || playing}>
                ↶ Deshacer
              </button>
              <span className="status">{currentTime.toFixed(2)} s</span>
            </div>

            {selected !== null && highlights[selected] && (
              <div className="selection">
                <div className="row">
                  <strong>Momento en {highlights[selected].time.toFixed(2)} s</strong>
                  <label>
                    <input
                      type="checkbox"
                      checked={highlights[selected].zoom}
                      onChange={(e) => updateSelected({ zoom: e.target.checked })}
                    />{" "}
                    Zoom
                  </label>
                  <button onClick={deleteSelected}>Eliminar</button>
                  <button onClick={() => setSelected(null)}>Cerrar</button>
                </div>
                <div className="row emoji-picker">
                  <button
                    className={!highlights[selected].emoji ? "active" : ""}
                    onClick={() => updateSelected({ emoji: undefined })}
                  >
                    Sin emoji
                  </button>
                  {QUICK_EMOJIS.map((em) => (
                    <button
                      key={em}
                      className={highlights[selected].emoji === em ? "active" : ""}
                      onClick={() => updateSelected({ emoji: em })}
                    >
                      {em}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {exportUrl && (
              <a href={exportUrl} download={`editado.${exportExt}`}>
                <button className="primary">Descargar video</button>
              </a>
            )}

            {words.length > 0 && activeClip === null && (
              <div className="clips">
                <div className="row">
                  <strong>Clips cortos</strong>
                  <label>
                    Duración{" "}
                    <select value={clipLength} onChange={(e) => setClipLength(e.target.value)}>
                      <option value="corto">15–30 s</option>
                      <option value="medio">30–60 s</option>
                      <option value="largo">60–90 s</option>
                    </select>
                  </label>
                  <label>
                    Cantidad{" "}
                    <select value={clipCount} onChange={(e) => setClipCount(Number(e.target.value))}>
                      {[3, 5, 8].map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button onClick={findClips} disabled={busy || playing}>
                    {clips.length ? "Buscar otra vez" : "Buscar clips"}
                  </button>
                  {clips.length > 1 && (
                    <button onClick={() => exportClips(clips.map((_, i) => i))} disabled={busy || playing}>
                      Exportar todos
                    </button>
                  )}
                </div>
                {clips.map((c, i) => (
                  <div key={i} className="clip-card">
                    <div className="row">
                      <span className="clip-score" title="Potencial viral (1–100)">
                        {c.score}
                      </span>
                      <strong>{c.title}</strong>
                    </div>
                    <div className="status">
                      #{i + 1} · {formatTime(c.start)}–{formatTime(c.end)} ({Math.round(c.end - c.start)} s)
                      {c.edit ? " · editado" : ""}
                      {c.reason ? ` · ${c.reason}` : ""}
                    </div>
                    <div className="row">
                      <button onClick={() => openClip(i)} disabled={busy || playing}>
                        Editar
                      </button>
                      <button onClick={() => exportClips([i])} disabled={busy || playing}>
                        Exportar
                      </button>
                      {c.exportUrl && (
                        <a href={c.exportUrl} download={`clip-${i + 1}.mp4`}>
                          <button className="primary">Descargar</button>
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <WordList words={words} onChange={changeWord} onSeek={stableSeek} />
          </>
        )}

        <div className="status">{status}</div>
      </div>
    </div>
  );
}

function formatTime(t: number) {
  const m = Math.floor(t / 60);
  const sec = Math.floor(t % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}
