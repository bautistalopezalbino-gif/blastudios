"""
Reel Blastudios v2 – 5 cosas que tu competencia automatiza y tú no
- Logo PNG real en barra de header
- Subtítulos karaoke (palabra a palabra)
- Fondos animados dinámicos con cambio de plano cada ~4s
"""

import asyncio, os, math, random, subprocess, time
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np

# ── Config ──────────────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
SCALE  = W / 390

def sc(v): return int(round(v * SCALE))

FD       = r"C:\Windows\Fonts"
VOICE    = "es-ES-AlvaroNeural"
DIR      = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram"
OUT      = os.path.join(DIR, "reel_blastudios_automatizacion.mp4")
TMP_V    = os.path.join(DIR, "_tmp_video.mp4")
TMP_A    = os.path.join(DIR, "_tmp_audio.mp3")
LOGO_PNG = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Fotos\blastudios-logo-Photoroom.png"

# ── Colors ───────────────────────────────────────────────────────────────────
BG    = (  9,  10,  18)
BLUE  = ( 37,  99, 235)
LBLU  = ( 96, 165, 250)
DBLU  = (  8,  18,  52)
WHITE = (248, 250, 252)
GRAY  = (110, 115, 135)
DGRAY = ( 25,  27,  40)
GREEN = ( 34, 197,  94)
AMBER = (245, 158,  11)
RED   = (220,  50,  47)
TEAL  = ( 20, 184, 166)

# ── Fonts ─────────────────────────────────────────────────────────────────────
def _fnt(name, sz):
    try:    return ImageFont.truetype(os.path.join(FD, name), sz)
    except: return ImageFont.load_default()

def FB(s): return _fnt('segoeuib.ttf', s)
def FR(s): return _fnt('segoeui.ttf',  s)
def FL(s): return _fnt('segoeuil.ttf', s)

F_H1    = FB(sc(24))
F_H2    = FB(sc(19))
F_BD    = FR(sc(13))
F_SUB_N = FR(sc(14))    # subtitle normal word
F_SUB_H = FB(sc(15))    # subtitle highlighted word (current)
F_SUB_P = FL(sc(13))    # subtitle past word
F_NUM   = FB(sc(58))    # big number
F_TAG   = FB(sc( 9))
F_FRAC  = FR(sc(10))

# ── Logo preparation ──────────────────────────────────────────────────────────
def load_logo_for_header(path, target_h):
    """Scale logo PNG (already transparent) to fit header height."""
    img = Image.open(path).convert("RGBA")
    ar  = img.width / img.height
    tw  = int(target_h * ar)
    return img.resize((tw, target_h), Image.LANCZOS)

HEADER_H  = sc(54)
LOGO_IMG  = load_logo_for_header(LOGO_PNG, int(HEADER_H * 0.72))

# ── Script ────────────────────────────────────────────────────────────────────
SCRIPT = (
    "¿Sabes qué hace tu competencia mientras tú duermes? "
    "Hay cinco cosas que ya automatiza, y tú no. "
    "Número uno: atención al cliente. "
    "Tienen un chatbot que responde, califica y cierra ventas a cualquier hora. Sin ti. "
    "Número dos: secuencias de email. "
    "Cada lead entra en un flujo que lo convierte, solo, en cliente. "
    "Número tres: publicación en redes sociales. "
    "Su contenido se programa, se publica y genera interacción todos los días. Sin nadie. "
    "Número cuatro: facturación automática. "
    "Sus facturas se crean, se envían y se cobran solas. Sin errores, sin retrasos. "
    "Número cinco: análisis en tiempo real. "
    "Saben exactamente qué funciona y qué no. Tú, todavía estás adivinando. "
    "En Blastudios lo automatizamos todo por ti. "
    "Tu competencia ya empezó. ¿Y tú?"
)

SCENE_DEFS = [
    # (id, label, title, bg_type, accent)
    ("intro", "",    "¿Sabes qué\nhace tu\ncompetencia?",  "intro",   BLUE),
    ("s1",    "1/5", "Atención\nal cliente",               "chat",    LBLU),
    ("s2",    "2/5", "Secuencias\nde email",               "email",   LBLU),
    ("s3",    "3/5", "Redes\nsociales",                    "social",  LBLU),
    ("s4",    "4/5", "Facturación\nautomática",            "invoice", GREEN),
    ("s5",    "5/5", "Análisis en\ntiempo real",           "chart",   AMBER),
    ("cta",   "",    "Blastudios\nlo hace\npor ti.",        "cta",     BLUE),
]

# ── Easing ────────────────────────────────────────────────────────────────────
def eo(t):  return 1 - (1 - min(1, max(0, t))) ** 3
def fade(start, dur, lt):
    if lt < start:       return 0.0
    if lt > start + dur: return 1.0
    return eo((lt - start) / dur)
def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))

# ── Drawing utils ─────────────────────────────────────────────────────────────
def alpha_composite_onto(base_rgb, layer_rgba):
    """Composite RGBA layer onto RGB image in-place."""
    merged = Image.alpha_composite(base_rgb.convert('RGBA'), layer_rgba)
    base_rgb.paste(merged.convert('RGB'))

def rr(d, xy, r, fill=None, outline=None, ow=2):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=ow)

def text_center(d, cx, y, txt, font, fill):
    bb = d.textbbox((0, 0), txt, font=font)
    d.text((cx - (bb[2]-bb[0])//2, y), txt, font=font, fill=fill)
    return bb[3] - bb[1]

def glow_layer(size, cx, cy, radius, color, alpha_peak=40):
    layer = Image.new('RGBA', size, (0,0,0,0))
    d = ImageDraw.Draw(layer)
    for i in range(5, 0, -1):
        a = int(alpha_peak * (i/5)**2)
        r = radius + sc(12)*(5-i+1)
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*color[:3], a))
    return layer

# ── Shared RNG for deterministic particle positions ───────────────────────────
rng = random.Random(42)
STARS = [(rng.randint(0, W), rng.randint(0, H), rng.random()) for _ in range(80)]

def draw_starfield(layer, t_global, alpha=180):
    d = ImageDraw.Draw(layer)
    for sx, sy, bright in STARS:
        p  = (math.sin(t_global * 0.7 + bright * 6.28) + 1) / 2
        a  = int(alpha * (0.08 + 0.22 * bright * p))
        r  = 1 if bright < 0.6 else 2
        d.ellipse([sx-r, sy-r, sx+r, sy+r], fill=(*WHITE, a))

# ── Shot system ───────────────────────────────────────────────────────────────
SHOT_DUR  = 4.0   # seconds per shot
SHOT_FADE = 0.45  # crossfade duration

def shot_info(lt):
    """Returns (shot_idx, t_shot, alpha) where alpha is the visibility of this shot."""
    shot   = int(lt / SHOT_DUR)
    t_shot = lt % SHOT_DUR
    fade_i = min(t_shot / SHOT_FADE, 1.0)
    fade_o = max(0.0, 1.0 - (t_shot - (SHOT_DUR - SHOT_FADE)) / SHOT_FADE)
    alpha  = min(fade_i, fade_o)
    return shot, t_shot, alpha

# ── BACKGROUND RENDERERS ──────────────────────────────────────────────────────
# Each draws onto `layer` (RGBA) using local time `lt` and global time `tg`.
# Shot system: draw shot 0 and shot 1 separately and blend.

def _bg_panel(d, x0, y0, x1, y1, radius, fill_a, fill_color=DGRAY):
    """Translucent rounded panel."""
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                        fill=(*fill_color, fill_a))

def bg_intro(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    cx, cy = W//2, H//2
    draw_starfield(layer, tg, 200)
    # Expanding concentric rings
    for ring in range(6):
        phase = (lt * 0.35 + ring * 0.7) % 4.5
        a = int(25 * max(0, 1 - phase / 4.5))
        r = int(sc(50) + phase * sc(180))
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(*LBLU, a), width=sc(2))
    # Floating "?" glyphs
    for i, (gx, gy, gs) in enumerate([(W//3, H//3, sc(40)),
                                        (2*W//3, H//4, sc(28)),
                                        (W//4, 2*H//3, sc(22)),
                                        (3*W//4, 3*H//5, sc(32))]):
        pulse = (math.sin(tg * 1.1 + i * 1.4) + 1) / 2
        a = int((12 + 18 * pulse))
        bb = d.textbbox((0,0), "?", font=FB(gs))
        drift_x = int(sc(8) * math.sin(tg * 0.4 + i))
        drift_y = int(sc(12) * math.cos(tg * 0.3 + i * 0.9))
        d.text((gx - (bb[2]-bb[0])//2 + drift_x,
                gy - (bb[3]-bb[1])//2 + drift_y),
               "?", font=FB(gs), fill=(*LBLU, a))
    # Floating digits 1-5
    for i in range(5):
        angle = tg * 0.18 + i * (2 * math.pi / 5)
        r_orb = sc(260) + sc(30) * math.sin(tg * 0.5 + i * 1.3)
        dx = cx + int(r_orb * math.cos(angle))
        dy = cy + int(r_orb * math.sin(angle) * 0.6)
        p = (math.sin(tg * 1.5 + i * 0.9) + 1) / 2
        a = int(10 + 22 * p)
        bb = d.textbbox((0,0), str(i+1), font=FB(sc(36)))
        d.text((dx - (bb[2]-bb[0])//2, dy - (bb[3]-bb[1])//2),
               str(i+1), font=FB(sc(36)), fill=(*BLUE, a))

def _chat_bubble(d, x, y, w, h, from_right, a, text="", font=None):
    col = BLUE if from_right else DGRAY
    out = LBLU if from_right else GRAY
    d.rounded_rectangle([x, y, x+w, y+h], radius=sc(8),
                        fill=(*col, a), outline=(*out, a//2), width=1)
    if text and font:
        tw_bb = d.textbbox((0,0), text, font=font)
        d.text((x+(w-(tw_bb[2]-tw_bb[0]))//2, y+(h-(tw_bb[3]-tw_bb[1]))//2),
               text, font=font, fill=(*WHITE, a))

def bg_chat(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    draw_starfield(layer, tg, 100)
    shot, ts, _ = shot_info(lt)

    if shot % 2 == 0:
        # SHOT A: Multiple chat windows (wide view)
        pan_x = int(sc(15) * math.sin(ts * 0.4))
        for col_i in range(2):
            bx = (sc(50) + col_i * sc(200)) + pan_x
            # Phone frame
            pw, ph = sc(145), sc(270)
            py = H//2 - ph//2 + int(sc(20) * math.sin(tg * 0.3 + col_i))
            _bg_panel(d, bx, py, bx+pw, py+ph, sc(12), 35)
            d.rounded_rectangle([bx, py, bx+pw, py+ph], radius=sc(12),
                                 outline=(*LBLU, 30), width=1)
            # Messages in phone
            msg_y = py + sc(14)
            msgs = [("...", False), ("Hola!", True), ("Precio?", False),
                    ("Automatizado 24h", True)]
            for mi, (mt, right) in enumerate(msgs):
                prog = clamp((lt - mi * 0.5) / 0.4)
                if prog <= 0: continue
                a = int(prog * 35)
                mw = sc(90); mh = sc(18)
                mx = bx + (pw - mw - sc(6)) if right else bx + sc(6)
                _chat_bubble(d, mx, msg_y, mw, mh, right, a, mt, F_TAG)
                msg_y += mh + sc(5)
        # Right side: big "24h" indicator
        rx = W - sc(130) + pan_x; ry = H//2 - sc(50)
        _bg_panel(d, rx, ry, rx+sc(100), ry+sc(70), sc(10), 28, DBLU)
        bb = d.textbbox((0,0), "24/7", font=FB(sc(18)))
        d.text((rx+(sc(100)-(bb[2]-bb[0]))//2, ry+sc(12)),
               "24/7", font=FB(sc(18)), fill=(*LBLU, 28))
        bb2 = d.textbbox((0,0), "online", font=F_TAG)
        d.text((rx+(sc(100)-(bb2[2]-bb2[0]))//2, ry+sc(36)),
               "online", font=F_TAG, fill=(*GREEN, 25))
    else:
        # SHOT B: Close-up single chat, zoomed in
        zoom = 1.0 + 0.06 * ts / SHOT_DUR
        pw = int(sc(200) * zoom); ph = int(sc(380) * zoom)
        bx = W//2 - pw//2 + int(sc(20)*math.sin(ts*0.25))
        py = H//2 - ph//2
        _bg_panel(d, bx, py, bx+pw, py+ph, sc(14), 30)
        d.rounded_rectangle([bx, py, bx+pw, py+ph], radius=sc(14),
                             outline=(*LBLU, 25), width=1)
        msg_defs = [
            ("Cliente necesita info", False, 0.0),
            ("Bot responde al instante", True, 0.4),
            ("¿Precio del servicio?", False, 0.9),
            ("Aquí tienes el catálogo", True, 1.4),
            ("Gracias, me interesa!", False, 1.9),
            ("Reserva confirmada ✓", True, 2.4),
        ]
        my = py + sc(20)
        mh = sc(24)
        for mt, right, delay in msg_defs:
            prog = clamp((lt - delay - shot * SHOT_DUR) / 0.35)
            if prog <= 0: continue
            a = int(prog * 32)
            mw = int(len(mt) * sc(5.5))
            mw = min(mw, pw - sc(20))
            mx = bx + pw - mw - sc(8) if right else bx + sc(8)
            _chat_bubble(d, mx, my, mw, mh, right, a, mt, F_TAG)
            my += mh + sc(8)

def bg_email(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    draw_starfield(layer, tg, 100)
    shot, ts, _ = shot_info(lt)
    cx = W // 2

    if shot % 2 == 0:
        # SHOT A: Funnel diagram (Lead → Email Seq → Cliente)
        pan_y = int(sc(10) * math.sin(ts * 0.35))
        stages = [("LEAD", BLUE), ("EMAIL 1", LBLU), ("EMAIL 3", LBLU), ("CLIENTE", GREEN)]
        box_w, box_h = sc(130), sc(32)
        sy0 = H//2 - sc(120) + pan_y
        for i, (label, col) in enumerate(stages):
            sy = sy0 + i * sc(72)
            prog = clamp((lt - i * 0.3) / 0.4)
            a = int(prog * 28)
            if a <= 0: continue
            bx = cx - box_w//2
            rr(d, [bx, sy, bx+box_w, sy+box_h], sc(6), fill=(*col, a))
            bb = d.textbbox((0,0), label, font=F_TAG)
            d.text((bx+(box_w-(bb[2]-bb[0]))//2, sy+(box_h-(bb[3]-bb[1]))//2),
                   label, font=F_TAG, fill=(*WHITE, min(a*2, 80)))
            # Arrow down
            if i < len(stages)-1:
                ax = cx; ay1 = sy + box_h + sc(2); ay2 = sy + sc(68)
                a2 = int(prog * 20)
                d.line([(ax, ay1), (ax, ay2-sc(6))], fill=(*LBLU, a2), width=sc(2))
                d.polygon([(ax, ay2), (ax-sc(6), ay2-sc(10)), (ax+sc(6), ay2-sc(10))],
                           fill=(*LBLU, a2))
        # Flying envelopes
        for env_i in range(4):
            env_phase = (tg * 0.5 + env_i * 0.9) % 3.0
            env_x = int(W * (env_phase / 3.0)) - sc(40)
            env_y = H//2 + sc(120) + int(sc(30) * math.sin(env_phase * 3.14))
            env_a = int(18 * math.sin(env_phase / 3.0 * 3.14))
            if env_a > 0:
                ew, eh = sc(32), sc(22)
                d.rectangle([env_x, env_y, env_x+ew, env_y+eh],
                             fill=(*BLUE, env_a))
                d.line([(env_x, env_y), (env_x+ew//2, env_y+eh//2), (env_x+ew, env_y)],
                       fill=(*LBLU, env_a), width=1)
    else:
        # SHOT B: Stats rising (email metrics)
        pan_x = int(sc(12) * math.cos(ts * 0.3))
        metrics = [("Apertura", 68), ("Clicks", 34), ("Conversión", 18)]
        mx0 = W//4 + pan_x
        for i, (name, val) in enumerate(metrics):
            mx = mx0 + i * sc(130)
            my = H//2 - sc(60)
            p = clamp((lt - i * 0.5 - shot * SHOT_DUR) / 0.6)
            a = int(p * 28)
            if a <= 0: continue
            bh = int(sc(100) * p)
            bw = sc(70)
            bx = mx - bw//2
            rr(d, [bx, my+sc(100)-bh, bx+bw, my+sc(100)], sc(4),
               fill=(*BLUE, a))
            pct = f"{int(val * p)}%"
            bb = d.textbbox((0,0), pct, font=F_TAG)
            d.text((mx-(bb[2]-bb[0])//2, my+sc(100)-bh-sc(14)),
                   pct, font=F_TAG, fill=(*LBLU, min(a*2, 70)))
            bb2 = d.textbbox((0,0), name, font=F_TAG)
            d.text((mx-(bb2[2]-bb2[0])//2, my+sc(108)),
                   name, font=F_TAG, fill=(*GRAY, a//2))

def bg_social(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    draw_starfield(layer, tg, 100)
    shot, ts, _ = shot_info(lt)

    if shot % 2 == 0:
        # SHOT A: Post grid (wide)
        pan = int(sc(8) * math.sin(ts * 0.4))
        cell = sc(78); gap = sc(10)
        cols = 3; rows = 4
        gx0 = W//2 - (cols * cell + (cols-1) * gap)//2 + pan
        gy0 = H//2 - (rows * cell + (rows-1) * gap)//2
        for r in range(rows):
            for c in range(cols):
                delay = (r * cols + c) * 0.18
                prog  = clamp((lt - delay) / 0.35)
                if prog <= 0: continue
                a = int(prog * 22)
                gx = gx0 + c * (cell + gap)
                gy = gy0 + r * (cell + gap)
                col = DBLU if (r + c) % 2 == 0 else DGRAY
                rr(d, [gx, gy, gx+cell, gy+cell], sc(6), fill=(*col, a))
                # Like counter
                likes = int((r * cols + c + 1) * 847 * min(prog, 1.0))
                bb = d.textbbox((0,0), f"♥ {likes}", font=F_TAG)
                d.text((gx+sc(4), gy+cell-sc(14)), f"♥ {likes}",
                       font=F_TAG, fill=(*RED, a))
    else:
        # SHOT B: Schedule calendar
        pan_y = int(sc(10) * math.sin(ts * 0.35))
        cx = W // 2
        # Day labels
        days = ["L", "M", "X", "J", "V", "S", "D"]
        cell_w = sc(70); start_x = cx - len(days) * cell_w // 2
        header_y = H//2 - sc(130) + pan_y
        for di, day in enumerate(days):
            dx = start_x + di * cell_w
            bb = d.textbbox((0,0), day, font=F_TAG)
            a = 18
            d.text((dx+(cell_w-(bb[2]-bb[0]))//2, header_y),
                   day, font=F_TAG, fill=(*GRAY, a))
        # Scheduled post markers
        schedule = [(0,0), (0,2), (1,1), (1,4), (2,0), (2,3), (2,6),
                    (3,1), (3,5), (4,2), (4,4)]
        for week, day_i in schedule:
            if day_i >= len(days): continue
            prog = clamp((lt - (week*7+day_i)*0.12 - shot*SHOT_DUR) / 0.3)
            if prog <= 0: continue
            a = int(prog * 28)
            cell_h = sc(24)
            cx_cell = start_x + day_i * cell_w + cell_w//2
            cy_cell = header_y + sc(20) + week * (cell_h + sc(8))
            rr(d, [cx_cell-sc(22), cy_cell, cx_cell+sc(22), cy_cell+cell_h],
               sc(4), fill=(*BLUE, a))
        # Followers counter
        fcount = int(12340 * min(lt / 4.0, 1.0) ** 0.5)
        bb = d.textbbox((0,0), f"↑ {fcount:,} seguidores", font=F_BD)
        cx2 = W//2; cy2 = H//2 + sc(170) + pan_y
        a2 = int(min(lt / 2.0, 1.0) * 22)
        d.text((cx2-(bb[2]-bb[0])//2, cy2), f"↑ {fcount:,} seguidores",
               font=F_BD, fill=(*GREEN, a2))

def bg_invoice(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    draw_starfield(layer, tg, 100)
    shot, ts, _ = shot_info(lt)

    if shot % 2 == 0:
        # SHOT A: Stack of invoices scattered
        pan = int(sc(12) * math.sin(ts * 0.4))
        for i in range(4):
            angle = [-0.15, 0.08, -0.05, 0.12][i]
            bx = W//2 - sc(90) + i * sc(15) + pan
            by = H//2 - sc(120) + i * sc(12)
            bw, bh = sc(160), sc(200)
            prog = clamp((lt - i * 0.3) / 0.4)
            a = int(prog * 20)
            if a <= 0: continue
            # Rotated doc simulation (approximate with offset)
            offset_x = int(sc(20) * math.sin(angle))
            rr(d, [bx+offset_x, by, bx+offset_x+bw, by+bh], sc(6),
               fill=(*DGRAY, a), outline=(*LBLU, a//2), ow=1)
            # Lines on doc
            for li in range(5):
                ly = by + sc(28) + li * sc(28)
                lw2 = bw - sc(20) - (li % 2) * sc(25)
                d.line([(bx+offset_x+sc(10), ly), (bx+offset_x+sc(10)+lw2, ly)],
                       fill=(*GRAY, a), width=1)
            # Amount
            amounts = ["1.250€", "890€", "2.100€", "640€"]
            bb = d.textbbox((0,0), amounts[i], font=F_TAG)
            d.text((bx+offset_x+bw-sc(40), by+bh-sc(22)),
                   amounts[i], font=F_TAG, fill=(*GREEN, a))
        # Check marks appearing
        for ci in range(3):
            prog2 = clamp((lt - ci * 0.6 - 1.0) / 0.3)
            if prog2 <= 0: continue
            a2 = int(prog2 * 35)
            cx2 = W//4 * (ci+1) + pan//2
            cy2 = H//2 + sc(100)
            cr = sc(16)
            d.ellipse([cx2-cr, cy2-cr, cx2+cr, cy2+cr], fill=(*GREEN, a2))
            bb = d.textbbox((0,0), "✓", font=FB(sc(13)))
            d.text((cx2-(bb[2]-bb[0])//2, cy2-(bb[3]-bb[1])//2),
                   "✓", font=FB(sc(13)), fill=(*WHITE, a2))
    else:
        # SHOT B: Single invoice close-up with "PAGADO" stamp
        pan_x = int(sc(8) * math.cos(ts * 0.3))
        bw, bh = sc(220), sc(300)
        bx = W//2 - bw//2 + pan_x
        by = H//2 - bh//2
        prog = clamp(ts / 0.5)
        a = int(prog * 25)
        rr(d, [bx, by, bx+bw, by+bh], sc(8), fill=(*DGRAY, a))
        d.rounded_rectangle([bx, by, bx+bw, by+bh], radius=sc(8),
                             outline=(*LBLU, a//2), width=1)
        # Invoice lines
        for li in range(7):
            ly = by + sc(40) + li * sc(32)
            lw2 = bw - sc(24) - (li % 3) * sc(20)
            d.line([(bx+sc(12), ly), (bx+sc(12)+lw2, ly)],
                   fill=(*GRAY, a), width=1)
        # Total line
        d.line([(bx+sc(12), by+bh-sc(55)), (bx+bw-sc(12), by+bh-sc(55))],
               fill=(*LBLU, a), width=2)
        bb = d.textbbox((0,0), "TOTAL: 2.850€", font=FB(sc(11)))
        d.text((bx+bw-sc(12)-(bb[2]-bb[0]), by+bh-sc(44)),
               "TOTAL: 2.850€", font=FB(sc(11)), fill=(*WHITE, a))
        # PAGADO stamp
        stamp_prog = clamp((ts - 1.5) / 0.4)
        if stamp_prog > 0:
            sa = int(stamp_prog * 30)
            scx = bx + bw//2 + sc(30); scy = by + bh//2
            sr_w = sc(90); sr_h = sc(34)
            rr(d, [scx-sr_w//2, scy-sr_h//2, scx+sr_w//2, scy+sr_h//2],
               sc(5), outline=(*GREEN, sa), ow=3)
            bb2 = d.textbbox((0,0), "PAGADO", font=FB(sc(14)))
            d.text((scx-(bb2[2]-bb2[0])//2, scy-(bb2[3]-bb2[1])//2),
                   "PAGADO", font=FB(sc(14)), fill=(*GREEN, sa))

def bg_chart(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    draw_starfield(layer, tg, 100)
    shot, ts, _ = shot_info(lt)

    if shot % 2 == 0:
        # SHOT A: Dashboard panels (wide)
        pan = int(sc(10) * math.sin(ts * 0.35))
        # KPI cards
        kpis = [("CTR", "4.8%", LBLU), ("ROI", "320%", GREEN), ("CPC", "0.42€", AMBER), ("Conv.", "18%", TEAL)]
        card_w, card_h = sc(115), sc(65)
        kx0 = W//2 - (4*card_w + 3*sc(12))//2 + pan
        ky0 = H//2 - sc(160)
        for i, (name, val, col) in enumerate(kpis):
            prog = clamp((lt - i * 0.25) / 0.4)
            a = int(prog * 28)
            kx = kx0 + i * (card_w + sc(12))
            rr(d, [kx, ky0, kx+card_w, ky0+card_h], sc(8), fill=(*DGRAY, a))
            bb = d.textbbox((0,0), val, font=FB(sc(13)))
            d.text((kx+(card_w-(bb[2]-bb[0]))//2, ky0+sc(10)), val,
                   font=FB(sc(13)), fill=(*col, a))
            bb2 = d.textbbox((0,0), name, font=F_TAG)
            d.text((kx+(card_w-(bb2[2]-bb2[0]))//2, ky0+sc(34)), name,
                   font=F_TAG, fill=(*GRAY, a))
        # Line chart below KPIs
        chart_y = ky0 + card_h + sc(30)
        chart_h2 = sc(100); chart_w2 = W - sc(80)
        cx0 = sc(40) + pan//2
        # Axis
        d.line([(cx0, chart_y+chart_h2), (cx0+chart_w2, chart_y+chart_h2)],
               fill=(*GRAY, 20), width=1)
        # Line points
        n_pts = 12
        pts = [0.3, 0.35, 0.4, 0.42, 0.38, 0.5, 0.6, 0.65, 0.72, 0.78, 0.82, 0.95]
        drawn = []
        for pi in range(n_pts):
            prog2 = clamp((lt - pi * 0.15) / 0.3)
            if prog2 <= 0: continue
            a2 = int(prog2 * 25)
            px = cx0 + int(pi / (n_pts-1) * chart_w2)
            py = chart_y + chart_h2 - int(pts[pi] * chart_h2)
            drawn.append((px, py, a2))
        for i in range(1, len(drawn)):
            d.line([drawn[i-1][:2], drawn[i][:2]], fill=(*LBLU, drawn[i][2]), width=sc(2))
            r_pt = sc(3)
            d.ellipse([drawn[i][0]-r_pt, drawn[i][1]-r_pt,
                       drawn[i][0]+r_pt, drawn[i][1]+r_pt], fill=(*LBLU, drawn[i][2]))
    else:
        # SHOT B: Close-up on single bar chart
        pan_x = int(sc(10) * math.cos(ts * 0.4))
        bars = [("Ene", 0.4), ("Feb", 0.5), ("Mar", 0.62), ("Abr", 0.55),
                ("May", 0.78), ("Jun", 0.95)]
        bw2 = sc(65); gap2 = sc(20)
        total_w = len(bars) * (bw2 + gap2)
        bx0 = W//2 - total_w//2 + pan_x
        by0 = H//2 + sc(60)
        for i, (label, h_rel) in enumerate(bars):
            prog = clamp((lt - i * 0.2 - shot * SHOT_DUR) / 0.5)
            a = int(prog * 30)
            if a <= 0: continue
            bh2 = int(sc(200) * h_rel * prog)
            bx2 = bx0 + i * (bw2 + gap2)
            by2 = by0 - bh2
            rr(d, [bx2, by2, bx2+bw2, by0], sc(4), fill=(*BLUE, a))
            d.rectangle([bx2, by2, bx2+bw2, by2+sc(4)], fill=(*LBLU, a))
            bb = d.textbbox((0,0), label, font=F_TAG)
            d.text((bx2+(bw2-(bb[2]-bb[0]))//2, by0+sc(6)), label,
                   font=F_TAG, fill=(*GRAY, a))
            pct = f"+{int(h_rel*100)}%"
            bb2 = d.textbbox((0,0), pct, font=F_TAG)
            d.text((bx2+(bw2-(bb2[2]-bb2[0]))//2, by2-sc(16)), pct,
                   font=F_TAG, fill=(*GREEN, a))

def bg_cta(layer, lt, tg):
    d = ImageDraw.Draw(layer)
    draw_starfield(layer, tg, 200)
    cx, cy = W//2, H//2
    # Radial glow explosion
    for ring in range(7):
        phase = (lt * 0.6 + ring * 0.5) % 3.5
        a = int(20 * max(0, 1 - phase / 3.5))
        r = int(sc(40) + phase * sc(280))
        d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(*BLUE, a), width=sc(3))
    # Particles
    rng2 = random.Random(99)
    for p_i in range(30):
        angle = rng2.random() * 2 * math.pi + tg * 0.2
        dist  = rng2.random() * sc(350) * min(lt / 2.0, 1.0)
        px2 = cx + int(dist * math.cos(angle))
        py2 = cy + int(dist * math.sin(angle))
        pr  = sc(2) + int(sc(3) * rng2.random())
        pulse2 = (math.sin(tg * 2 + p_i) + 1) / 2
        pa = int((15 + 25 * pulse2) * min(lt / 1.5, 1.0))
        col_choices = [BLUE, LBLU, WHITE]
        col2 = col_choices[p_i % 3]
        d.ellipse([px2-pr, py2-pr, px2+pr, py2+pr], fill=(*col2, pa))

BG_FNS = {
    "intro":   bg_intro,
    "chat":    bg_chat,
    "email":   bg_email,
    "social":  bg_social,
    "invoice": bg_invoice,
    "chart":   bg_chart,
    "cta":     bg_cta,
}

# ── Icon renderers (center visual per scene) ──────────────────────────────────
def draw_icon_chat(d, cx, cy, sz, lt):
    t = lt % 2.0
    bw, bh = int(sz*0.85), int(sz*0.58)
    x0 = cx - bw//2; y0 = cy - bh//2
    d.rounded_rectangle([x0, y0, x0+bw, y0+bh], radius=sc(10), fill=(*BLUE, 220))
    d.polygon([(x0+sc(20), y0+bh), (x0+sc(8), y0+bh+sc(14)), (x0+sc(36), y0+bh)],
              fill=(*BLUE, 220))
    for i, dx in enumerate([cx-sc(18), cx, cx+sc(18)]):
        beat = (math.sin(t*math.pi*3 - i*1.0) + 1) / 2
        dy2  = int(sc(4)*beat)
        dr   = sc(5)
        d.ellipse([dx-dr, cy-dr-dy2, dx+dr, cy+dr-dy2], fill=(*WHITE, 220))
    # Bot label
    bb = d.textbbox((0,0), "BOT", font=F_TAG)
    d.text((cx-(bb[2]-bb[0])//2, y0+bh+sc(18)), "BOT", font=F_TAG, fill=(*LBLU, 200))

def draw_icon_email(d, cx, cy, sz, lt):
    ew, eh = int(sz*0.82), int(sz*0.56)
    x0 = cx-ew//2; y0 = cy-eh//2
    d.rounded_rectangle([x0, y0, x0+ew, y0+eh], radius=sc(6),
                        fill=(*DGRAY, 220), outline=(*LBLU, 200), width=sc(2))
    d.polygon([(x0, y0), (cx, cy-sc(6)), (x0+ew, y0)], fill=(*LBLU, 70))
    d.line([(x0, y0), (cx, cy-sc(6)), (x0+ew, y0)], fill=(*LBLU, 180), width=sc(2))
    # Cascade arrows
    for i in range(3):
        delay = i * 0.25
        prog  = clamp((lt - delay) / 0.4)
        if prog <= 0: continue
        ax = x0+ew+sc(14)+int(sc(32)*prog)
        ay = cy + (i-1)*sc(16)
        a2 = int(230 * prog * (1-max(0, prog-0.7)/0.3))
        al = sc(18)
        d.line([(ax, ay), (ax+al, ay)], fill=(*LBLU, a2), width=sc(3))
        d.polygon([(ax+al, ay), (ax+al-sc(7), ay-sc(5)), (ax+al-sc(7), ay+sc(5))],
                  fill=(*LBLU, a2))

def draw_icon_social(d, cx, cy, sz, lt):
    pw, ph = int(sz*0.5), int(sz*0.82)
    x0 = cx-pw//2; y0 = cy-ph//2
    d.rounded_rectangle([x0, y0, x0+pw, y0+ph], radius=sc(10),
                        fill=(*DGRAY, 220), outline=(*LBLU, 180), width=sc(2))
    sx = x0+sc(6); sy = y0+sc(12)
    sw = pw-sc(12); img_h = int((ph-sc(24))*0.55)
    a_img = int(255*clamp(lt/0.5))
    d.rectangle([sx, sy, sx+sw, sy+img_h], fill=(*DBLU, a_img))
    # Play button
    mx = sx+sw//2; my = sy+img_h//2
    d.polygon([(mx-sc(8), my-sc(10)), (mx-sc(8), my+sc(10)), (mx+sc(10), my)],
              fill=(*LBLU, a_img))
    # Like counter
    lv = int(1234*clamp((lt-0.3)/0.6)**0.7) if lt > 0.3 else 0
    a_l = int(255*clamp((lt-0.3)/0.3))
    d.text((sx+sc(4), sy+img_h+sc(6)), f"♥ {lv:,}", font=F_TAG, fill=(*RED, a_l))

def draw_icon_invoice(d, cx, cy, sz, lt):
    dw, dh = int(sz*0.68), int(sz*0.82)
    x0 = cx-dw//2; y0 = cy-dh//2
    fold = sc(18)
    d.polygon([(x0, y0), (x0+dw-fold, y0), (x0+dw, y0+fold),
               (x0+dw, y0+dh), (x0, y0+dh)], fill=(*DGRAY, 220))
    d.polygon([(x0+dw-fold, y0), (x0+dw, y0+fold), (x0+dw-fold, y0+fold)],
              fill=(*BLUE, 180))
    d.polygon([(x0, y0), (x0+dw-fold, y0), (x0+dw, y0+fold),
               (x0+dw, y0+dh), (x0, y0+dh)], outline=(*LBLU, 160), width=sc(2))
    for i, fy in enumerate([0.25, 0.40, 0.55, 0.68]):
        a = int(220*clamp((lt-i*0.12)/0.25))
        lx2 = x0+dw-sc(10)-(sc(16)*(i%2))
        d.line([(x0+sc(10), y0+int(dh*fy)), (lx2, y0+int(dh*fy))],
               fill=(*GRAY, a), width=sc(2))
    a_ck = int(255*clamp((lt-0.5)/0.4))
    if a_ck > 0:
        cr = sc(16); ccx = x0+dw-sc(4); ccy = y0+dh-sc(6)
        d.ellipse([ccx-cr, ccy-cr, ccx+cr, ccy+cr], fill=(*GREEN, a_ck))
        prog = clamp((lt-0.5)/0.5)
        p1=(ccx-sc(8), ccy); p2=(ccx-sc(2), ccy+sc(7)); p3=(ccx+sc(9), ccy-sc(8))
        d.line([p1, p2], fill=(255,255,255,a_ck), width=sc(3))
        if prog > 0.5:
            d.line([p2, p3], fill=(255,255,255,int(a_ck*(prog*2-1))), width=sc(3))

def draw_icon_chart(d, cx, cy, sz, lt):
    ch = int(sz*0.72); cw = int(sz*0.88)
    x0 = cx-cw//2; yb = cy+ch//2
    heights = [0.4, 0.62, 0.78, 0.55, 0.95]
    bw2 = int(cw/(len(heights)*1.6))
    gap2 = int((cw-bw2*len(heights))/(len(heights)+1))
    for i, rh in enumerate(heights):
        prog = clamp((lt-i*0.12)/0.45)
        a = int(220*prog); bh2 = int(ch*rh*prog)
        bx2 = x0+gap2+i*(bw2+gap2); by2 = yb-bh2
        col = BLUE if i < len(heights)-1 else LBLU
        d.rectangle([bx2, by2, bx2+bw2, yb], fill=(*col, a))
        d.rectangle([bx2, by2, bx2+bw2, by2+sc(3)], fill=(*WHITE, a//2))
        a2 = int(220*clamp((lt-i*0.12-0.3)/0.25))
        if a2 > 0:
            pct = f"{int(rh*100)}%"
            bb = d.textbbox((0,0), pct, font=F_TAG)
            d.text((bx2+(bw2-(bb[2]-bb[0]))//2, by2-sc(15)), pct,
                   font=F_TAG, fill=(*WHITE, a2))
    d.line([(x0, yb), (x0+cw, yb)], fill=(*GRAY, 160), width=sc(2))

def draw_icon_intro(d, cx, cy, sz, lt):
    a = int(220*clamp(lt/0.4))
    bb = d.textbbox((0,0), "?", font=FB(sc(80)))
    d.text((cx-(bb[2]-bb[0])//2, cy-(bb[3]-bb[1])//2),
           "?", font=FB(sc(80)), fill=(*LBLU, a))

def draw_icon_cta(d, cx, cy, sz, lt, img_ref):
    # Draw the actual logo PNG at center
    a = int(255*clamp(lt/0.6))
    target_w = int(sz * 1.6)
    limg = load_logo_for_header(LOGO_PNG, target_w)
    lx = cx - limg.width // 2
    ly = cy - limg.height // 2
    layer2 = Image.new('RGBA', img_ref.size, (0,0,0,0))
    layer2.paste(limg, (lx, ly), limg)
    # Apply alpha
    r2, g2, b2, a2 = layer2.split()
    a2_mod = a2.point(lambda p: int(p * a / 255))
    layer2.putalpha(a2_mod)
    alpha_composite_onto(img_ref, layer2)

ICON_FNS = {
    "intro":   draw_icon_intro,
    "chat":    draw_icon_chat,
    "email":   draw_icon_email,
    "social":  draw_icon_social,
    "invoice": draw_icon_invoice,
    "chart":   draw_icon_chart,
}

# ── Header bar with real logo ─────────────────────────────────────────────────
def draw_header(img, alpha_f=1.0):
    """White bar at top with real PNG logo centered."""
    a = int(240 * alpha_f)
    layer = Image.new('RGBA', img.size, (0,0,0,0))
    d = ImageDraw.Draw(layer)
    # White bar (slight transparency to blend with video edge)
    d.rectangle([0, 0, W, HEADER_H], fill=(255, 255, 255, a))
    # Logo centered
    lx = (W - LOGO_IMG.width) // 2
    ly = (HEADER_H - LOGO_IMG.height) // 2
    # Apply alpha to logo
    logo_copy = LOGO_IMG.copy()
    lr, lg, lb, la = logo_copy.split()
    la_mod = la.point(lambda p: int(p * alpha_f))
    logo_copy.putalpha(la_mod)
    layer.paste(logo_copy, (lx, ly), logo_copy)
    alpha_composite_onto(img, layer)

# ── Scene content ─────────────────────────────────────────────────────────────
def render_scene_content(img, scene_idx, lt, tg):
    sid, label, title, bg_type, accent = SCENE_DEFS[scene_idx]
    d = ImageDraw.Draw(img)
    cx = W // 2

    alpha_f = clamp(lt / 0.35)
    slide_f = 1.0 - eo(clamp(lt / 0.40)) if lt < 0.40 else 0.0

    # ── Background layer
    bg_layer = Image.new('RGBA', img.size, (0,0,0,0))
    BG_FNS.get(bg_type, bg_intro)(bg_layer, lt, tg)
    alpha_composite_onto(img, bg_layer)
    d = ImageDraw.Draw(img)

    # ── Scene counter pill (top right)
    if label:
        a_l = int(255 * alpha_f)
        px0 = W - sc(72); py0 = sc(6); px1 = W - sc(14); py1 = sc(42)
        rr(d, [px0, py0, px1, py1], sc(6), fill=(*DBLU, a_l), outline=(*BLUE, a_l//2), ow=1)
        bb = d.textbbox((0,0), label, font=F_FRAC)
        d.text((px0+(px1-px0-(bb[2]-bb[0]))//2, py0+(py1-py0-(bb[3]-bb[1]))//2),
               label, font=F_FRAC, fill=(*LBLU, a_l))

    # ── Icon area (vertical center of usable area = HEADER_H to KARAOKE_Y)
    content_top = HEADER_H + sc(20)
    content_bot = H - sc(220)   # above karaoke bar
    content_cy  = (content_top + content_bot) // 2 - sc(30)
    icon_y      = content_cy - sc(50) + int(sc(40) * slide_f)
    icon_sz     = sc(110)

    # Glow behind icon
    glow = glow_layer(img.size, cx, icon_y, icon_sz//2, accent, 30)
    alpha_composite_onto(img, glow)
    d = ImageDraw.Draw(img)

    # Icon
    if bg_type == "cta":
        draw_icon_cta(d, cx, icon_y, icon_sz, lt, img)
        d = ImageDraw.Draw(img)
    elif bg_type in ICON_FNS:
        ICON_FNS[bg_type](d, cx, icon_y, icon_sz, lt)

    # ── Title
    title_y = icon_y + icon_sz//2 + sc(28) + int(sc(28)*slide_f)
    a_t = int(255 * alpha_f)
    for line in title.split('\n'):
        bb = d.textbbox((0,0), line, font=F_H1)
        lw = bb[2]-bb[0]; lh = bb[3]-bb[1]
        d.text((cx-lw//2, title_y), line, font=F_H1, fill=(*WHITE, a_t))
        title_y += lh + sc(5)

    # Accent underline
    if alpha_f > 0.1:
        d.line([(cx-sc(50), title_y+sc(6)), (cx+sc(50), title_y+sc(6))],
               fill=(*accent, int(180*alpha_f)), width=sc(2))

# ── Karaoke subtitle renderer ─────────────────────────────────────────────────
def render_karaoke(img, sentences, t_ms):
    """
    sentences: list of {text, start_ms, dur_ms, words: [{word, start_ms, duration_ms}]}
    Karaoke style: full sentence visible, past words WHITE, current word BLUE+bold, future GRAY.
    """
    if not sentences: return

    # Find active sentence
    active = None
    for sent in sentences:
        end_ms = sent['start_ms'] + sent['dur_ms'] + 400
        if sent['start_ms'] <= t_ms <= end_ms:
            active = sent
            break
    if active is None:
        # Show last sentence for trailing time
        for sent in reversed(sentences):
            if t_ms > sent['start_ms']:
                active = sent
                break
    if active is None: return

    words = active['words']
    all_word_texts = [w['word'] for w in words]

    # Bar background
    bar_y  = H - sc(225)
    bar_h  = sc(130)
    bar_x  = sc(16)
    bar_w  = W - sc(32)

    layer = Image.new('RGBA', img.size, (0,0,0,0))
    dl = ImageDraw.Draw(layer)
    dl.rounded_rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h],
                          radius=sc(12), fill=(0, 0, 0, 190))
    alpha_composite_onto(img, layer)

    d = ImageDraw.Draw(img)
    max_line_w = bar_w - sc(40)

    # Layout words into lines
    lines = [[]]
    lw_acc = 0
    for wi, w_obj in enumerate(words):
        wt = w_obj['word']
        is_cur = (w_obj['start_ms'] <= t_ms < w_obj['start_ms'] + w_obj['duration_ms'] + 50)
        f = F_SUB_H if is_cur else F_SUB_N
        bb = d.textbbox((0,0), wt + ' ', font=f)
        ww = bb[2] - bb[0]
        if lw_acc + ww > max_line_w and lines[-1]:
            lines.append([])
            lw_acc = 0
        lines[-1].append(wi)
        lw_acc += ww

    # Keep only last 2 lines containing or just past current word
    # Find which line has the current word
    cur_line = 0
    for li, line_idxs in enumerate(lines):
        for wi in line_idxs:
            w_obj = words[wi]
            if w_obj['start_ms'] <= t_ms < w_obj['start_ms'] + w_obj['duration_ms'] + 50:
                cur_line = li
    display_lines = lines[max(0, cur_line-1):cur_line+2]

    line_h = sc(32)
    total_disp_h = len(display_lines) * line_h
    y_start = bar_y + (bar_h - total_disp_h) // 2

    for line_idxs in display_lines:
        # Calculate line width
        line_total_w = 0
        for wi in line_idxs:
            w_obj = words[wi]
            is_cur = (w_obj['start_ms'] <= t_ms < w_obj['start_ms'] + w_obj['duration_ms'] + 50)
            is_past = w_obj['start_ms'] + w_obj['duration_ms'] < t_ms
            f = F_SUB_H if is_cur else F_SUB_N
            bb = d.textbbox((0,0), w_obj['word'] + ' ', font=f)
            line_total_w += bb[2] - bb[0]

        x = W//2 - line_total_w//2
        for wi in line_idxs:
            w_obj = words[wi]
            is_cur = (w_obj['start_ms'] <= t_ms < w_obj['start_ms'] + w_obj['duration_ms'] + 50)
            is_past = w_obj['start_ms'] + w_obj['duration_ms'] < t_ms

            if is_cur:
                f   = F_SUB_H
                col = LBLU
                # Highlight background
                bb  = d.textbbox((0,0), w_obj['word'], font=f)
                ww  = bb[2] - bb[0]; wh = bb[3] - bb[1]
                hl_layer = Image.new('RGBA', img.size, (0,0,0,0))
                dhl = ImageDraw.Draw(hl_layer)
                dhl.rounded_rectangle([x-sc(3), y_start-sc(2),
                                        x+ww+sc(3), y_start+wh+sc(2)],
                                       radius=sc(4), fill=(*BLUE, 60))
                alpha_composite_onto(img, hl_layer)
                d = ImageDraw.Draw(img)
            elif is_past:
                f   = F_SUB_P
                col = WHITE
            else:
                f   = F_SUB_N
                col = GRAY

            bb = d.textbbox((0,0), w_obj['word'] + ' ', font=f)
            d.text((x, y_start), w_obj['word'], font=f, fill=col)
            x += bb[2] - bb[0]

        y_start += line_h

# ── URL bar ───────────────────────────────────────────────────────────────────
def draw_url_bar(img, alpha_f=1.0):
    a = int(255 * alpha_f)
    d = ImageDraw.Draw(img)
    url = "blastudios.vercel.app"
    bb = d.textbbox((0,0), url, font=F_TAG)
    cx = W // 2
    d.text((cx-(bb[2]-bb[0])//2, H-sc(38)), url, font=F_TAG, fill=(*GRAY, a))

# ── Audio generation ──────────────────────────────────────────────────────────
async def generate_audio():
    print("Generando audio con edge-tts...")
    communicate = edge_tts.Communicate(SCRIPT, voice=VOICE, rate="+5%")
    raw_sents  = []
    audio_chunks = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "SentenceBoundary":
            raw_sents.append({
                "text":     chunk["text"],
                "start_ms": chunk["offset"]   / 10000,
                "dur_ms":   chunk["duration"] / 10000,
            })

    audio_bytes = b"".join(audio_chunks)
    with open(TMP_A, "wb") as f:
        f.write(audio_bytes)

    print(f"  Audio: {len(audio_bytes)//1024} KB, {len(raw_sents)} oraciones")

    # Build per-word timing from sentence proportional distribution
    sentences = []
    flat_words = []
    for sent in raw_sents:
        raw_words = sent["text"].split()
        if not raw_words: continue
        total_chars = sum(max(1, len(w.strip("¿?.,;:!\"'()"))) for w in raw_words)
        cursor_ms   = sent["start_ms"] + 20
        eff_dur     = max(0, sent["dur_ms"] - 40)
        sent_words  = []
        for w in raw_words:
            clean = w.strip("¿?.,;:!\"'()")
            chars = max(1, len(clean))
            w_dur = eff_dur * chars / total_chars
            entry = {"word": w, "start_ms": cursor_ms, "duration_ms": w_dur}
            sent_words.append(entry)
            flat_words.append(entry)
            cursor_ms += w_dur
        sentences.append({
            "text":     sent["text"],
            "start_ms": sent["start_ms"],
            "dur_ms":   sent["dur_ms"],
            "words":    sent_words,
        })

    print(f"  Palabras: {len(flat_words)}, Oraciones: {len(sentences)}")
    return flat_words, sentences

# ── Scene timing ──────────────────────────────────────────────────────────────
def compute_scene_times(flat_words):
    numero_count = 0
    matched = [False] * 7
    scene_starts = [None] * 7

    for w in flat_words:
        wt = w["word"].strip("¿?.,;:!\"'()")

        if not matched[0] and wt == "Sabes":
            scene_starts[0] = w["start_ms"] - 120
            matched[0] = True

        if wt == "Número" and numero_count < 5:
            si = numero_count + 1
            if not matched[si]:
                scene_starts[si] = w["start_ms"]
                matched[si] = True
            numero_count += 1

        if not matched[6] and wt == "Blastudios":
            scene_starts[6] = w["start_ms"]
            matched[6] = True

    # Fallback
    last_ms = flat_words[-1]["start_ms"] + flat_words[-1]["duration_ms"]
    for i in range(7):
        if scene_starts[i] is None:
            scene_starts[i] = last_ms * i / 7
    return scene_starts

# ── Render loop ───────────────────────────────────────────────────────────────
def render_video(flat_words, sentences, total_ms):
    total_frames = int(math.ceil(total_ms / 1000 * FPS)) + FPS
    print(f"\nRenderizando {total_frames} frames ({total_ms/1000:.1f}s)...")

    scene_times = compute_scene_times(flat_words)
    print(f"  Escenas (ms): {[int(x) for x in scene_times]}")
    scene_times_ext = list(scene_times) + [total_ms + 5000]

    writer = imageio.get_writer(
        TMP_V, fps=FPS, codec='libx264', quality=None, bitrate='18M',
        output_params=['-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p']
    )
    t0 = time.time()

    for fi in range(total_frames):
        t_ms  = fi / FPS * 1000
        tg    = t_ms / 1000

        # Scene
        si = 0
        for k in range(len(scene_times_ext)-1):
            if k < len(SCENE_DEFS) and t_ms >= scene_times_ext[k]:
                si = k
        si  = min(si, len(SCENE_DEFS)-1)
        lt  = (t_ms - scene_times_ext[si]) / 1000

        # Build frame
        img = Image.new('RGB', (W, H), BG)
        render_scene_content(img, si, lt, tg)
        render_karaoke(img, sentences, t_ms)
        draw_header(img)
        draw_url_bar(img)

        writer.append_data(np.array(img))

        if fi % 60 == 0:
            elapsed = time.time() - t0
            eta     = elapsed / max(fi,1) * (total_frames - fi)
            pct     = (fi+1) / total_frames * 100
            print(f"  {fi+1}/{total_frames} ({pct:.0f}%) ETA {eta:.0f}s", end='\r')

    writer.close()
    print(f"\n  Video listo: {TMP_V}")

# ── Combine AV ────────────────────────────────────────────────────────────────
def combine_av():
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print("Combinando audio + video...")
    r = subprocess.run(
        [ffmpeg, '-y', '-i', TMP_V, '-i', TMP_A,
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', OUT],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("FFMPEG error:", r.stderr[-400:])
        raise RuntimeError("ffmpeg combine failed")
    sz = os.path.getsize(OUT) / 1024 / 1024
    print(f"  Reel final: {OUT}  ({sz:.1f} MB)")

def cleanup():
    for f in [TMP_V, TMP_A]:
        try:
            if os.path.exists(f): os.remove(f)
        except: pass

# ── Entry point ───────────────────────────────────────────────────────────────
async def main():
    os.makedirs(DIR, exist_ok=True)
    flat_words, sentences = await generate_audio()
    if not flat_words:
        print("ERROR: sin timing de palabras"); return

    last = flat_words[-1]
    total_ms = last["start_ms"] + last["duration_ms"] + 1000
    print(f"  Duracion total: {total_ms/1000:.1f}s")

    render_video(flat_words, sentences, total_ms)
    combine_av()
    cleanup()
    print("REEL COMPLETADO:", OUT)

if __name__ == "__main__":
    asyncio.run(main())
