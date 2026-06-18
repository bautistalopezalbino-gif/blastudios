"""
Reel Blastudios — "5 automatizaciones que te ahorran 10 horas a la semana"
Formato vertical 9:16 (1080x1920), 30fps, ~68s.

Estética Blastudios:
  - Fondo #0A0A0F con acentos neón azul #4DAAFF e índigo/violeta
  - Space Grotesk (texto principal) / Space Mono (datos/código)
  - Animaciones easing, blobs de acento, motif de nodos (flujo de automatización)

Stack: PIL + numpy para frames, imageio-ffmpeg para encode. Audio ambiental
generado con numpy (sin dependencia de red).  Sin voz en off (TTS bloqueado
por la red del entorno) — pensado para añadir trending audio en Instagram.
"""

import os, math, subprocess, wave
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import imageio_ffmpeg

# ── Rutas ─────────────────────────────────────────────────────────────────────
DIR    = os.path.dirname(os.path.abspath(__file__))
FONTS  = os.path.join(DIR, "fonts")
OUT    = os.path.join(DIR, "reel_blastudios_5_automatizaciones.mp4")
TMP_V  = os.path.join(DIR, "_tmp_5auto_video.mp4")
TMP_A  = os.path.join(DIR, "_tmp_5auto_audio.wav")

F_GROTESK = os.path.join(FONTS, "SpaceGrotesk.ttf")
F_MONO    = os.path.join(FONTS, "SpaceMono-Regular.ttf")
F_MONO_B  = os.path.join(FONTS, "SpaceMono-Bold.ttf")

# ── Dimensiones ───────────────────────────────────────────────────────────────
W, H = 1080, 1920
FPS  = 30

# ── Paleta (web blastudios.vercel.app) ────────────────────────────────────────
BG      = (10, 10, 15)        # #0A0A0F
PANEL   = (18, 19, 28)        # cards
NEON    = (77, 170, 255)      # #4DAAFF azul neón
BLUE    = (37, 99, 235)       # #2563EB azul Blastudios
VIOLET  = (124, 92, 255)      # índigo/violeta
WHITE   = (245, 245, 247)     # #F5F5F7
GRAY    = (150, 156, 175)
DGRAY   = (95, 100, 120)
GREEN   = (52, 211, 153)

# ── Fuentes ───────────────────────────────────────────────────────────────────
@lru_cache(maxsize=256)
def grotesk(size, weight=500):
    f = ImageFont.truetype(F_GROTESK, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f

@lru_cache(maxsize=128)
def mono(size, bold=False):
    return ImageFont.truetype(F_MONO_B if bold else F_MONO, size)

# ── Helpers ───────────────────────────────────────────────────────────────────
def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3

def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return 0.5 * (1 - math.cos(math.pi * t))

def spring(t, overshoot=1.12):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3 * math.cos(t * math.pi * 1.5) * 0 + (1 - (1 - t) ** 2) * 0 + ease_out_cubic(t) * overshoot - (overshoot - 1) * ease_out_cubic(t) ** 1.5

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))

def text_w(draw, s, font):
    b = draw.textbbox((0, 0), s, font=font)
    return b[2] - b[0]

def text_h(draw, s, font):
    b = draw.textbbox((0, 0), s, font=font)
    return b[3] - b[1]

def draw_text_center(draw, cx, y, s, font, fill, anchor="ma"):
    draw.text((cx, y), s, font=font, fill=fill, anchor=anchor)

def rounded(draw, box, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def wrap(draw, s, font, max_w):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_w(draw, test, font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ── Fondo con blob de acento + grid de puntos (cacheado por escena) ───────────
@lru_cache(maxsize=16)
def make_bg(accent, blob_x, blob_y):
    img = Image.new("RGB", (W, H), BG)
    # blob radial de acento (glow)
    blob = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(blob)
    R = 560
    bd.ellipse([blob_x - R, blob_y - R, blob_x + R, blob_y + R], fill=255)
    blob = blob.filter(ImageFilter.GaussianBlur(220))
    arr = np.asarray(blob, dtype=np.float32) / 255.0
    base = np.asarray(img, dtype=np.float32)
    acc = np.array(accent, dtype=np.float32)
    glow = (arr[..., None] * 0.16) * acc[None, None, :]
    out = np.clip(base + glow, 0, 255).astype(np.uint8)
    img = Image.fromarray(out, "RGB")
    # grid de puntos sutil
    d = ImageDraw.Draw(img, "RGBA")
    step = 86
    for gy in range(60, H, step):
        for gx in range(40, W, step):
            d.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=(255, 255, 255, 12))
    # viñeta inferior para legibilidad
    vg = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vg)
    vd.rectangle([0, H - 520, W, H], fill=90)
    vg = vg.filter(ImageFilter.GaussianBlur(160))
    va = np.asarray(vg, np.float32) / 255.0
    out2 = np.asarray(img, np.float32) * (1 - va[..., None] * 0.55)
    return Image.fromarray(np.clip(out2, 0, 255).astype(np.uint8), "RGB")

# ── Motif de nodos (flujo de automatización) ─────────────────────────────────
def draw_flow(draw, cx, y, accent, phase, n=3, gap=150):
    """Pequeña fila de nodos conectados que 'pulsa' de izq a der."""
    total = gap * (n - 1)
    x0 = cx - total // 2
    pts = [(x0 + i * gap, y) for i in range(n)]
    for i in range(n - 1):
        draw.line([pts[i], pts[i + 1]], fill=(*DGRAY, 160), width=4)
    # pulso viajando
    seg = (phase * (n - 1)) % (n - 1)
    si = int(seg)
    f = seg - si
    px = pts[si][0] + (pts[si + 1][0] - pts[si][0]) * f
    draw.ellipse([px - 7, y - 7, px + 7, y + 7], fill=(*accent, 255))
    for i, (x, yy) in enumerate(pts):
        rr = 22
        draw.ellipse([x - rr, yy - rr, x + rr, yy + rr], fill=(16, 18, 28, 255),
                     outline=(*accent, 255), width=4)
        draw.ellipse([x - 6, yy - 6, x + 6, yy + 6], fill=(*accent, 255))

# ── Barra de progreso global + etiqueta sección ──────────────────────────────
def draw_header(draw, t, total, label, accent):
    # logotipo textual
    draw.text((54, 70), "BLA", font=grotesk(40, 700), fill=WHITE)
    draw.text((54 + text_w(draw, "BLA", grotesk(40, 700)), 70), "STUDIOS",
              font=grotesk(40, 700), fill=accent)
    # barra de progreso
    bx0, bx1, by = 54, W - 54, 138
    draw.rounded_rectangle([bx0, by, bx1, by + 8], radius=4, fill=(255, 255, 255, 30))
    p = max(0.0, min(1.0, t / total))
    draw.rounded_rectangle([bx0, by, bx0 + int((bx1 - bx0) * p), by + 8], radius=4, fill=accent)
    # etiqueta de sección (mono)
    draw.text((W - 54, 74), label, font=mono(26, True), fill=GRAY, anchor="ra")

def chip(draw, x, y, label, accent, mono_size=30, padx=22, pady=14):
    w = text_w(draw, label, mono(mono_size, True))
    box = [x, y, x + w + padx * 2, y + mono_size + pady * 2]
    draw.rounded_rectangle(box, radius=18, fill=(255, 255, 255, 14),
                           outline=(*accent, 150), width=3)
    draw.text((x + padx, y + pady - 4), label, font=mono(mono_size, True), fill=accent)
    return box[2] - box[0]

# ── Contenido ────────────────────────────────────────────────────────────────
TOTAL = 68.0  # segundos

AUTOS = [
    dict(n="01", name="Captura de leads → CRM",
         desc="DM o formulario entra, ficha creada sola.",
         tools=["MAKE", "NOTION"], save="2 h",
         flow=3, accent=NEON,
         steps=["FORM / DM", "ENRIQUECER", "FICHA NOTION"]),
    dict(n="02", name="Propuestas con IA",
         desc="Lead aprobado, propuesta lista en PDF.",
         tools=["ZAPIER", "NOTION AI"], save="2,5 h",
         flow=3, accent=VIOLET,
         steps=["LEAD OK", "IA REDACTA", "PDF ENVIADO"]),
    dict(n="03", name="Onboarding de clientes",
         desc="Cobro hecho, espacio y bienvenida listos.",
         tools=["MAKE", "STRIPE", "NOTION"], save="2 h",
         flow=3, accent=BLUE,
         steps=["PAGO STRIPE", "CREA ESPACIO", "EMAIL AUTO"]),
    dict(n="04", name="Clips y reposting",
         desc="Subtítulos y recorte, programado solo.",
         tools=["CAPCUT", "MAKE", "BUFFER"], save="2 h",
         flow=3, accent=NEON,
         steps=["RAW CLIP", "SUBS + CUT", "PROGRAMA"]),
    dict(n="05", name="Reporting semanal",
         desc="Métricas resumidas por IA y enviadas.",
         tools=["MAKE", "GA4", "NOTION AI"], save="1,5 h",
         flow=3, accent=VIOLET,
         steps=["GA4 DATA", "IA RESUME", "INFORME"]),
]

# ── Render por escena ─────────────────────────────────────────────────────────
def frame_hook(t):
    accent = NEON
    img = make_bg(accent, 540, 760).copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_header(d, t, TOTAL, "HOOK", accent)
    # dato grande mono que sube
    a = ease_out_cubic(t / 0.5)
    dy = int((1 - a) * 40)
    d.text((54, 560 + dy), "− 10 h", font=grotesk(190, 700), fill=(*WHITE, int(255 * a)))
    d.text((54, 760 + dy), "/ SEMANA", font=mono(64, True), fill=(*accent, int(255 * a)))
    # frase de impacto, palabra por palabra
    words = ["Pierdes", "10", "horas", "cada", "semana", "en", "tareas", "manuales."]
    a2 = ease_out_cubic((t - 0.4) / 1.4)
    show = int(len(words) * a2 + 0.001)
    line = " ".join(words[:max(0, show)])
    for ln_i, ln in enumerate(wrap(d, line, grotesk(58, 600), W - 108)):
        d.text((54, 980 + ln_i * 72), ln, font=grotesk(58, 600), fill=WHITE)
    return img

def frame_promesa(t):
    accent = VIOLET
    img = make_bg(accent, 540, 700).copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_header(d, 3 + t, TOTAL, "PROMESA", accent)
    a = ease_out_cubic(t / 0.5)
    d.text((54, 600), "En 60 segundos:", font=mono(40, True), fill=(*accent, int(255 * a)))
    big = "5 automatizaciones reales"
    for i, ln in enumerate(wrap(d, big, grotesk(96, 700), W - 108)):
        yy = 680 + i * 108
        dy = int((1 - ease_out_cubic((t - 0.15 - i * 0.1) / 0.5)) * 36)
        d.text((54, yy + dy), ln, font=grotesk(96, 700), fill=WHITE)
    sub = "Make · Zapier · Notion AI · CapCut. Plug & play."
    a3 = ease_out_cubic((t - 0.6) / 0.6)
    for i, ln in enumerate(wrap(d, sub, grotesk(46, 500), W - 108)):
        d.text((54, 1020 + i * 60), ln, font=grotesk(46, 500), fill=(*GRAY, int(255 * a3)))
    draw_flow(d, 540, 1320, accent, (t * 0.6) % 1.0, n=4)
    return img

def frame_auto(idx, t, local_dur):
    a = AUTOS[idx]
    accent = a["accent"]
    img = make_bg(accent, 540, 520).copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_header(d, 7 + idx * 9 + t, TOTAL, f"{idx+1}/5", accent)

    # número gigante de fondo (watermark, encima de la cabecera)
    ap = ease_out_cubic(t / 0.45)
    d.text((W - 54, 168), a["n"], font=grotesk(230, 700), fill=(*accent, int(22 * ap)), anchor="ra")

    # badge número
    by = 360
    d.rounded_rectangle([54, by, 54 + 130, by + 90], radius=22, fill=(*accent, 40),
                        outline=(*accent, 220), width=4)
    d.text((54 + 65, by + 12), a["n"], font=grotesk(58, 700), fill=accent, anchor="ma")

    # nombre (slide-up)
    dy = int((1 - ease_out_cubic(t / 0.5)) * 40)
    name_y = 500
    for i, ln in enumerate(wrap(d, a["name"], grotesk(82, 700), W - 108)):
        d.text((54, name_y + i * 92 + dy), ln, font=grotesk(82, 700), fill=WHITE)

    # descripción
    a2 = ease_out_cubic((t - 0.3) / 0.5)
    d.text((54, 720), a["desc"], font=grotesk(42, 500), fill=(*GRAY, int(255 * a2)))

    # chips de herramientas (stagger)
    cx = 54
    cy = 810
    for i, tname in enumerate(a["tools"]):
        ca = ease_out_cubic((t - 0.4 - i * 0.12) / 0.4)
        if ca <= 0:
            continue
        wdt = chip(d, cx, cy, tname, accent, mono_size=30)
        cx += wdt + 18

    # flujo de nodos con etiquetas (motif central)
    flow_y = 1120
    fgap = 320
    draw_flow(d, 540, flow_y, accent, (t * 0.7) % 1.0, n=3, gap=fgap)
    x0 = 540 - fgap
    for i, st in enumerate(a["steps"]):
        sa = ease_out_cubic((t - 0.5 - i * 0.12) / 0.4)
        if sa <= 0:
            continue
        d.text((x0 + i * fgap, flow_y + 46), st, font=mono(22, True),
               fill=(*GRAY, int(255 * sa)), anchor="ma")

    # tiempo ahorrado — pop con spring
    sp = ease_out_cubic((t - 0.45) / 0.55)
    box_y = 1360
    d.rounded_rectangle([54, box_y, W - 54, box_y + 240], radius=30,
                        fill=(255, 255, 255, 10), outline=(*accent, 120), width=3)
    d.text((90, box_y + 46), "AHORRO / SEMANA", font=mono(30, True), fill=GRAY)
    scale = 0.7 + 0.3 * sp
    big = "+ " + a["save"]
    fsize = int(150 * scale)
    d.text((90, box_y + 86), big, font=grotesk(fsize, 700), fill=accent)
    d.text((W - 90, box_y + 150), "sin tocar nada", font=grotesk(38, 500),
           fill=(*GRAY, int(255 * sp)), anchor="ra")
    return img

def frame_cta(t):
    accent = NEON
    img = make_bg(accent, 540, 900).copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_header(d, TOTAL - 1, TOTAL, "EMPIEZA", accent)

    a = ease_out_cubic(t / 0.5)
    d.text((54, 470), "Total:", font=mono(40, True), fill=(*accent, int(255 * a)))
    d.text((54, 540), "10 h / semana", font=grotesk(120, 700), fill=WHITE)
    d.text((54, 700), "de vuelta a tu vida.", font=grotesk(60, 500), fill=GRAY)

    # CTA principal
    a2 = ease_out_cubic((t - 0.5) / 0.6)
    by = 940
    pulse = 1 + 0.02 * math.sin(t * 5)
    d.rounded_rectangle([54, by, W - 54, by + 200], radius=36, fill=(*accent, int(40 * a2)),
                        outline=(*accent, int(255 * a2)), width=4)
    d.text((540, by + 36), "Escribe “AUTO” por DM", font=grotesk(58, 700),
           fill=(*WHITE, int(255 * a2)), anchor="ma")
    d.text((540, by + 116), "y te montamos la 1.ª gratis", font=grotesk(44, 500),
           fill=(*accent, int(255 * a2)), anchor="ma")

    a3 = ease_out_cubic((t - 1.0) / 0.6)
    d.text((540, 1230), "Guarda este reel ↓", font=grotesk(46, 600),
           fill=(*GRAY, int(255 * a3)), anchor="ma")
    d.text((540, 1320), "@blastudios", font=grotesk(64, 700),
           fill=(*WHITE, int(255 * a3)), anchor="ma")
    d.text((540, 1410), "blastudios.vercel.app", font=mono(38, True),
           fill=(*accent, int(255 * a3)), anchor="ma")
    return img

# ── Timeline ──────────────────────────────────────────────────────────────────
# (inicio, duración, fn(t_local))
SCENES = []
SCENES.append((0.0, 3.0, lambda t: frame_hook(t)))
SCENES.append((3.0, 4.0, lambda t: frame_promesa(t)))
t0 = 7.0
DUR_AUTO = 9.0
for i in range(5):
    SCENES.append((t0 + i * DUR_AUTO, DUR_AUTO, (lambda i: (lambda t: frame_auto(i, t, DUR_AUTO)))(i)))
CTA_START = t0 + 5 * DUR_AUTO  # 52.0
SCENES.append((CTA_START, TOTAL - CTA_START, lambda t: frame_cta(t)))

XFADE = 0.45  # crossfade entre escenas

def render_at(global_t):
    # escena activa
    cur = None
    for s in SCENES:
        if s[0] <= global_t < s[0] + s[1]:
            cur = s
            break
    if cur is None:
        cur = SCENES[-1]
    start, dur, fn = cur
    local = global_t - start
    img = fn(local)
    # crossfade hacia la siguiente al final
    rem = (start + dur) - global_t
    if rem < XFADE:
        nxt = None
        for s in SCENES:
            if abs(s[0] - (start + dur)) < 1e-6:
                nxt = s
                break
        if nxt:
            nstart, ndur, nfn = nxt
            nimg = nfn(global_t - nstart)
            a = ease_in_out(1 - rem / XFADE)
            img = Image.blend(img, nimg, a)
    return img

# ── Audio ambiental (numpy, sin red) ─────────────────────────────────────────
def make_audio(path, dur, sr=44100):
    n = int(dur * sr)
    t = np.linspace(0, dur, n, endpoint=False)
    # pad cálido: dos sinusoides graves con leve detune + LFO de volumen
    pad = (np.sin(2 * np.pi * 110 * t) + np.sin(2 * np.pi * 110.4 * t) * 0.7
           + np.sin(2 * np.pi * 220 * t) * 0.25)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * t)
    pad *= lfo
    # pulso suave cada 2s (transiciones)
    beat = np.zeros(n)
    period = int(sr * 2.0)
    env_len = int(sr * 0.18)
    env = np.exp(-np.linspace(0, 6, env_len))
    for start in range(0, n - env_len, period):
        seg = (np.sin(2 * np.pi * 660 * t[start:start + env_len]) * env)
        beat[start:start + env_len] += seg
    sig = pad * 0.18 + beat * 0.12
    # fades de entrada/salida
    fade = int(sr * 0.6)
    sig[:fade] *= np.linspace(0, 1, fade)
    sig[-fade:] *= np.linspace(1, 0, fade)
    sig = np.clip(sig, -1, 1)
    pcm = (sig * 32767 * 0.7).astype(np.int16)
    stereo = np.stack([pcm, pcm], axis=1).flatten()
    with wave.open(path, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(stereo.tobytes())

# ── Encode ────────────────────────────────────────────────────────────────────
def main():
    total_frames = int(round(TOTAL * FPS))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Render {total_frames} frames ({TOTAL}s @ {FPS}fps)…")

    writer = imageio_ffmpeg.write_frames(
        TMP_V, (W, H), fps=FPS, codec="libx264", quality=6,
        macro_block_size=8, pix_fmt_in="rgb24", pix_fmt_out="yuv420p",
        ffmpeg_log_level="error",
    )
    writer.send(None)
    for i in range(total_frames):
        gt = i / FPS
        img = render_at(gt)
        writer.send(np.asarray(img, dtype=np.uint8))
        if i % 60 == 0:
            print(f"  {i}/{total_frames}  ({gt:4.1f}s)")
    writer.close()
    print("Video frames listos. Generando audio…")

    make_audio(TMP_A, TOTAL)
    print("Muxing audio + video…")
    subprocess.run([
        ffmpeg, "-y", "-i", TMP_V, "-i", TMP_A,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", OUT,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for f in (TMP_V, TMP_A):
        try: os.remove(f)
        except OSError: pass
    mb = os.path.getsize(OUT) / 1e6
    print(f"✓ {OUT}  ({mb:.1f} MB)")

if __name__ == "__main__":
    main()
