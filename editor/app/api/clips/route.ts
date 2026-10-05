import { NextResponse } from "next/server";
import { finalizeClips, heuristicClips, toSentences, type ClipCandidate, type ClipOptions } from "@/lib/clips";
import { askJson } from "@/lib/llm";
import type { Word } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

const prompt = ({ min, max, count }: ClipOptions) => `Eres editor de clips virales para TikTok, Reels y Shorts.
Recibes la transcripción de un video largo, numerada por frases con su tiempo de inicio y fin.
Elige los ${count} mejores fragmentos para publicar como clips independientes:
- Cada clip dura entre ${min} y ${max} segundos (calcúlalo con los tiempos).
- Empieza con un gancho fuerte (una pregunta, una afirmación sorprendente, una cifra) y se entiende sin contexto.
- Contiene una idea completa y termina en una frase cerrada.
- No se solapan entre sí.
Para cada clip da un título corto y llamativo (máx. 60 caracteres, en el idioma del video), el motivo y una puntuación de 1 a 100 de su potencial viral.
Responde solo con JSON: {"clips":[{"start":<nº de la primera frase>,"end":<nº de la última frase>,"title":"...","reason":"...","score":<1-100>}]}`;

/**
 * Recibe las palabras del video y devuelve los mejores clips cortos.
 * Los elige Gemini u OpenAI (ver lib/llm.ts); sin clave, o si falla, una heurística.
 */
export async function POST(req: Request) {
  const { words, min = 30, max = 60, count = 5 } = (await req.json()) as { words: Word[] } & Partial<ClipOptions>;
  const opts = { min, max, count };
  const sentences = toSentences(words);
  if (!sentences.length) return NextResponse.json({ clips: [], source: "heuristic" });
  try {
    const transcript = sentences
      .map((s, i) => `${i} [${s.start.toFixed(1)}-${s.end.toFixed(1)}s] ${s.text}`)
      .join("\n");
    const answer = await askJson<{ clips: ClipCandidate[] }>(prompt(opts), transcript);
    if (answer) {
      const clips = finalizeClips(answer.data.clips ?? [], sentences, opts);
      if (clips.length) return NextResponse.json({ clips, source: answer.source });
    }
  } catch (e) {
    console.error("clips:", e);
  }
  return NextResponse.json({ clips: heuristicClips(sentences, opts), source: "heuristic" });
}
