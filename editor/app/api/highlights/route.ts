import { NextResponse } from "next/server";
import { heuristicHighlights, spaceOut } from "@/lib/highlights";
import { askJson } from "@/lib/llm";
import type { Highlight, Word } from "@/lib/types";

export const runtime = "nodejs";
export const maxDuration = 60;

const PROMPT = `Eres editor de videos cortos para TikTok y Reels.
Recibes la transcripción numerada palabra a palabra. Elige los momentos clave:
- "zoom": palabras de mayor énfasis (revelaciones, cifras, remates). Como mucho uno cada 3 segundos.
- "emoji": un emoji que refuerce lo que se dice en esa palabra. Como mucho uno cada 3 segundos.
Responde solo con JSON: {"highlights":[{"index":<número de palabra>,"zoom":true|false,"emoji":"<emoji o vacío>"}]}`;

type LlmHighlight = { index: number; zoom?: boolean; emoji?: string };

/**
 * Recibe las palabras y devuelve los momentos destacados.
 * Los elige Gemini u OpenAI (ver lib/llm.ts); sin clave, o si falla, usa una heurística.
 */
export async function POST(req: Request) {
  const { words } = (await req.json()) as { words: Word[] };
  if (!words.length) return NextResponse.json({ highlights: [], source: "heuristic" });
  try {
    const transcript = words.map((w, i) => `${i}[${w.start.toFixed(1)}s] ${w.text}`).join("\n");
    const answer = await askJson<{ highlights: LlmHighlight[] }>(PROMPT, transcript);
    if (!answer) return NextResponse.json({ highlights: heuristicHighlights(words), source: "heuristic" });
    const highlights: Highlight[] = (answer.data.highlights ?? [])
      .filter((h) => words[h.index])
      .map((h) => ({ time: words[h.index].start, zoom: !!h.zoom, emoji: h.emoji || undefined }));
    return NextResponse.json({ highlights: spaceOut(highlights), source: answer.source });
  } catch (e) {
    console.error("highlights:", e);
    return NextResponse.json({ highlights: heuristicHighlights(words), source: "heuristic" });
  }
}
