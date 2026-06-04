"""
Reel Blastudios – 5 cosas que tu competencia automatiza y tú no
Pipeline: edge-tts → audio MP3 + word timing → Pillow frames → ffmpeg H.264 + audio
"""

import asyncio, os, math, sys, subprocess, tempfile, time
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio.v2 as imageio
import imageio_ffmpeg

# ── Config ─────────────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
SCALE  = W / 390

def sc(v): return int(round(v * SCALE))

FD    = r"C:\Windows\Fonts"
VOICE = "es-ES-AlvaroNeural"

DIR   = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram"
OUT   = os.path.join(DIR, "reel_blastudios_automatizacion.mp4")
TMP_V = os.path.join(DIR, "_tmp_video.mp4")
TMP_A = os.path.join(DIR, "_tmp_audio.mp3")

# ── Colors ──────────────────────────────────────────────────────────────────
BG    = ( 11,  11,  18)
BLUE  = ( 37,  99, 235)
LBLU  = ( 96, 165, 250)
DBLU  = ( 10,  20,  55)
WHITE = (248, 250, 252)
GRAY  = (130, 135, 155)
DGRAY = ( 32,  34,  44)
AMBER = (245, 158,  11)
RED   = (220,  50,  47)
GREEN = ( 34, 197,  94)

# ── Fonts ───────────────────────────────────────────────────────────────────
def _fnt(name, sz):
    try:    return ImageFont.truetype(os.path.join(FD, name), sz)
    except: return ImageFont.load_default()

def FB(s): return _fnt('segoeuib.ttf', s)
def FR(s): return _fnt('segoeui.ttf',  s)
def FL(s): return _fnt('segoeuil.ttf', s)

# Pre-build fonts once
F_NUM   = FB(sc(68))    # big scene number
F_H1    = FB(sc(22))    # scene title
F_H2    = FB(sc(17))    # scene subtitle/label
F_BD    = FR(sc(12))    # body text
F_SUB   = FB(sc(13))    # subtitle words (normal)
F_SUBHI = FB(sc(14))    # subtitle current word (slightly bigger)
F_LOGO  = FB(sc( 9))    # logo watermark
F_FRAC  = FR(sc(10))    # "x/5" fraction

# ── Script (full narration) ─────────────────────────────────────────────────
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

# Scene definitions: (scene_id, label, title, icon_type, accent_color)
SCENE_DEFS = [
    ("intro",  "",    "¿Sabes qué hace\ntu competencia\nmientras duermes?", "eye",      BLUE),
    ("s1",     "1/5", "Atención\nal cliente",                               "chat",     LBLU),
    ("s2",     "2/5", "Secuencias\nde email",                               "email",    LBLU),
    ("s3",     "3/5", "Redes\nsociales",                                    "social",   LBLU),
    ("s4",     "4/5", "Facturación\nautomática",                            "invoice",  LBLU),
    ("s5",     "5/5", "Análisis en\ntiempo real",                           "chart",    LBLU),
    ("cta",    "",    "Blastudios\nlo hace\npor ti.",                        "logo",     BLUE),
]

# Keywords that signal start of each scene (first word of that segment)
SCENE_START_WORDS = [
    "¿Sabes",     # intro
    "Número",     # s1 – first "Número"
    "Número",     # s2 – second "Número"
    "Número",     # s3
    "Número",     # s4
    "Número",     # s5
    "En",         # cta
]

# ── Easing helpers ──────────────────────────────────────────────────────────
def eo(t): return 1 - (1 - t)**3          # ease-out cubic
def eio(t):
    t *= 2
    if t < 1: return 0.5 * t**3
    t -= 2
    return 0.5 * (t**3 + 2)

def fade(start, dur, lt):
    if lt < start:        return 0.0
    if lt > start + dur:  return 1.0
    return eo((lt - start) / dur)

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))

# ── Drawing helpers ─────────────────────────────────────────────────────────
def centered_text(d, cx, y, text, font, fill):
    bb = d.textbbox((0, 0), text, font=font)
    w  = bb[2] - bb[0]
    d.text((cx - w // 2, y), text, font=font, fill=fill)
    return bb[3] - bb[1]

def multiline_centered(d, cx, y, text, font, fill, spacing=8):
    for line in text.split('\n'):
        h = centered_text(d, cx, y, line, font, fill)
        y += h + spacing

def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []
    line  = []
    for w in words:
        test = ' '.join(line + [w])
        bb   = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] <= max_w:
            line.append(w)
        else:
            if line: lines.append(' '.join(line))
            line = [w]
    if line: lines.append(' '.join(line))
    return lines

def alpha_paste(base, layer_rgba, pos=(0, 0)):
    base.paste(layer_rgba, pos, layer_rgba)

def rounded_rect(d, xy, r, fill, outline=None, ow=0):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill,
                        outline=outline, width=ow)

def glow_circle(img, cx, cy, radius, color, alpha=60):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(4, 0, -1):
        a = int(alpha * (i / 4) ** 2)
        r = radius + sc(8) * (4 - i + 1)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=(*color[:3], a))
    alpha_paste(img, layer)

# ── Logo (mini) ─────────────────────────────────────────────────────────────
def draw_mini_logo(img, cx, y, alpha_f=1.0):
    a = int(255 * alpha_f)
    lw = sc(22)
    lx = cx - lw // 2

    sq = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(sq)
    ds.rounded_rectangle([lx, y, lx + lw, y + lw], radius=sc(5),
                         fill=(*BLUE, a))
    ds.rectangle([lx + sc(5), y + sc(3), lx + sc(8), y + lw - sc(3)],
                 fill=(255, 255, 255, a))
    ds.ellipse([lx + sc(10), y + sc(11), lx + sc(19), y + lw - sc(2)],
               fill=(255, 255, 255, a))
    ds.ellipse([lx + sc(12), y + sc(14), lx + sc(17), y + lw - sc(5)],
               fill=(*BLUE, a))
    alpha_paste(img, sq)

    d = ImageDraw.Draw(img)
    tw = d.textbbox((0, 0), "blastudios", font=F_LOGO)
    d.text((cx - (tw[2] - tw[0]) // 2 + lw // 2 + sc(4),
            y + (lw - (tw[3] - tw[1])) // 2),
           "blastudios", font=F_LOGO, fill=(*WHITE, a))

# ── Icon drawers ────────────────────────────────────────────────────────────
def icon_chat(d, cx, cy, sz, t=1.0):
    """Animated chat bubble with typing dots."""
    bw, bh = int(sz * 0.9), int(sz * 0.65)
    x0 = cx - bw // 2; y0 = cy - bh // 2
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=sc(10),
                        fill=(*BLUE, 220))
    # tail
    d.polygon([(x0 + sc(18), y0 + bh),
               (x0 + sc(8),  y0 + bh + sc(12)),
               (x0 + sc(32), y0 + bh)], fill=(*BLUE, 220))
    # dots
    dot_r = sc(5)
    positions = [cx - sc(18), cx, cx + sc(18)]
    for i, dx in enumerate(positions):
        beat_i = (math.sin(t * math.pi * 2 * 1.5 - i * 1.0) + 1) / 2
        dy = int(sc(3) * beat_i)
        d.ellipse([dx - dot_r, cy - dot_r - dy,
                   dx + dot_r, cy + dot_r - dy],
                  fill=(*WHITE, 230))

    # second bubble (response, arrives with t)
    if t > 0.3:
        a2 = int(255 * clamp((t - 0.3) / 0.4))
        bw2 = int(bw * 0.65)
        x2 = cx + sc(28); y2 = cy + sc(28)
        d.rounded_rectangle([x2, y2, x2 + bw2, y2 + bh * 0.8],
                             radius=sc(8), fill=(*DGRAY, a2),
                             outline=(*LBLU, a2 // 2), width=2)
        dot2_r = sc(4)
        for i, ddx in enumerate([-sc(12), 0, sc(12)]):
            d.ellipse([x2 + bw2 // 2 + ddx - dot2_r, y2 + int(bh * 0.4) - dot2_r,
                       x2 + bw2 // 2 + ddx + dot2_r, y2 + int(bh * 0.4) + dot2_r],
                      fill=(*LBLU, a2))

def icon_email(d, cx, cy, sz, t=1.0):
    """Envelope with cascade of copy arrows."""
    ew = int(sz * 0.85); eh = int(sz * 0.6)
    x0 = cx - ew // 2; y0 = cy - eh // 2
    d.rounded_rectangle([x0, y0, x0 + ew, y0 + eh], radius=sc(6),
                        fill=(*DGRAY, 220), outline=(*LBLU, 200), width=sc(2))
    # Envelope flap (V shape)
    d.polygon([(x0, y0), (cx, cy - sc(4)), (x0 + ew, y0)],
              fill=(*LBLU, 80))
    d.line([(x0, y0), (cx, cy - sc(4)), (x0 + ew, y0)],
           fill=(*LBLU, 200), width=sc(2))

    # Animated cascade arrows (3 copies sent)
    for i in range(3):
        delay = i * 0.28
        prog  = clamp((t - delay) / 0.4)
        if prog <= 0: continue
        ax = x0 + ew + sc(12) + int(sc(30) * prog)
        ay = cy + (i - 1) * sc(16)
        a  = int(255 * prog * (1 - max(0, prog - 0.7) / 0.3))
        arrow_len = sc(20)
        d.line([(ax, ay), (ax + arrow_len, ay)],
               fill=(*LBLU, a), width=sc(3))
        d.polygon([(ax + arrow_len, ay),
                   (ax + arrow_len - sc(7), ay - sc(5)),
                   (ax + arrow_len - sc(7), ay + sc(5))],
                  fill=(*LBLU, a))

def icon_social(d, cx, cy, sz, t=1.0):
    """Phone frame with post & likes counter."""
    pw = int(sz * 0.52); ph = int(sz * 0.85)
    x0 = cx - pw // 2; y0 = cy - ph // 2
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=sc(10),
                        fill=(*DGRAY, 220), outline=(*LBLU, 180), width=sc(2))
    # Screen content
    sx = x0 + sc(6); sy = y0 + sc(12)
    sw = pw - sc(12); sh = ph - sc(24)
    d.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=sc(5),
                        fill=(*BG, 200))
    # Post image placeholder
    img_h = int(sh * 0.55)
    a_img = int(255 * clamp(t / 0.5))
    d.rectangle([sx, sy, sx + sw, sy + img_h], fill=(*DBLU, a_img))
    # Small play / image icon
    mid_x = sx + sw // 2; mid_y = sy + img_h // 2
    d.polygon([(mid_x - sc(8), mid_y - sc(10)),
               (mid_x - sc(8), mid_y + sc(10)),
               (mid_x + sc(10), mid_y)], fill=(*LBLU, a_img))
    # Likes counter animating up
    like_val = int(1234 * clamp((t - 0.3) / 0.6) ** 0.7)
    if like_val > 0:
        a_like = int(255 * clamp((t - 0.3) / 0.3))
        fy = sy + img_h + sc(4)
        d.text((sx + sc(4), fy), f"♥ {like_val:,}", font=F_FRAC,
               fill=(*RED, a_like))

def icon_invoice(d, cx, cy, sz, t=1.0):
    """Document with lines and an animated checkmark."""
    dw = int(sz * 0.7); dh = int(sz * 0.85)
    x0 = cx - dw // 2; y0 = cy - dh // 2
    # Folded corner
    fold = sc(18)
    d.polygon([(x0, y0), (x0 + dw - fold, y0),
               (x0 + dw, y0 + fold),
               (x0 + dw, y0 + dh),
               (x0, y0 + dh)], fill=(*DGRAY, 220))
    d.polygon([(x0 + dw - fold, y0),
               (x0 + dw, y0 + fold),
               (x0 + dw - fold, y0 + fold)], fill=(*BLUE, 180))
    d.polygon([(x0, y0), (x0 + dw - fold, y0),
               (x0 + dw, y0 + fold),
               (x0 + dw, y0 + dh),
               (x0, y0 + dh)],
              outline=(*LBLU, 160), width=sc(2))
    # Text lines
    line_col = (*GRAY, 180)
    lx1 = x0 + sc(10); lx2 = x0 + dw - sc(10)
    for i, ly_frac in enumerate([0.25, 0.40, 0.55, 0.68]):
        a_l = int(255 * clamp((t - i * 0.12) / 0.25))
        lx2_var = lx2 - sc(18) * (i % 2)
        d.line([(lx1, y0 + int(dh * ly_frac)),
                (lx2_var, y0 + int(dh * ly_frac))],
               fill=(*GRAY, a_l), width=sc(2))
    # Animated checkmark circle
    a_ck = int(255 * clamp((t - 0.5) / 0.4))
    if a_ck > 0:
        cr = sc(16); ccx = x0 + dw - sc(4); ccy = y0 + dh - sc(6)
        d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr],
                  fill=(*GREEN, a_ck))
        prog = clamp((t - 0.5) / 0.5)
        # Draw check mark proportionally
        p1 = (ccx - sc(8), ccy)
        p2 = (ccx - sc(2), ccy + sc(7))
        p3 = (ccx + sc(9), ccy - sc(8))
        if prog > 0.5:
            a_p = min(prog * 2 - 1, 1.0)
            d.line([p1, p2], fill=(255, 255, 255, a_ck), width=sc(3))
            d.line([p2, p3], fill=(255, 255, 255, int(a_ck * a_p)), width=sc(3))

def icon_chart(d, cx, cy, sz, t=1.0):
    """Animated bar chart growing upward."""
    chart_w = int(sz * 0.9); chart_h = int(sz * 0.75)
    x0 = cx - chart_w // 2; y_base = cy + chart_h // 2

    heights = [0.4, 0.6, 0.75, 0.55, 0.95]  # relative heights
    bar_w   = int(chart_w / (len(heights) * 1.6))
    gap     = int((chart_w - bar_w * len(heights)) / (len(heights) + 1))

    for i, rel_h in enumerate(heights):
        delay = i * 0.12
        prog  = clamp((t - delay) / 0.45)
        if prog <= 0: continue
        actual_h = int(chart_h * rel_h * prog)
        bx = x0 + gap + i * (bar_w + gap)
        by = y_base - actual_h
        # Gradient effect (darker at bottom)
        bar_color = BLUE if i < len(heights) - 1 else LBLU
        d.rectangle([bx, by, bx + bar_w, y_base],
                    fill=(*bar_color, 220))
        # Glow top
        d.rectangle([bx, by, bx + bar_w, by + sc(4)],
                    fill=(*WHITE, 120))
        # Value label on top bar
        a_v = int(255 * clamp((t - delay - 0.35) / 0.25))
        if a_v > 0:
            pct = f"{int(rel_h * 100)}%"
            tb = d.textbbox((0, 0), pct, font=F_FRAC)
            tw = tb[2] - tb[0]
            d.text((bx + (bar_w - tw) // 2, by - sc(14)), pct,
                   font=F_FRAC, fill=(*WHITE, a_v))

    # X axis line
    d.line([(x0, y_base), (x0 + chart_w, y_base)],
           fill=(*GRAY, 160), width=sc(2))

def icon_eye(d, cx, cy, sz, t=1.0):
    """Eye / question mark for intro."""
    # Big question mark
    a = int(255 * clamp(t / 0.4))
    d.text((cx - sc(30), cy - sc(50)), "?", font=FB(sc(80)),
           fill=(*LBLU, a))

def icon_logo_big(d, cx, cy, sz, t=1.0):
    """Blastudios logo mark (large)."""
    a = int(255 * clamp(t / 0.5))
    lw = int(sz * 0.8)
    x0 = cx - lw // 2; y0 = cy - lw // 2
    d.rounded_rectangle([x0, y0, x0 + lw, y0 + lw], radius=sc(20),
                        fill=(*BLUE, a))
    bw = int(lw * 0.11); bh = int(lw * 0.7)
    bx = x0 + int(lw * 0.27); by = y0 + int(lw * 0.15)
    d.rectangle([bx, by, bx + bw, by + bh], fill=(255, 255, 255, a))
    cr = int(lw * 0.185)
    ccx = x0 + int(lw * 0.59); ccy = y0 + int(lw * 0.70)
    d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr],
              fill=(255, 255, 255, a))
    d.ellipse([ccx - cr // 2, ccy - cr // 2,
               ccx + cr // 2, ccy + cr // 2],
              fill=(*BLUE, a))

ICON_FN = {
    "eye":     icon_eye,
    "chat":    icon_chat,
    "email":   icon_email,
    "social":  icon_social,
    "invoice": icon_invoice,
    "chart":   icon_chart,
    "logo":    icon_logo_big,
}

# ── Background: starfield + subtle grid ─────────────────────────────────────
import random
rng = random.Random(42)
STARS = [(rng.randint(0, W), rng.randint(0, H), rng.random()) for _ in range(120)]

def draw_background(img, t_global):
    img.paste(BG, [0, 0, W, H])
    d = ImageDraw.Draw(img)
    # Stars
    for sx, sy, bright in STARS:
        pulse = (math.sin(t_global * 0.8 + bright * 6.28) + 1) / 2
        a = int((0.15 + 0.35 * bright * pulse) * 255)
        r = 1 if bright < 0.5 else 2
        d.ellipse([sx - r, sy - r, sx + r, sy + r],
                  fill=(*WHITE, a))
    # Subtle blue radial glow at center
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    for step in range(5):
        ar = int(10 * (5 - step) / 5)
        hr = sc(300) + step * sc(80)
        dl.ellipse([W // 2 - hr, H // 2 - hr, W // 2 + hr, H // 2 + hr],
                   fill=(*BLUE, ar))
    alpha_paste(img, layer)

# ── Scene renderer ──────────────────────────────────────────────────────────
def render_scene(img, scene_idx, lt, t_global):
    """Render scene content. lt = local time within scene (seconds)."""
    sid, label, title, icon_type, color = SCENE_DEFS[scene_idx]
    d = ImageDraw.Draw(img)
    cx = W // 2

    # ── Entry easing
    slide_f = fade(0.0, 0.35, lt)
    alpha_f = fade(0.0, 0.30, lt)

    # ── Fraction label (top left, scenes 1-5)
    if label:
        a_l = int(255 * alpha_f)
        rounded_rect(d, [sc(20), sc(28), sc(76), sc(55)],
                     sc(5), fill=(*DBLU, a_l), outline=(*BLUE, a_l // 2), ow=1)
        tw = d.textbbox((0, 0), label, font=F_FRAC)
        d.text((sc(20) + (sc(56) - (tw[2] - tw[0])) // 2,
                sc(28) + (sc(27) - (tw[3] - tw[1])) // 2),
               label, font=F_FRAC, fill=(*LBLU, a_l))

    # ── Icon area (center of screen)
    icon_y_center = H // 2 - sc(80) + int(sc(60) * (1 - eo(slide_f)))
    icon_sz = sc(120)
    icon_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    di = ImageDraw.Draw(icon_layer)

    glow_circle(img, cx, icon_y_center, icon_sz // 2, color, alpha=20)
    anim_t = min(lt / 0.8, 1.0) if lt < 0.8 else (lt - 0.8) % 2.0
    ICON_FN[icon_type](di, cx, icon_y_center, icon_sz, anim_t)
    alpha_paste(img, icon_layer)
    d = ImageDraw.Draw(img)

    # ── Title block
    title_y = icon_y_center + icon_sz // 2 + sc(28) + int(sc(30) * (1 - eo(slide_f)))
    title_a = int(255 * alpha_f)

    for line in title.split('\n'):
        tb = d.textbbox((0, 0), line, font=F_H1)
        lw = tb[2] - tb[0]; lh = tb[3] - tb[1]
        d.text((cx - lw // 2, title_y), line, font=F_H1,
               fill=(*WHITE, title_a))
        title_y += lh + sc(4)

    # ── Accent line
    if alpha_f > 0.1:
        line_a = int(200 * alpha_f)
        line_y = title_y + sc(8)
        line_len = sc(60)
        d.line([(cx - line_len // 2, line_y), (cx + line_len // 2, line_y)],
               fill=(*color, line_a), width=sc(2))

# ── Subtitle renderer ────────────────────────────────────────────────────────
def render_subtitles(img, words, t_ms, phrase_window_ms=3500):
    """Draw subtitle bar with current word highlighted."""
    if not words: return

    # Find active phrase: collect words in a [t - window, t + small_future] range
    # Show words from ~3.5 seconds ago up to 0.5s ahead
    window_start = t_ms - phrase_window_ms
    window_end   = t_ms + 500

    phrase_words = [
        w for w in words
        if w['start_ms'] >= window_start and w['start_ms'] <= window_end
    ]

    # Trim to max last 10 words
    if len(phrase_words) > 10:
        phrase_words = phrase_words[-10:]

    if not phrase_words: return

    # Bar background
    bar_h = sc(90)
    bar_y = H - sc(130) - bar_h

    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    dl.rounded_rectangle([sc(20), bar_y - sc(10),
                           W - sc(20), bar_y + bar_h + sc(10)],
                         radius=sc(12),
                         fill=(0, 0, 0, 160))
    alpha_paste(img, layer)

    d = ImageDraw.Draw(img)
    pad_x = sc(32)
    max_w = W - pad_x * 2

    # Layout subtitle words
    lines  = [[]]
    line_w = 0
    for wi in phrase_words:
        word_text = wi['word']
        # Use larger font for current word
        is_current = (wi['start_ms'] <= t_ms <
                      wi['start_ms'] + wi['duration_ms'] + 80)
        f  = F_SUBHI if is_current else F_SUB
        tb = d.textbbox((0, 0), word_text + ' ', font=f)
        ww = tb[2] - tb[0]
        if line_w + ww > max_w and lines[-1]:
            lines.append([])
            line_w = 0
        lines[-1].append((word_text, wi, is_current))
        line_w += ww

    # Render lines (max 2 lines from the bottom)
    lines = lines[-2:] if len(lines) > 2 else lines
    line_height = sc(28)
    total_h = len(lines) * line_height
    y_start = bar_y + (bar_h - total_h) // 2

    for line in lines:
        # Calculate total line width
        lw_total = 0
        for (wt, wi, is_cur) in line:
            f  = F_SUBHI if is_cur else F_SUB
            tb = d.textbbox((0, 0), wt + ' ', font=f)
            lw_total += tb[2] - tb[0]
        x = cx = W // 2
        x = x - lw_total // 2

        for (wt, wi, is_cur) in line:
            f    = F_SUBHI if is_cur else F_SUB
            col  = LBLU    if is_cur else WHITE
            tb   = d.textbbox((0, 0), wt + ' ', font=f)
            d.text((x, y_start), wt, font=f, fill=col)
            x += tb[2] - tb[0]

        y_start += line_height

# ── Bottom bar ───────────────────────────────────────────────────────────────
def draw_bottom_bar(img, alpha_f=1.0):
    a = int(255 * alpha_f)
    d = ImageDraw.Draw(img)
    url_text = "blastudios.vercel.app"
    tb = d.textbbox((0, 0), url_text, font=F_LOGO)
    tw = tb[2] - tb[0]
    d.text((W // 2 - tw // 2, H - sc(40)), url_text, font=F_LOGO,
           fill=(*GRAY, a))

# ── Audio generation ─────────────────────────────────────────────────────────
async def generate_audio():
    """
    edge-tts 7.x emits SentenceBoundary (not WordBoundary).
    We collect sentence timings and then distribute each sentence's
    duration proportionally among its words (by character count).
    """
    print("Generando audio con edge-tts...")
    communicate = edge_tts.Communicate(SCRIPT, voice=VOICE, rate="+5%")
    sentences  = []
    audio_chunks = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "SentenceBoundary":
            sentences.append({
                "text":       chunk["text"],
                "start_ms":   chunk["offset"]   / 10000,
                "dur_ms":     chunk["duration"] / 10000,
            })

    audio_bytes = b"".join(audio_chunks)
    with open(TMP_A, "wb") as f:
        f.write(audio_bytes)

    print(f"  Audio: {len(audio_bytes)//1024} KB, {len(sentences)} oraciones")

    # Distribute sentence timing → per-word timing
    words = []
    for sent in sentences:
        raw_words = sent["text"].split()
        if not raw_words:
            continue
        # Total characters (for proportional split)
        total_chars = sum(max(1, len(w.strip("¿?.,;:!\"'()")) ) for w in raw_words)
        cursor_ms   = sent["start_ms"]
        # Add a small gap at sentence start (20ms)
        cursor_ms  += 20
        effective_dur = max(0, sent["dur_ms"] - 20)

        for w in raw_words:
            clean  = w.strip("¿?.,;:!\"'()")
            chars  = max(1, len(clean))
            w_dur  = effective_dur * chars / total_chars
            words.append({
                "word":        w,
                "start_ms":    cursor_ms,
                "duration_ms": w_dur,
            })
            cursor_ms += w_dur

    print(f"  Palabras con timing: {len(words)}")
    return words

# ── Scene timing from word boundaries ────────────────────────────────────────
def compute_scene_times(words):
    """
    Returns list of scene start times (ms) by matching
    each scene's first word in SCENE_START_WORDS.
    """
    scene_starts = []
    TRIGGERS = [
        "¿Sabes",          # intro
        ("Número", 0),     # s1 – 1st occurrence of "Número"
        ("Número", 1),     # s2 – 2nd
        ("Número", 2),     # s3
        ("Número", 3),     # s4
        ("Número", 4),     # s5
        "En",              # cta
    ]
    numero_count = 0
    matched      = [False] * len(TRIGGERS)

    for w in words:
        wt = w["word"].strip("¿?.,;:!")

        # Check each trigger
        for i, trig in enumerate(TRIGGERS):
            if matched[i]: continue
            if isinstance(trig, tuple):
                keyword, nth = trig
                if wt == keyword:
                    if numero_count == nth:
                        scene_starts.append(w["start_ms"])
                        matched[i] = True
                    if nth == numero_count and not matched[i - 1 if i > 0 else i]:
                        pass
            else:
                if wt == trig.strip("¿?.,;:!"):
                    scene_starts.append(w["start_ms"])
                    matched[i] = True

        if wt == "Número":
            numero_count += 1

    # Fallback: evenly space if detection fails
    if len(scene_starts) < len(SCENE_DEFS):
        last_ms = (words[-1]["start_ms"] + words[-1]["duration_ms"]) if words else 30000
        scene_starts = [last_ms * i / len(SCENE_DEFS) for i in range(len(SCENE_DEFS))]
        print("  [WARN] Scene timing detection fallback used.")

    return scene_starts

# ── Main render ──────────────────────────────────────────────────────────────
def render_video(words, total_ms):
    total_frames = int(math.ceil(total_ms / 1000 * FPS)) + FPS  # +1s buffer
    print(f"\nRenderizando {total_frames} frames ({total_ms/1000:.1f}s)...")

    scene_times = compute_scene_times(words)
    print(f"  Tiempos de escena (ms): {[int(s) for s in scene_times]}")

    # Append sentinel
    scene_times_list = list(scene_times) + [total_ms + 5000]

    writer = imageio.get_writer(
        TMP_V,
        fps=FPS,
        codec='libx264',
        quality=None,
        bitrate='18M',
        output_params=['-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p']
    )

    t0 = time.time()
    for fi in range(total_frames):
        t_ms = fi / FPS * 1000

        # Determine scene
        scene_idx = 0
        for si in range(len(scene_times_list) - 1):
            if si < len(SCENE_DEFS) and t_ms >= scene_times_list[si]:
                scene_idx = si

        scene_idx = min(scene_idx, len(SCENE_DEFS) - 1)
        lt = (t_ms - scene_times_list[scene_idx]) / 1000  # local time in seconds
        t_global = t_ms / 1000

        # Build frame
        img = Image.new('RGB', (W, H), BG)
        draw_background(img, t_global)
        render_scene(img, scene_idx, lt, t_global)
        render_subtitles(img, words, t_ms)
        draw_mini_logo(img, W // 2, sc(14))
        draw_bottom_bar(img)

        writer.append_data(np.array(img))

        if fi % 90 == 0:
            elapsed = time.time() - t0
            pct = (fi + 1) / total_frames * 100
            eta = elapsed / (fi + 1) * (total_frames - fi - 1) if fi > 0 else 0
            print(f"  Frame {fi+1}/{total_frames} ({pct:.0f}%) – ETA {eta:.0f}s",
                  end='\r')

    writer.close()
    print(f"\n  Vídeo sin audio guardado en {TMP_V}")

# ── Combine audio + video ─────────────────────────────────────────────────────
def combine_av():
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    print("\nCombinando audio y vídeo...")
    result = subprocess.run([
        ffmpeg, '-y',
        '-i', TMP_V,
        '-i', TMP_A,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        OUT
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print("FFMPEG stderr:", result.stderr[-500:])
        raise RuntimeError("FFmpeg combine failed")
    print(f"  Reel final: {OUT}")
    sz = os.path.getsize(OUT) / (1024 * 1024)
    print(f"  Tamaño: {sz:.1f} MB")

# ── Cleanup temp files ────────────────────────────────────────────────────────
def cleanup():
    for f in [TMP_V, TMP_A]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except:
            pass

# ── Entry point ──────────────────────────────────────────────────────────────
async def main():
    import numpy as np  # lazy import

    os.makedirs(DIR, exist_ok=True)

    # 1. Generate audio
    words = await generate_audio()

    if not words:
        print("ERROR: no se obtuvo timing de palabras.")
        return

    last_w  = words[-1]
    total_ms = last_w["start_ms"] + last_w["duration_ms"] + 800  # +0.8s tail
    print(f"  Duración total: {total_ms/1000:.1f}s")

    # 2. Render frames
    render_video(words, total_ms)

    # 3. Combine
    combine_av()

    # 4. Cleanup
    cleanup()

    print("\nREEL COMPLETADO:", OUT)

if __name__ == "__main__":
    import numpy as np
    asyncio.run(main())
