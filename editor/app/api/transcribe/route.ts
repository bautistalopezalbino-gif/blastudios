import { NextResponse } from "next/server";
import type { Word } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Recibe el audio/video y devuelve las palabras con su marca de tiempo.
 * Sin OPENAI_API_KEY responde con una transcripción de demo para poder probar la interfaz.
 */
export async function POST(req: Request) {
  const form = await req.formData();
  const file = form.get("file");
  const duration = Number(form.get("duration")) || 10;
  if (!(file instanceof Blob)) {
    return NextResponse.json({ error: "Falta el archivo" }, { status: 400 });
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return NextResponse.json({ words: demoWords(duration), demo: true });

  const body = new FormData();
  body.append("file", file, "audio.mp4");
  body.append("model", "whisper-1");
  body.append("response_format", "verbose_json");
  body.append("timestamp_granularities[]", "word");

  const res = await fetch("https://api.openai.com/v1/audio/transcriptions", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body,
  });
  if (!res.ok) {
    return NextResponse.json({ error: `Error al transcribir: ${await res.text()}` }, { status: 502 });
  }
  const data = (await res.json()) as { words?: { word: string; start: number; end: number }[] };
  const words: Word[] = (data.words ?? []).map((w) => ({ text: w.word.trim(), start: w.start, end: w.end }));
  return NextResponse.json({ words, demo: false });
}

function demoWords(duration: number): Word[] {
  const text =
    "Esta es una transcripción de demo. Añade tu clave de OpenAI para ver tus propias palabras aquí.".split(" ");
  const step = duration / text.length;
  return text.map((t, i) => ({ text: t, start: i * step, end: (i + 1) * step - 0.05 }));
}
