import { NextResponse } from "next/server";
import { heuristicHighlights, spaceOut } from "@/lib/highlights";
import type { Highlight, Word } from "@/lib/types";

export const runtime = "nodejs";

const PROMPT = `Eres editor de videos cortos para TikTok y Reels.
Recibes la transcripción numerada palabra a palabra. Elige los momentos clave:
- "zoom": palabras de mayor énfasis (revelaciones, cifras, remates). Como mucho uno cada 3 segundos.
- "emoji": un emoji que refuerce lo que se dice en esa palabra. Como mucho uno cada 3 segundos.
Responde solo con JSON: {"highlights":[{"index":<número de palabra>,"zoom":true|false,"emoji":"<emoji o vacío>"}]}`;

type LlmHighlight = { index: number; zoom?: boolean; emoji?: string };

/**
 * Recibe las palabras y devuelve los momentos destacados.
 * Los elige Gemini (GEMINI_API_KEY) u OpenAI (OPENAI_API_KEY); sin clave, o si falla, usa una heurística.
 */
export async function POST(req: Request) {
  const { words } = (await req.json()) as { words: Word[] };
  const gemini = process.env.GEMINI_API_KEY;
  const openai = process.env.OPENAI_API_KEY;
  if ((!gemini && !openai) || !words.length) {
    return NextResponse.json({ highlights: heuristicHighlights(words), source: "heuristic" });
  }

  try {
    const transcript = words.map((w, i) => `${i}[${w.start.toFixed(1)}s] ${w.text}`).join("\n");
    const parsed = gemini ? await askGemini(gemini, transcript) : await askOpenAI(openai!, transcript);
    const highlights: Highlight[] = parsed
      .filter((h) => words[h.index])
      .map((h) => ({ time: words[h.index].start, zoom: !!h.zoom, emoji: h.emoji || undefined }));
    return NextResponse.json({ highlights: spaceOut(highlights), source: gemini ? "gemini" : "openai" });
  } catch (e) {
    console.error("highlights:", e);
    return NextResponse.json({ highlights: heuristicHighlights(words), source: "heuristic" });
  }
}

async function askGemini(apiKey: string, transcript: string): Promise<LlmHighlight[]> {
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
    method: "POST",
    headers: { "x-goog-api-key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: PROMPT }] },
      contents: [{ role: "user", parts: [{ text: transcript }] }],
      generationConfig: { responseMimeType: "application/json" },
    }),
  });
  if (!res.ok) throw new Error(`Gemini ${res.status}: ${await res.text()}`);
  const data = await res.json();
  const text: string = data.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? "").join("") ?? "";
  return (JSON.parse(text) as { highlights: LlmHighlight[] }).highlights ?? [];
}

async function askOpenAI(apiKey: string, transcript: string): Promise<LlmHighlight[]> {
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
  if (!res.ok) throw new Error(`OpenAI ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return (JSON.parse(data.choices[0].message.content) as { highlights: LlmHighlight[] }).highlights ?? [];
}
