/**
 * Pide una respuesta JSON a un LLM: Gemini (GEMINI_API_KEY) u OpenAI (OPENAI_API_KEY).
 * Solo para el servidor. Devuelve null si no hay ninguna clave configurada.
 */
export async function askJson<T>(system: string, user: string): Promise<{ data: T; source: string } | null> {
  const gemini = process.env.GEMINI_API_KEY;
  const openai = process.env.OPENAI_API_KEY;
  if (gemini) return { data: (await askGemini(gemini, system, user)) as T, source: "gemini" };
  if (openai) return { data: (await askOpenAI(openai, system, user)) as T, source: "openai" };
  return null;
}

async function askGemini(apiKey: string, system: string, user: string): Promise<unknown> {
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
    method: "POST",
    headers: { "x-goog-api-key": apiKey, "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: "user", parts: [{ text: user }] }],
      generationConfig: { responseMimeType: "application/json" },
    }),
  });
  if (!res.ok) throw new Error(`Gemini ${res.status}: ${await res.text()}`);
  const data = await res.json();
  const text: string = data.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? "").join("") ?? "";
  return JSON.parse(text);
}

async function askOpenAI(apiKey: string, system: string, user: string): Promise<unknown> {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
    }),
  });
  if (!res.ok) throw new Error(`OpenAI ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return JSON.parse(data.choices[0].message.content);
}
