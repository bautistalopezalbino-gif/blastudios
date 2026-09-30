# Blastudios Editor (MVP)

Editor automático de videos verticales, inspirado en herramientas como ViroEdit/Submagic.

**Qué hace**
1. Subes un video (máx. 180 s).
2. Detecta los silencios en el navegador (Web Audio, volumen RMS) y los recorta.
3. Transcribe con Whisper (`/api/transcribe`) y obtiene la marca de tiempo de cada palabra.
4. Dibuja subtítulos animados (estilos TikTok, Karaoke y Minimal) sobre un canvas 9:16.
5. Sigue la cara con MediaPipe: el recorte 9:16 la mantiene centrada (útil con videos horizontales) y los subtítulos suben si la taparían.
6. Zooms y emojis automáticos en los momentos clave (`/api/highlights`): los elige un LLM si hay `OPENAI_API_KEY`; si no, una heurística por palabras clave.
7. Exporta a MP4 en el navegador con WebCodecs ([Mediabunny](https://mediabunny.dev)), fotograma a fotograma y más rápido que el tiempo real. Usa H.264 + AAC si el navegador los tiene (Chrome, Edge, Safari) y, si no, VP9 + Opus. Sin WebCodecs, graba en tiempo real con MediaRecorder.

## Arrancar

```bash
cd editor
npm install
cp .env.example .env.local   # añade OPENAI_API_KEY (sin ella se usa una transcripción de demo)
npm run dev
```

## Estructura

- `components/Editor.tsx`: interfaz, vista previa y exportación
- `lib/silence.ts`: detección de silencios
- `lib/timeline.ts`: tramos, agrupación de palabras en subtítulos
- `lib/face.ts`: detección y suavizado de la posición de la cara
- `lib/highlights.ts`: heurística de momentos clave y animación de zooms y emojis
- `lib/export.ts`: exportación rápida (decodifica, dibuja y codifica cada fotograma; corta el audio por tramos)
- `lib/render.ts`: dibujo del fotograma y de los subtítulos
- `app/api/transcribe/route.ts`: proxy a Whisper (OpenAI)
- `app/api/highlights/route.ts`: elige zooms y emojis (LLM o heurística)

## Siguientes pasos

- Modelo de cara de largo alcance: el actual (`blaze_face_short_range`) solo detecta caras cercanas, tipo selfie
- Editar a mano los zooms y emojis (añadir, quitar, cambiar el emoji)
- Efectos de sonido sincronizados con los zooms
- Cuentas, créditos y pagos (Supabase y Stripe)

El WASM de MediaPipe se copia a `public/mediapipe/wasm` al hacer `npm install` y el modelo está en `public/mediapipe/`, así que no depende de ninguna CDN.

## Despliegue

Es independiente del sitio estático de la raíz. En Vercel, crea otro proyecto con *Root Directory* = `editor`.
