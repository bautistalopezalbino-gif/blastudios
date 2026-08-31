"""
Reel Blastudios — "5 automatizaciones que te ahorran 10 horas a la semana"
Paleta de blastudios.vercel.app: fondo #0A0A0F, azul #2563EB, texto #F5F5F7.
Tipografía: Space Grotesk (títulos) + Space Mono (datos).
Genera MP4 1080x1920 @30fps con voz TTS sincronizada por escena.

Uso:  python3 gen_reel_10_horas.py
Requiere: pillow numpy imageio imageio-ffmpeg edge-tts
Fuentes: SpaceGrotesk-{Medium,Bold}.ttf y SpaceMono-{Regular,Bold}.ttf
en la carpeta indicada por FONT_DIR (o junto al script).
"""

import asyncio, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio.v2 as imageio
import imageio_ffmpeg

# ── Rutas ────────────────────────────────────────────────────────────────────
HERE     = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("REEL_FONT_DIR", os.path.join(HERE, "fonts"))
WORK     = os.environ.get("REEL_WORK_DIR", HERE)
OUT      = os.path.join(HERE, "reel_10_horas_semana.mp4")
LOGO_PNG = os.path.join(HERE, "..", "Fotos", "blastudios-logo-Photoroom.png")
VOICE    = "es-ES-AlvaroNeural"
FFMPEG   = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1080, 1920, 30

# ── Paleta (blastudios.vercel.app) ───────────────────────────────────────────
BG     = ( 10,  10,  15)   # #0A0A0F
BLUE   = ( 37,  99, 235)   # #2563EB — azul primario de la web
LBLUE  = ( 96, 165, 250)   # #60A5FA
VIOLET = (139,  92, 246)   # #8B5CF6
WHITE  = (245, 245, 247)   # #F5F5F7 — texto de la web
GRAY   = (152, 152, 159)   # #98989F
DGRAY  = ( 28,  28,  34)
GREEN  = ( 52, 199,  89)

def _font(name, sz):
    p = os.path.join(FONT_DIR, name)
    return ImageFont.truetype(p, sz)

def SG_B(s): return _font("SpaceGrotesk-Bold.ttf",   s)   # títulos
def SG_M(s): return _font("SpaceGrotesk-Medium.ttf", s)   # texto
def SM_B(s): return _font("SpaceMono-Bold.ttf",      s)   # datos
def SM_R(s): return _font("SpaceMono-Regular.ttf",   s)   # etiquetas

# ── Guión por escena ─────────────────────────────────────────────────────────
# (id, narración TTS, título 2 líneas, flujo 3 nodos, chip herramientas,
#  stat, acento, nº)
SCENES = [
    dict(id="hook",
         tts="Estás regalando diez horas cada semana, a tareas que una máquina hace mejor.",
         title=["Estás regalando", "10h cada semana"],
         sub="a tareas que una máquina hace mejor",
         accent=BLUE, num=None, kind="hook"),
    dict(id="promesa",
         tts="Cinco automatizaciones reales. Cada una se monta en menos de una hora.",
         title=["5 automatizaciones", "reales"],
         sub="setup < 1h cada una · sin código",
         accent=LBLUE, num=None, kind="promesa"),
    dict(id="a1",
         tts="Uno: onboarding de clientes. El formulario crea carpeta, contrato y factura. Solo, sin abrir nada.",
         title=["Onboarding", "de clientes"],
         flow=["FORM", "MAKE", "NOTION"], chip="MAKE + NOTION",
         stat="-2h", accent=BLUE, num=1, kind="auto"),
    dict(id="a2",
         tts="Dos: propuestas automáticas. Del brief al PDF con Notion AI. Tú solo revisas y envías.",
         title=["Propuestas", "automáticas"],
         flow=["BRIEF", "NOTION AI", "PDF"], chip="NOTION AI",
         stat="-1,5h", accent=VIOLET, num=2, kind="auto"),
    dict(id="a3",
         tts="Tres: recicla tu contenido. Un vídeo se convierte en siete posts programados. Sin tocar nada.",
         title=["Reciclaje", "de contenido"],
         flow=["1 VÍDEO", "ZAPIER", "7 POSTS"], chip="ZAPIER + METRICOOL",
         stat="-3h", accent=LBLUE, num=3, kind="auto"),
    dict(id="a4",
         tts="Cuatro: seguimiento de leads. Si no responden, la secuencia insiste por ti. Cero leads olvidados.",
         title=["Seguimiento", "de leads"],
         flow=["LEAD", "ZAPIER", "GMAIL"], chip="ZAPIER + GMAIL",
         stat="-2h", accent=BLUE, num=4, kind="auto"),
    dict(id="a5",
         tts="Cinco: informes para clientes. Las métricas llegan solas cada lunes. Tu cliente feliz. Tú, libre.",
         title=["Informes", "para clientes"],
         flow=["MÉTRICAS", "MAKE", "SHEETS"], chip="MAKE + SHEETS",
         stat="-1,5h", accent=VIOLET, num=5, kind="auto"),
    dict(id="recap",
         tts="Suma: diez horas cada semana. Un día entero de trabajo, devuelto.",
         title=["= 10h", "/semana"],
         sub="un día entero de trabajo. devuelto.",
         accent=BLUE, num=None, kind="recap"),
    dict(id="cta",
         tts="Comenta AUTO y te mando la plantilla con las cinco configuradas. Sígueme para más automatización real.",
         title=["Comenta", "“AUTO”"],
         sub="y te mando la plantilla de las 5",
         accent=BLUE, num=None, kind="cta"),
]

# ── Audio: TTS por escena y ensamblado ───────────────────────────────────────
SR = 44100

async def synth_all():
    import edge_tts
    for s in SCENES:
        mp3 = os.path.join(WORK, f"_tts_{s['id']}.mp3")
        if not os.path.exists(mp3):
            await edge_tts.Communicate(s["tts"], VOICE, rate="+4%").save(mp3)
        wav = os.path.join(WORK, f"_tts_{s['id']}.wav")
        if not os.path.exists(wav):
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", mp3,
                            "-ar", str(SR), "-ac", "1", wav], check=True)
        with wave.open(wav) as w:
            s["audio_dur"] = w.getnframes() / w.getframerate()
            s["audio"] = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)

def build_timeline():
    t = 0.0
    for s in SCENES:
        pad = 0.55 if s["kind"] in ("auto", "hook") else 0.45
        dur = max(s["audio_dur"] + pad, 3.0)
        if s["kind"] == "cta":
            dur = s["audio_dur"] + 1.6
        s["t0"], s["dur"] = t, dur
        t += dur
    return t

def write_audio(total):
    track = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for s in SCENES:
        i0 = int((s["t0"] + 0.18) * SR)
        a = s["audio"].astype(np.float32)
        track[i0:i0 + len(a)] += a
    track = np.clip(track, -32767, 32767).astype(np.int16)
    track = track[:int(total * SR)]
    path = os.path.join(WORK, "_voice.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(track.tobytes())
    return path

# ── Utilidades de dibujo ─────────────────────────────────────────────────────
def ease_out(t):  return 1 - (1 - min(max(t, 0), 1)) ** 3

def spring(t):
    t = min(max(t, 0), 1)
    return 1 + (2 ** (-8 * t)) * math.sin((t - 0.08) * 14) * 0.35 * (1 - t)

def center_text(d, y, txt, font, fill, ls=0):
    wdt = d.textlength(txt, font=font)
    d.text(((W - wdt) / 2, y), txt, font=font, fill=fill)

def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def make_glow(color, radius=420, alpha=90):
    g = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    dg.ellipse([radius * 0.35, radius * 0.35, radius * 1.65, radius * 1.65],
               fill=color + (alpha,))
    return g.filter(ImageFilter.GaussianBlur(radius * 0.35))

LOGO = None
def load_logo(h_px=64):
    global LOGO
    img = Image.open(LOGO_PNG).convert("RGBA")
    ar = img.width / img.height
    LOGO = img.resize((int(h_px * ar), h_px), Image.LANCZOS)

def wrap(d, txt, font, maxw):
    words, lines, cur = txt.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

# Glows precalculados por acento
_GLOWS = {}
def glow_for(color):
    if color not in _GLOWS: _GLOWS[color] = make_glow(color)
    return _GLOWS[color]

# ── Capas comunes ────────────────────────────────────────────────────────────
def draw_bg(frame, scene, t):
    g = glow_for(scene["accent"])
    # blob que respira lentamente
    bx = int(W * 0.72 + 40 * math.sin(t * 0.7))
    by = int(H * 0.22 + 30 * math.cos(t * 0.5))
    frame.alpha_composite(g, (bx - g.width // 2, by - g.height // 2))
    g2 = glow_for(VIOLET if scene["accent"] != VIOLET else BLUE)
    frame.alpha_composite(g2.resize((g2.width // 2, g2.height // 2)),
                          (int(W * 0.05), int(H * 0.72)))

def draw_header(frame, d, scene, prog):
    if LOGO is not None:
        lg = LOGO.copy()
        frame.alpha_composite(lg, (60, 70))
    if scene["kind"] == "auto":
        f = SM_R(34)
        txt = f"{scene['num']}/5"
        d.text((W - 60 - d.textlength(txt, font=f), 86), txt, font=f, fill=GRAY)
    # pips de progreso (5 automatizaciones)
    pw, gap, y = 88, 22, 190
    x0 = (W - 5 * pw - 4 * gap) / 2
    done = 0 if scene["num"] is None else scene["num"]
    if scene["kind"] in ("recap", "cta"): done = 5
    for i in range(5):
        x = x0 + i * (pw + gap)
        fill = scene["accent"] if i < done else DGRAY
        if scene["kind"] == "auto" and i == done - 1:
            w_ = int(pw * min(prog * 1.5, 1))
            rrect(d, [x, y, x + pw, y + 8], 4, fill=DGRAY)
            if w_ > 8: rrect(d, [x, y, x + w_, y + 8], 4, fill=fill)
        else:
            rrect(d, [x, y, x + pw, y + 8], 4, fill=fill)

def draw_subtitle(d, scene, k):
    f = SG_M(44)
    lines = wrap(d, scene["tts"].rstrip("."), f, W - 200)[:3]
    y = 1560
    a = ease_out(k * 2.2)
    col = tuple(int(c * a + BG[i] * (1 - a)) for i, c in enumerate((210, 212, 220)))
    for ln in lines:
        center_text(d, y, ln, f, col); y += 62

def draw_url(d):
    center_text(d, 1806, "blastudios.vercel.app", SM_R(34), (110, 114, 128))

# ── Escenas ──────────────────────────────────────────────────────────────────
def scene_hook(frame, d, s, t, k):
    a = ease_out(k * 3)
    # contador gigante 0h → 10h
    n = int(round(10 * ease_out(min(t / 1.4, 1))))
    f_big = SM_B(300)
    txt = f"{n}h"
    y = 520 + (1 - a) * 60
    center_text(d, y, txt, f_big, s["accent"] if n >= 10 else WHITE)
    center_text(d, 900, "PERDIDAS / SEMANA", SM_R(46), GRAY)
    f_t = SG_B(88)
    y2 = 1080
    for i, ln in enumerate(s["title"]):
        aa = ease_out((t - 0.25 - i * 0.12) * 2.5)
        col = tuple(int(c * aa + BG[j] * (1 - aa)) for j, c in enumerate(WHITE))
        center_text(d, y2 + i * 104, ln, f_t, col)

def scene_promesa(frame, d, s, t, k):
    f_t = SG_B(104)
    y = 640
    for i, ln in enumerate(s["title"]):
        aa = ease_out((t - i * 0.14) * 2.6)
        yy = y + i * 122 + (1 - aa) * 50
        col = tuple(int(c * aa) for c in (WHITE if i == 0 else s["accent"]))
        center_text(d, yy, ln, f_t, col)
    aa = ease_out((t - 0.5) * 2.5)
    if aa > 0:
        f_c = SM_R(40)
        tw = d.textlength(s["sub"], font=f_c)
        x0, y0 = (W - tw) / 2 - 36, 1000
        rrect(d, [x0, y0, x0 + tw + 72, y0 + 92], 46,
              outline=tuple(int(c * aa) for c in s["accent"]), width=3)
        d.text((x0 + 36, y0 + 24), s["sub"], font=f_c,
               fill=tuple(int(c * aa) for c in (200, 204, 214)))

def scene_auto(frame, d, s, t, k):
    ac = s["accent"]
    # número watermark
    f_wm = SG_B(560)
    wm = f"0{s['num']}"
    a_wm = ease_out(t * 2) * 0.10
    tmp = Image.new("RGBA", (W, 700), (0, 0, 0, 0))
    dt = ImageDraw.Draw(tmp)
    dt.text((W - dt.textlength(wm, font=f_wm) - 30, -80), wm, font=f_wm,
            fill=ac + (int(255 * a_wm),))
    frame.alpha_composite(tmp, (0, 240))
    # card glass con flujo de 3 nodos
    a_c = ease_out((t - 0.1) * 2.4)
    cy0, cy1 = 330, 760
    yoff = int((1 - a_c) * 60)
    card = Image.new("RGBA", (W - 120, cy1 - cy0), (0, 0, 0, 0))
    dc = ImageDraw.Draw(card)
    rrect(dc, [0, 0, card.width - 1, card.height - 1], 44,
          fill=(20, 21, 28, int(215 * a_c)),
          outline=(255, 255, 255, int(28 * a_c)), width=2)
    dc.text((44, 36), "WORKFLOW", font=SM_R(30),
            fill=ac + (int(255 * a_c),))
    # nodos
    nw, nh, gap = 268, 118, 42
    x = (card.width - 3 * nw - 2 * gap) / 2
    ny = 190
    f_n = SM_B(34)
    for i, label in enumerate(s["flow"]):
        tt = t - 0.35 - i * 0.28
        aa = ease_out(tt * 2.6)
        if aa <= 0: continue
        xx = x + i * (nw + gap)
        is_mid = (i == 1)
        fill = ac + (int(255 * aa),) if is_mid else (32, 34, 44, int(255 * aa))
        rrect(dc, [xx, ny, xx + nw, ny + nh], 26, fill=fill,
              outline=(255, 255, 255, int(30 * aa)), width=2)
        fl = f_n if len(label) <= 9 else SM_B(27)
        tw = dc.textlength(label, font=fl)
        col = (255, 255, 255, int(255 * aa)) if is_mid else \
              tuple(list(WHITE) + [int(255 * aa)])
        dc.text((xx + (nw - tw) / 2, ny + (nh - fl.size) / 2 - 4),
                label, font=fl, fill=col)
        if i < 2:  # flecha
            ax = xx + nw + gap / 2
            aa2 = ease_out((tt - 0.14) * 3)
            if aa2 > 0:
                dc.text((ax - 12, ny + nh / 2 - 20), "→", font=SG_B(40),
                        fill=(255, 255, 255, int(160 * aa2)))
    # stat dentro de la card
    aa = ease_out((t - 1.15) * 2.4)
    if aa > 0:
        f_s = SM_B(96)
        stat = s["stat"]
        sw = dc.textlength(stat, font=f_s)
        sy = 300
        dc.text(((card.width - sw) / 2 - 80, sy), stat, font=f_s,
                fill=ac + (int(255 * aa),))
        dc.text(((card.width - sw) / 2 - 80 + sw + 24, sy + 46),
                "/semana", font=SM_R(40),
                fill=(160, 164, 176, int(255 * aa)))
    frame.alpha_composite(card, (60, cy0 + yoff))
    # título
    f_t = SG_B(100)
    y = 850
    for i, ln in enumerate(s["title"]):
        aa = ease_out((t - 0.2 - i * 0.1) * 2.6)
        col = tuple(int(c * aa) for c in WHITE)
        d.text((80, y + i * 112 + (1 - aa) * 40), ln, font=f_t, fill=col)
    # chip herramientas
    aa = ease_out((t - 0.55) * 2.5)
    if aa > 0:
        f_c = SM_B(36)
        tw = d.textlength(s["chip"], font=f_c)
        x0, y0 = 80, 1120
        rrect(d, [x0, y0, x0 + tw + 64, y0 + 84], 42,
              fill=tuple(int(c * 0.16 * aa) for c in ac),
              outline=tuple(int(c * aa) for c in ac), width=3)
        d.text((x0 + 32, y0 + 20), s["chip"], font=f_c,
               fill=tuple(int(c * aa) for c in tuple(min(255, c + 60) for c in ac)))

def scene_recap(frame, d, s, t, k):
    rows = [("01 Onboarding", "-2h"), ("02 Propuestas", "-1,5h"),
            ("03 Contenido", "-3h"), ("04 Leads", "-2h"), ("05 Informes", "-1,5h")]
    f_r, f_v = SM_R(40), SM_B(44)
    y = 430
    for i, (name, val) in enumerate(rows):
        aa = ease_out((t - i * 0.14) * 3)
        if aa <= 0: continue
        col = tuple(int(c * aa) for c in (190, 194, 206))
        d.text((150, y + i * 88), name, font=f_r, fill=col)
        vw = d.textlength(val, font=f_v)
        d.text((W - 150 - vw, y + i * 88 - 4), val, font=f_v,
               fill=tuple(int(c * aa) for c in LBLUE))
    aa = ease_out((t - 0.95) * 2.2)
    if aa > 0:
        d.line([(150, 900), (150 + (W - 300) * aa, 900)], fill=GRAY, width=3)
        f_big = SM_B(190)
        sc_ = spring((t - 1.1) / 0.7)
        txt = "=10h"
        center_text(d, 960 + (1 - min(sc_, 1)) * 30, txt, f_big,
                    tuple(int(c * aa) for c in s["accent"]))
        center_text(d, 1210, "/SEMANA RECUPERADAS", SM_R(44),
                    tuple(int(c * aa) for c in GRAY))
        aa2 = ease_out((t - 1.6) * 2.4)
        if aa2 > 0:
            f_t = SG_B(64)
            center_text(d, 1330, "un día entero. devuelto.", f_t,
                        tuple(int(c * aa2) for c in WHITE))

def scene_cta(frame, d, s, t, k):
    # logo grande con spring
    if LOGO is not None:
        sc_ = spring(t / 0.8)
        lw = int(LOGO.width * 2.0 * min(sc_, 1.25))
        lh = int(LOGO.height * 2.0 * min(sc_, 1.25))
        if lw > 0:
            lg = LOGO.resize((lw, lh), Image.LANCZOS)
            frame.alpha_composite(lg, ((W - lw) // 2, 430 - lh // 2 + 60))
    f_t = SG_B(110)
    y = 640
    for i, ln in enumerate(s["title"]):
        aa = ease_out((t - 0.3 - i * 0.12) * 2.4)
        col = WHITE if i == 0 else s["accent"]
        center_text(d, y + i * 128 + (1 - aa) * 40, ln, f_t,
                    tuple(int(c * aa) for c in col))
    aa = ease_out((t - 0.7) * 2.2)
    if aa > 0:
        center_text(d, 940, s["sub"], SG_M(48),
                    tuple(int(c * aa) for c in (200, 204, 214)))
    # botón simulado
    aa = ease_out((t - 1.1) * 2.2)
    if aa > 0:
        f_b = SM_B(44)
        txt = "COMENTA: AUTO"
        tw = d.textlength(txt, font=f_b)
        x0, y0 = (W - tw) / 2 - 56, 1090
        pulse = 1 + 0.02 * math.sin(t * 5)
        rrect(d, [x0, y0, x0 + tw + 112, y0 + 110], 55,
              fill=tuple(int(c * aa * pulse) for c in s["accent"]))
        d.text((x0 + 56, y0 + 28), txt, font=f_b,
               fill=(255, 255, 255, int(255 * aa)))
    aa = ease_out((t - 1.5) * 2.2)
    if aa > 0:
        center_text(d, 1290, "sígueme para más automatización real",
                    SG_M(42), tuple(int(c * aa) for c in GRAY))

RENDER = {"hook": scene_hook, "promesa": scene_promesa, "auto": scene_auto,
          "recap": scene_recap, "cta": scene_cta}

# ── Render principal ─────────────────────────────────────────────────────────
def render(total):
    tmp_v = os.path.join(WORK, "_video.mp4")
    wr = imageio.get_writer(tmp_v, fps=FPS, codec="libx264",
                            quality=8, pixelformat="yuv420p",
                            macro_block_size=1)
    n_frames = int(total * FPS)
    scene_i = 0
    for f_i in range(n_frames):
        t_glob = f_i / FPS
        while scene_i < len(SCENES) - 1 and \
              t_glob >= SCENES[scene_i]["t0"] + SCENES[scene_i]["dur"]:
            scene_i += 1
        s = SCENES[scene_i]
        t = t_glob - s["t0"]
        k = t / s["dur"]
        frame = Image.new("RGBA", (W, H), BG + (255,))
        d = ImageDraw.Draw(frame)
        draw_bg(frame, s, t_glob)
        d = ImageDraw.Draw(frame)
        draw_header(frame, d, s, k)
        d = ImageDraw.Draw(frame)
        RENDER[s["kind"]](frame, d, s, t, k)
        d = ImageDraw.Draw(frame)
        if s["kind"] == "auto":
            draw_subtitle(d, s, k)
        draw_url(d)
        # crossfade de entrada/salida de escena
        fade = min(1, t * 4, (s["dur"] - t) * 4)
        if s is SCENES[-1]:
            fade = min(1, t * 4)  # el CTA termina en fade global abajo
        if f_i > n_frames - int(0.8 * FPS):
            fade = min(fade, (n_frames - f_i) / (0.8 * FPS))
        arr = np.asarray(frame.convert("RGB"), dtype=np.float32)
        if fade < 1:
            bgarr = np.array(BG, dtype=np.float32)
            arr = arr * fade + bgarr * (1 - fade)
        wr.append_data(arr.astype(np.uint8))
        if f_i % (FPS * 5) == 0:
            print(f"  frame {f_i}/{n_frames} ({t_glob:.1f}s) escena={s['id']}")
    wr.close()
    return tmp_v

def main():
    print("1/4 · Sintetizando voz…")
    asyncio.run(synth_all())
    total = build_timeline()
    print(f"    duración total: {total:.1f}s")
    for s in SCENES:
        print(f"    {s['id']:8s} {s['t0']:5.1f}s → {s['t0']+s['dur']:5.1f}s")
    print("2/4 · Mezclando audio…")
    voice = write_audio(total)
    print("3/4 · Renderizando frames…")
    load_logo(64)
    tmp_v = render(total)
    print("4/4 · Muxeando MP4 final…")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-i", tmp_v, "-i", voice,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", OUT], check=True)
    print(f"OK → {OUT}  ({os.path.getsize(OUT)/1e6:.1f} MB, {total:.1f}s)")

if __name__ == "__main__":
    main()
