import { NextResponse } from "next/server";
import type { Word } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

/**
 * Recibe un bloque de audio (WAV, ≤ 2 min) y devuelve las palabras con su marca de tiempo usando Whisper de OpenAI.
 * Sin OPENAI_API_KEY responde 501 y el cliente transcribe en el navegador.
 */
export async function POST(req: Request) {
  const form = await req.formData();
  const file = form.get("file");
  if (!(file instanceof Blob)) {
    return NextResponse.json({ error: "Falta el archivo" }, { status: 400 });
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return NextResponse.json({ error: "no_key" }, { status: 501 });

  const body = new FormData();
  body.append("file", file, file instanceof File && file.name ? file.name : "audio.wav");
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
  return NextResponse.json({ words });
}
