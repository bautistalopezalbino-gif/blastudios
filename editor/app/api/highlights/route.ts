import { NextResponse } from "next/server";
import { heuristicHighlights, spaceOut } from "@/lib/highlights";
import type { Highlight, Word } from "@/lib/types";

export const runtime = "nodejs";

const PROMPT = `Eres editor de videos cortos para TikTok y Reels.
Recibes la transcripción numerada palabra a palabra. Elige los momentos clave:
- "zoom": palabras de mayor énfasis (revelaciones, cifras, remates). Como mucho uno cada 3 segundos.
- "emoji": un emoji que refuerce lo que se dice en esa palabra. Como mucho uno cada 3 segundos.
Responde solo con JSON: {"highlights":[{"index":<número de palabra>,"zoom":true|false,"emoji":"<emoji o vacío>"}]}`;

/**
 * Recibe las palabras y devuelve los momentos destacados.
 * Con OPENAI_API_KEY los elige un LLM; sin ella (o si falla) usa una heurística por palabras clave.
 */
export async function POST(req: Request) {
  const { words } = (await req.json()) as { words: Word[] };
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey || !words.length) {
    return NextResponse.json({ highlights: heuristicHighlights(words), source: "heuristic" });
  }

  try {
    const transcript = words.map((w, i) => `${i}[${w.start.toFixed(1)}s] ${w.text}`).join("\n");
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || "gpt-4o-mini",
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: PROMPT },
          { role: "user", content: transcript },
        ],
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const parsed = JSON.parse(data.choices[0].message.content) as {
      highlights: { index: number; zoom?: boolean; emoji?: string }[];
    };
    const highlights: Highlight[] = parsed.highlights
      .filter((h) => words[h.index])
      .map((h) => ({ time: words[h.index].start, zoom: !!h.zoom, emoji: h.emoji || undefined }));
    return NextResponse.json({ highlights: spaceOut(highlights), source: "llm" });
  } catch (e) {
    console.error("highlights:", e);
    return NextResponse.json({ highlights: heuristicHighlights(words), source: "heuristic" });
  }
}
