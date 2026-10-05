# Blastudios Editor (MVP)

Editor automático de videos verticales, inspirado en herramientas como ViroEdit/Submagic.

**Qué hace**
1. Subes un video de hasta 30 minutos.
2. Extrae el audio una sola vez, por trozos y en mono a 16 kHz (~115 MB para 30 min), y detecta los silencios para recortarlos.
3. Transcribe con Whisper por bloques de hasta 2 minutos cortados en silencios, con marcas de tiempo por palabra: en el navegador (Transformers.js, sin clave; el modelo de ~77 MB se descarga la primera vez) o en el servidor con OpenAI si hay `OPENAI_API_KEY` (cada bloque viaja como WAV de ≤ 3,8 MB, dentro del límite de Vercel).
4. Dibuja subtítulos animados sobre un canvas 9:16 con 8 estilos (TikTok, Hormozi, MrBeast, Caja, Karaoke, Neón, Editorial y Minimal) y colores de marca personalizables, que se recuerdan en el navegador. Las fuentes van incluidas con `@fontsource` (sin Google Fonts en tiempo de ejecución).
5. Sigue la cara con MediaPipe: el recorte 9:16 la mantiene centrada (útil con videos horizontales) y los subtítulos suben si la taparían.
6. Zooms y emojis automáticos en los momentos clave (`/api/highlights`): los elige Gemini (`GEMINI_API_KEY`) u OpenAI; si no hay clave, una heurística por palabras clave.
7. Efectos de sonido generados con Web Audio (sin archivos): un "whoosh" justo antes de cada zoom y un "pop" con cada emoji. Suenan en la vista previa y se mezclan en el audio exportado, con volumen ajustable.
8. Editor visual: línea de tiempo con los tramos (clic para quitar o recuperar), "Cortar aquí" para dividir un tramo, marcadores de zoom y emoji que se arrastran y se editan (zoom sí/no, emoji, eliminar), "Deshacer" (Ctrl+Z) y Supr para borrar el seleccionado.
9. Exporta a MP4 en el navegador con WebCodecs ([Mediabunny](https://mediabunny.dev)), fotograma a fotograma y más rápido que el tiempo real. Usa H.264 + AAC si el navegador los tiene (Chrome, Edge, Safari) y, si no, VP9 + Opus. El audio se decodifica y codifica por trozos, intercalado con el video. Si el montaje dura más de 3 minutos y el navegador lo permite (Chrome, Edge), el MP4 se escribe directamente en un archivo elegido por el usuario, así que la memoria no crece con la duración. Sin WebCodecs, graba en tiempo real con MediaRecorder.

## Arrancar

```bash
cd editor
npm install
cp .env.example .env.local   # opcional: GEMINI_API_KEY / OPENAI_API_KEY
npm run dev
```

## Estructura

- `components/Editor.tsx`: interfaz, vista previa, edición y exportación
- `components/Timeline.tsx`: línea de tiempo (tramos, cortes, marcadores, cabezal)
- `lib/edit.ts`: operaciones de edición de tramos (dividir, quitar, recuperar)
- `lib/silence.ts`: detección de silencios
- `lib/timeline.ts`: tramos, agrupación de palabras en subtítulos
- `lib/face.ts`: detección y suavizado de la posición de la cara
- `lib/highlights.ts`: heurística de momentos clave y animación de zooms y emojis
- `lib/export.ts`: exportación rápida (decodifica, dibuja y codifica cada fotograma; corta el audio por tramos)
- `lib/audio.ts`: extracción del audio a 16 kHz y codificación WAV
- `lib/transcribe.ts`: transcripción por bloques (servidor o navegador)
- `lib/whisper.ts`, `lib/whisper.worker.ts`: transcripción de un bloque en el navegador en un Web Worker
- `components/WordList.tsx`: lista de palabras editable (memorizada para videos largos)
- `lib/sfx.ts`: generación, reproducción y mezcla de los efectos de sonido
- `lib/captions.ts`: estilos de subtítulos (fuente, colores, resaltado, animación) y su dibujo
- `lib/render.ts`: dibujo del fotograma, del emoji y colocación de los subtítulos
- `app/api/transcribe/route.ts`: proxy a Whisper de OpenAI (responde 501 sin clave)
- `app/api/highlights/route.ts`: elige zooms y emojis (Gemini, OpenAI o heurística)

## Siguientes pasos

- Modelo de cara de largo alcance: el actual (`blaze_face_short_range`) solo detecta caras cercanas, tipo selfie
- Editar los subtítulos en la línea de tiempo (mover y ajustar la duración de las palabras)
- Más efectos de sonido (ding en cifras, impacto en remates) y música de fondo
- Cuentas, créditos y pagos (Supabase y Stripe)

El WASM de MediaPipe se copia a `public/mediapipe/wasm` al hacer `npm install` y el modelo está en `public/mediapipe/`, así que no depende de ninguna CDN.

## Despliegue

Es independiente del sitio estático de la raíz. En Vercel, crea otro proyecto con *Root Directory* = `editor`.
