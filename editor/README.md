# Blastudios Editor (MVP)

Editor automático de videos verticales, inspirado en herramientas como ViroEdit/Submagic.

**Qué hace**
1. Subes un video (máx. 180 s).
2. Detecta los silencios en el navegador (Web Audio, volumen RMS) y los recorta.
3. Transcribe con Whisper (`/api/transcribe`) y obtiene la marca de tiempo de cada palabra.
4. Dibuja subtítulos animados (estilos TikTok, Karaoke y Minimal) sobre un canvas 9:16.
5. Exporta en el navegador (MediaRecorder, MP4 o WebM según el navegador).

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
- `lib/render.ts`: dibujo del fotograma y de los subtítulos
- `app/api/transcribe/route.ts`: proxy a Whisper (OpenAI)

## Siguientes pasos

- Seguimiento facial con MediaPipe (encuadre y subtítulos que no tapen la cara)
- Zooms y emojis en los momentos clave elegidos por un LLM
- Exportación más rápida que el tiempo real con WebCodecs y `mp4-muxer`
- Cuentas, créditos y pagos (Supabase y Stripe)

## Despliegue

Es independiente del sitio estático de la raíz. En Vercel, crea otro proyecto con *Root Directory* = `editor`.
