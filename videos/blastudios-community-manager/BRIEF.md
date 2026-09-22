---
workflow: product-launch-video
flow: automation
storyboard: no
message: "Llevar tú el Instagram de tu negocio cuesta 90 horas al mes; nosotros lo llevamos por ti"
destination: instagram-reels
aspect: 1080x1920
language: es
audience: "Dueños de negocio local en España (hostelería, retail, estética, clínicas, servicios), 28-55 años, que ya facturan y llevan ellos mismos el Instagram"
length: 30s
angle: cost-of-doing-it-yourself
style_preset: blue-professional
---

## Intent

Reel de venta del servicio de **Community Manager** de blastudios. El ángulo no es
"hacemos contenido bonito" — es el **coste de oportunidad**: llevar tú el Instagram
te cuesta 3 horas al día / 90 horas al mes que no dedicas a vender. Primero se
cuantifica el dolor con números concretos, se remata con el coste real, y solo
entonces aparece el servicio como el sistema que lo resuelve.

Tono blastudios: directo, sin humo, seguro. La línea de la web — "No es suerte, es
sistema" — es la brújula. Tipografía cinética sobre negro, ritmo rápido, cero
plantilla genérica de agencia.

Pensado para verse **en silencio**: todo el mensaje está en pantalla.

## Customizations

- Contador digital que sube de 0:00 a 3:04 en el hook — el número ES el gancho.
- Giro cromático como bisagra narrativa: melocotón #F4BA95 en las escenas de dolor,
  azul eléctrico #2563EB a partir de la solución. Nunca se mezclan.
- Cierre con el teléfono real de blastudios (648 021 435) y CTA "Escribe CM por DM".
- Logo blastudios discreto en la esquina durante todo el reel.

## Notes

- **Marca (fuente de verdad: `index.html` del repo, no scraping):** fondo #000000,
  azul primario #2563EB, azul profundo #0D1F3C, texto #F5F5F7, secundario #98989F,
  acento terciario #F4BA95. Titulares Space Grotesk 700 (-0.03em), cuerpo Inter.
  Etiquetas en mayúscula: Inter 600, 0.14em.
- **Modo sin captura:** los tokens de marca se toman del código fuente del repo, que
  es más exacto que rastrear el sitio desplegado (la home es una SPA con loader).
- **Vídeo mudo por decisión técnica:** no hay sesión de HeyGen en este entorno y los
  engines locales (Kokoro TTS / MusicGen) no tienen dependencias instaladas. El reel
  se entrega sin pista de audio para que se le ponga audio de tendencia al publicar
  en Instagram, que además es lo que favorece el alcance.
- **No inventar métricas de clientes.** La única prueba social permitida es mencionar
  a Küme Pastelería, que es un caso real documentado en `marketing/`.
- Los "16 piezas al mes" y el desglose de horas son la propuesta comercial a validar
  por Bautista antes de publicar; son argumentos, no datos auditados.
- Texto dentro del 85% central: la UI de Instagram come los bordes.
