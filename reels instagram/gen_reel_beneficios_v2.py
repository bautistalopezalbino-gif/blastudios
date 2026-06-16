#!/usr/bin/env python3
"""Generador de Reel Blastudios - Beneficios v2
   1080x1920  32s  con audio TTS, spring iOS, glassmorphism, karaoke"""
import os, math, time, asyncio, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio
import imageio_ffmpeg
import edge_tts

# ── CONFIG ────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
DUR    = 32
FRAMES = FPS * DUR
SCALE  = W / 390   # 2.769

OUT_DIR   = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram"
TMP_V     = os.path.join(OUT_DIR, "_tmp_bene_video.mp4")
TMP_A     = os.path.join(OUT_DIR, "_tmp_bene_audio.mp3")
OUT       = os.path.join(OUT_DIR, "reel_blastudios_beneficios.mp4")
FD        = r"C:\Windows\Fonts"
LOGO_PATH = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Fotos\blastudios-logo-Photoroom.png"

VOICE  = "es-ES-ElviraNeural"
SCRIPT = (
    "¿Tu negocio trabaja para ti... o tú para él? "
    "En Blastudios lo cambiamos. "
    "Primero: diseño web que convierte visitas en clientes reales. "
    "Segundo: campañas digitales basadas en datos, sin malgastar tu presupuesto. "
    "Tercero: inteligencia artificial que atiende a tus clientes, las veinticuatro horas. "
    "Y cuarto: una marca que comunica, que vende, que crece. "
    "No es suerte. Es sistema. "
    "Escríbenos hoy. blastudios punto vercel punto app."
)

def sc(v): return int(round(v * SCALE))

# ── COLORES ──────────────────────────────────────────────────────
BG    = (  8,   9,  14)
BLUE  = ( 37,  99, 235)
DBLU  = ( 13,  27,  62)
LBLU  = ( 96, 165, 250)
VIOL  = (139,  92, 246)
PINK  = (236,  72, 153)
GREEN = ( 34, 197,  94)
AMBER = (245, 158,  11)
WHITE = (248, 250, 252)
LGRAY = (185, 188, 200)
GRAY  = ( 80,  84, 100)

SCENE_ACCENT = [BLUE, LBLU, VIOL, PINK, GREEN, AMBER]

# ── FUENTES ──────────────────────────────────────────────────────
def fnt(name, sz):
    p = os.path.join(FD, name)
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()

FB = lambda s: fnt('segoeuib.ttf', s)
FR = lambda s: fnt('segoeui.ttf',  s)
FL = lambda s: fnt('segoeuil.ttf', s)

F_H1  = FB(sc(34))
F_H2  = FB(sc(26))
F_H3  = FB(sc(21))
F_NUM = FB(sc(60))
F_BD  = FR(sc(14))
F_SM  = FR(sc(12))
F_TAG = FB(sc(11))
F_KH  = FB(sc(18))
F_KN  = FR(sc(16))
F_KP  = FL(sc(15))

# ── LOGO ─────────────────────────────────────────────────────────
HDR_H         = sc(50)
LOGO_MAX_W    = sc(200)

def _load_logo():
    if not os.path.exists(LOGO_PATH):
        return None, 0, 0
    img = Image.open(LOGO_PATH).convert('RGBA')
    ow, oh = img.size
    nw = LOGO_MAX_W
    nh = int(oh * nw / ow)
    if nh > HDR_H - sc(10):
        nh = HDR_H - sc(10)
        nw = int(ow * nh / oh)
    return img.resize((nw, nh), Image.LANCZOS), nw, nh

LOGO_IMG, LOGO_W, LOGO_H = _load_logo()

# ── LAYOUT ───────────────────────────────────────────────────────
PIP_CY = HDR_H + sc(22)          # 193px — pips below header
CY     = H // 2 - sc(90)         # 711px — content center (shifted up)
PAD    = sc(24)                   # 66px
BW     = W - PAD * 2              # content width 948px
KARA_T = H - sc(240)             # 1256px — karaoke top
KARA_H = sc(130)                  # 360px — karaoke height
KARA_B = KARA_T + KARA_H         # 1616px
URL_Y  = KARA_B + sc(18)         # 1666px

# ── EASING ───────────────────────────────────────────────────────
def _c(v):       return max(0., min(1., v))
def eo(t):       return 1 - (1 - _c(t)) ** 3
def eio(t):      t = _c(t); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * _c(t)
def fade(s, d, t): return _c((t - s) / d) if d > 0 else (1. if t >= s else 0.)

def spring(t):
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    omega, zeta = 22.0, 0.52
    od  = omega * math.sqrt(max(0, 1 - zeta ** 2))
    val = 1 - math.exp(-zeta * omega * t) * (
        math.cos(od * t) + (zeta / math.sqrt(max(1e-9, 1 - zeta ** 2))) * math.sin(od * t)
    )
    return max(0.0, val)

# ── HELPERS ───────────────────────────────────────────────────────
def tw(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f); return b[2] - b[0]

def cxf(d, txt, f, ox=0, ow=W):
    return ox + (ow - tw(d, txt, f)) // 2

def wraptext(d, txt, f, maxw):
    words = txt.split(); lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if tw(d, test, f) <= maxw: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def new_layer():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def composite(img, layer):
    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')

def ac(col, a):
    return tuple(int(c * _c(a)) for c in col)

def otxt(img, pos, txt, font, col, a=1.0):
    if a <= 0.01: return img
    lay = new_layer()
    ImageDraw.Draw(lay).text(pos, txt, font=font, fill=(*col, int(a * 255)))
    return composite(img, lay)

def gtxt(img, pos, txt, font, col, gcol, gr=10, a=1.0):
    if a <= 0.01: return img
    gl = new_layer()
    ImageDraw.Draw(gl).text(pos, txt, font=font, fill=(*gcol, int(a * 85)))
    gl = gl.filter(ImageFilter.GaussianBlur(gr))
    base = Image.alpha_composite(img.convert('RGBA'), gl)
    return otxt(base.convert('RGB'), pos, txt, font, col, a)

def glass_rect(img, x0, y0, x1, y1, radius=sc(18), blur=12,
               fill=(255, 255, 255, 14), border=(255, 255, 255, 35)):
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(W, x1); y1 = min(H, y1)
    pad = blur * 2
    cx0 = max(0, x0 - pad); cy0 = max(0, y0 - pad)
    cx1 = min(W, x1 + pad); cy1 = min(H, y1 + pad)
    region = img.crop((cx0, cy0, cx1, cy1)).filter(ImageFilter.GaussianBlur(blur))
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=220)
    tmp = Image.new('RGB', (W, H))
    tmp.paste(region, (cx0, cy0))
    img.paste(tmp, mask=mask)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)
    d.rounded_rectangle([x0 + 2, y0 + 2, x1 - 2, min(y1, y0 + radius * 2 + 6)],
                        radius=radius, fill=(255, 255, 255, 10))
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=border, width=2)
    return composite(img, layer)

def orb(img, x, y, rad, col, s=0.28):
    sz = rad * 2
    o  = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
    od = ImageDraw.Draw(o)
    for r in range(rad, 0, max(1, rad // 22)):
        a = int(s * 255 * ((1 - r / rad) ** 0.55))
        od.ellipse([rad - r, rad - r, rad + r, rad + r], fill=(*col, a))
    o = o.filter(ImageFilter.GaussianBlur(rad // 4))
    base = img.convert('RGBA')
    px, py = x - rad, y - rad
    ox2, oy2, ow2, oh2 = 0, 0, sz, sz
    if px < 0:  ox2 = -px; ow2 = sz + px; px = 0
    if py < 0:  oy2 = -py; oh2 = sz + py; py = 0
    if px + ow2 > W: ow2 = W - px
    if py + oh2 > H: oh2 = H - py
    if ow2 > 0 and oh2 > 0:
        crop = o.crop([ox2, oy2, ox2 + ow2, oy2 + oh2])
        base.paste(crop, (px, py), crop)
    return base.convert('RGB')

# ── BACKGROUND ───────────────────────────────────────────────────
def draw_bg(img, si, t):
    accent = SCENE_ACCENT[min(si, len(SCENE_ACCENT) - 1)]
    p1 = math.sin(t * 0.65) * sc(16)
    p2 = math.cos(t * 0.48) * sc(13)
    img = orb(img, int(-sc(10) + p1), -sc(20), sc(200), accent, 0.22)
    img = orb(img, int(W + sc(10) + p2), H - sc(10), sc(170), BLUE, 0.18)
    img = orb(img, W // 2, CY + int(p1 * 0.4), sc(150), DBLU, 0.26)
    return img

# ── HEADER ────────────────────────────────────────────────────────
def draw_header(img, si=0):
    # En la escena final (s5 CTA) no hay header — pantalla completa para el CTA
    if si >= 5:
        return img
    lay = new_layer()
    d   = ImageDraw.Draw(lay)
    d.rectangle([0, 0, W, HDR_H], fill=(255, 255, 255, 242))
    if LOGO_IMG:
        lx = (W - LOGO_W) // 2
        ly = (HDR_H - LOGO_H) // 2
        lay.paste(LOGO_IMG, (lx, ly), LOGO_IMG)
    return composite(img, lay)

# ── PROGRESS PIPS (s1–s4) ─────────────────────────────────────────
PIP_N    = 4
PIP_R    = sc(5)
PIP_PILL = sc(14)
PIP_PH   = sc(5)
PIP_GAP  = sc(14)

def draw_pips(img, si, lt):
    if si < 1 or si > 4: return img
    active = si - 1
    pill_a = spring(min(1.0, lt / 0.4))
    pill_w = int(lerp(PIP_R, PIP_PILL, pill_a))
    total_w = (PIP_N - 1) * (PIP_R * 2 + PIP_GAP) + pill_w * 2
    sx = (W - total_w) // 2
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    cur_x = sx
    for i in range(PIP_N):
        if i == active:
            d.rounded_rectangle([cur_x, PIP_CY - PIP_PH,
                                  cur_x + pill_w * 2, PIP_CY + PIP_PH],
                                 radius=PIP_PH, fill=(255, 255, 255, 230))
            cur_x += pill_w * 2 + PIP_GAP
        else:
            cx_ = cur_x + PIP_R
            alpha = 90 if i < active else 50
            d.ellipse([cx_ - PIP_R, PIP_CY - PIP_R, cx_ + PIP_R, PIP_CY + PIP_R],
                      fill=(255, 255, 255, alpha))
            cur_x += PIP_R * 2 + PIP_GAP
    return composite(img, layer)

# ── URL ───────────────────────────────────────────────────────────
def draw_url(img):
    txt = "blastudios.vercel.app"
    lay = new_layer()
    d   = ImageDraw.Draw(lay)
    d.text((cxf(d, txt, F_SM), URL_Y), txt, font=F_SM, fill=(*GRAY, 180))
    return composite(img, lay)

# ── KARAOKE ───────────────────────────────────────────────────────
def render_karaoke(img, sentences, t_ms):
    if not sentences: return img
    act_idx = -1
    for i, s in enumerate(sentences):
        if s['start_ms'] <= t_ms < s['start_ms'] + s['dur_ms'] + 600:
            act_idx = i; break
    if act_idx == -1:
        for i in range(len(sentences) - 1, -1, -1):
            if sentences[i]['start_ms'] <= t_ms:
                act_idx = i; break
    if act_idx == -1: return img

    words = sentences[act_idx]['words']
    d_dummy = ImageDraw.Draw(img)
    max_kara_w = W - sc(80)
    lines = []
    cur_line = []; cur_w = 0
    for wobj in words:
        ww = tw(d_dummy, wobj['word'] + ' ', F_KN)
        if cur_w + ww > max_kara_w and cur_line:
            lines.append(cur_line); cur_line = [wobj]; cur_w = ww
        else:
            cur_line.append(wobj); cur_w += ww
    if cur_line: lines.append(cur_line)

    # Find which line has the active word
    cur_line_idx = 0
    for li, ln in enumerate(lines):
        for wobj in ln:
            if wobj['start_ms'] <= t_ms < wobj['start_ms'] + wobj['duration_ms']:
                cur_line_idx = li

    start_line = max(0, cur_line_idx - 1)
    visible    = lines[start_line:start_line + 2]

    line_h     = sc(30)
    total_h    = len(visible) * line_h
    y0         = KARA_T + (KARA_H - total_h) // 2

    img = glass_rect(img, sc(16), KARA_T - sc(8), W - sc(16), KARA_B + sc(8),
                     radius=sc(24), blur=16,
                     fill=(0, 0, 0, 90), border=(255, 255, 255, 28))

    lay = new_layer()
    d2  = ImageDraw.Draw(lay)

    for li, ln in enumerate(visible):
        ly = y0 + li * line_h
        full_w = sum(tw(d2, w['word'] + ' ', F_KN) for w in ln)
        lx = (W - full_w) // 2
        for wobj in ln:
            w_end = wobj['start_ms'] + wobj['duration_ms']
            if wobj['start_ms'] <= t_ms < w_end:
                f_ = F_KH; col = (255, 255, 255, 255)
            elif t_ms >= w_end:
                f_ = F_KP; col = (*LGRAY, 160)
            else:
                f_ = F_KN; col = (200, 205, 220, 200)
            d2.text((lx, ly), wobj['word'], font=f_, fill=col)
            lx += tw(d2, wobj['word'] + ' ', F_KN)

    return composite(img, lay)

# ══════════════════════════════════════════════════════════════════
# ESCENAS
# ══════════════════════════════════════════════════════════════════

def s0(img, lt):
    """Hook: tu negocio trabaja para ti"""
    d  = ImageDraw.Draw(img)
    Y0 = CY - sc(63)

    ma  = spring(fade(0.08, 0.45, lt))
    yo  = int(lerp(sc(16), 0, spring(fade(0.08, 0.45, lt))))

    for i, line in enumerate(["¿Tu negocio", "trabaja para ti..."]):
        lx = cxf(d, line, F_H2)
        ly = Y0 + i * sc(46) + yo
        img = gtxt(img, (lx, ly), line, F_H2, WHITE, BLUE, sc(11), ma)
        d = ImageDraw.Draw(img)

    full  = "...¿o tú para él?"
    spd   = len(full) / 1.1
    nc    = int(min((lt - 0.65) * spd, len(full))) if lt > 0.65 else 0
    typed = full[:nc]
    if typed:
        ta  = spring(fade(0.65, 0.18, lt))
        fw  = tw(d, full, F_H3)
        lx2 = (W - fw) // 2
        img = gtxt(img, (lx2, Y0 + sc(114) + yo), typed, F_H3, BLUE, BLUE, sc(9), ta)
        d = ImageDraw.Draw(img)
    if lt > 0.65 and nc < len(full) and (lt * 1.8) % 1 < 0.55:
        fw   = tw(d, full, F_H3)
        typw = tw(d, typed, F_H3) if typed else 0
        cx2  = (W - fw) // 2 + typw + sc(3)
        d.rectangle([cx2, Y0 + sc(116) + yo, cx2 + sc(2), Y0 + sc(136) + yo], fill=BLUE)
    return img


def s1(img, lt):
    """Diseño web que convierte"""
    accent = SCENE_ACCENT[1]
    BRY = CY - sc(158)
    CRY = BRY + sc(162 + 18)
    CRH = sc(136)

    # Browser mock — spring slide-in
    br_a = spring(fade(0.05, 0.38, lt))
    br_y = BRY + int(lerp(sc(18), 0, spring(fade(0.05, 0.38, lt))))
    if br_a > 0:
        img = glass_rect(img, PAD, br_y, PAD + BW, br_y + sc(162),
                         radius=sc(14), blur=12,
                         fill=(*DBLU, int(0.50 * br_a * 255)),
                         border=(*accent, int(0.22 * br_a * 255)))
        d = ImageDraw.Draw(img)
        d.rectangle([PAD, br_y, PAD + BW, br_y + sc(26)], fill=ac((18, 38, 90), br_a))
        for i, dc in enumerate([(220, 80, 70), (220, 170, 50), (50, 190, 80)]):
            dx = PAD + sc(12) + i * sc(14)
            d.ellipse([dx - sc(4), br_y + sc(9), dx + sc(4), br_y + sc(17)], fill=ac(dc, br_a))
        d.rounded_rectangle([PAD + sc(52), br_y + sc(5), PAD + BW - sc(8), br_y + sc(21)],
                             radius=sc(4), fill=ac((30, 35, 58), br_a))
        d.text((PAD + sc(58), br_y + sc(7)), "blastudios.vercel.app",
               font=F_SM, fill=ac((155, 160, 178), br_a))
        hy = br_y + sc(32)
        d.rounded_rectangle([PAD + sc(8), hy, PAD + BW - sc(8), hy + sc(52)],
                             radius=sc(8), fill=ac((22, 50, 118), br_a))
        htxt = "TU MARCA  ·  ONLINE  ·  AHORA"
        d.text((cxf(d, htxt, F_TAG, PAD + sc(8), BW - sc(16)), hy + sc(19)),
               htxt, font=F_TAG, fill=ac((172, 178, 198), br_a))
        shim = (lt * 0.45) % 1.0
        ry2  = hy + sc(60)
        for rw3 in [BW - sc(38), BW - sc(62), BW - sc(98)]:
            d.rounded_rectangle([PAD + sc(8), ry2, PAD + sc(8) + rw3, ry2 + sc(7)],
                                 radius=sc(3), fill=ac((46, 52, 72), br_a * 0.17))
            sx  = PAD + sc(8) + int((rw3 + sc(55)) * shim) - sc(28)
            sx1 = max(PAD + sc(8), sx)
            sx2 = min(PAD + sc(8) + rw3, sx + sc(32))
            if sx2 > sx1:
                d.rounded_rectangle([sx1, ry2, sx2, ry2 + sc(7)],
                                     radius=sc(3), fill=ac((65, 95, 190), br_a * 0.6))
            ry2 += sc(14)

    # Tarjeta de texto — spring desde abajo
    cry_off = int(lerp(sc(14), 0, spring(fade(0.18, 0.36, lt))))
    img = glass_rect(img, PAD, CRY + cry_off, PAD + BW, CRY + CRH + cry_off,
                     radius=sc(18), blur=12,
                     fill=(*DBLU, 70), border=(*accent, 70))
    d = ImageDraw.Draw(img)

    ta = spring(fade(0.17, 0.26, lt))
    if ta > 0:
        d.text((PAD + sc(20), CRY + sc(15) + cry_off), "DISEÑO WEB",
               font=F_TAG, fill=ac(accent, ta))
    ha = spring(fade(0.27, 0.28, lt))
    hy2 = CRY + sc(36) + cry_off + int(lerp(sc(10), 0, spring(fade(0.27, 0.28, lt))))
    if ha > 0:
        t1w = tw(d, "WEB QUE ", F_H3)
        d.text((PAD + sc(20), hy2), "WEB QUE ", font=F_H3, fill=ac(WHITE, ha))
        d.text((PAD + sc(20) + t1w, hy2), "CONVIERTE", font=F_H3, fill=ac(accent, ha))
    sa = spring(fade(0.37, 0.28, lt))
    if sa > 0:
        for i, ln in enumerate(wraptext(d, "Diseñamos experiencias que transforman visitas en clientes reales.", F_SM, BW - sc(40))):
            d.text((PAD + sc(20), CRY + sc(66) + cry_off + i * sc(17)), ln,
                   font=F_SM, fill=ac(LGRAY, sa))
    return img


def s2(img, lt):
    """Campanas digitales con métricas"""
    accent = SCENE_ACCENT[2]
    CRY = CY - sc(149)
    CRH = sc(210)
    CTY = CRY + CRH + sc(14)
    CTH = sc(74)
    CTY = min(CTY, KARA_T - CTH - sc(10))

    card_off = int(lerp(sc(16), 0, spring(fade(0.04, 0.38, lt))))
    img = glass_rect(img, PAD, CRY + card_off, PAD + BW, CRY + CRH + card_off,
                     radius=sc(18), blur=12,
                     fill=(*DBLU, 70), border=(*accent, 70))
    d = ImageDraw.Draw(img)

    ta = spring(fade(0.05, 0.26, lt))
    if ta > 0:
        d.text((PAD + sc(20), CRY + sc(14) + card_off), "CAMPANAS DIGITALES",
               font=F_TAG, fill=ac(accent, ta))

    # Contador animado
    ca = spring(fade(0.09, 0.33, lt))
    cv = int(min((lt - 0.09) / 1.05 * 247, 247)) if lt > 0.09 else 0
    if ca > 0:
        ns  = str(cv)
        ny  = CRY + sc(40) + card_off + int(lerp(sc(14), 0, spring(fade(0.09, 0.33, lt))))
        gl  = new_layer()
        gd  = ImageDraw.Draw(gl)
        gd.text((PAD + sc(20), ny), ns, font=F_NUM, fill=(*accent, int(ca * 75)))
        gl  = gl.filter(ImageFilter.GaussianBlur(sc(13)))
        img = Image.alpha_composite(img.convert('RGBA'), gl).convert('RGB')
        d   = ImageDraw.Draw(img)
        d.text((PAD + sc(20), ny), ns, font=F_NUM, fill=ac(accent, ca))
        d.text((PAD + sc(22) + tw(d, ns, F_NUM), ny + sc(24)), "%",
               font=F_H2, fill=ac(WHITE, ca))

    ha  = spring(fade(0.18, 0.28, lt))
    hy3 = CRY + sc(136) + card_off + int(lerp(sc(10), 0, spring(fade(0.18, 0.28, lt))))
    if ha > 0:
        t1w = tw(d, "RESULTADOS ", F_H3)
        d.text((PAD + sc(20), hy3), "RESULTADOS ", font=F_H3, fill=ac(WHITE, ha))
        d.text((PAD + sc(20) + t1w, hy3), "MEDIBLES", font=F_H3, fill=ac(accent, ha))

    sa = spring(fade(0.28, 0.26, lt))
    if sa > 0:
        for i, ln in enumerate(wraptext(d, "Campanas basadas en datos — sin malgastar tu presupuesto.", F_SM, BW - sc(40))):
            d.text((PAD + sc(20), CRY + sc(163) + card_off + i * sc(17)), ln,
                   font=F_SM, fill=ac(LGRAY, sa))

    # Barras de chart con spring crecimiento
    cha  = spring(fade(0.14, 0.48, lt))
    grow = spring(fade(0.14, 0.52, lt))
    if cha > 0 and CTY + CTH < KARA_T:
        bw4 = (BW - sc(8) * 4) // 5
        for bi, bv in enumerate([0.28, 0.44, 0.60, 0.76, 1.0]):
            bx2 = PAD + bi * (bw4 + sc(8))
            bh4 = int(CTH * bv * grow)
            by4 = CTY + CTH - bh4
            if bh4 <= 0: continue
            if bi == 4:
                col = ac(accent, cha)
                d.rounded_rectangle([bx2, by4, bx2 + bw4, CTY + CTH], radius=sc(5), fill=col)
                gl2 = new_layer()
                ImageDraw.Draw(gl2).rounded_rectangle(
                    [bx2 - sc(4), by4 - sc(4), bx2 + bw4 + sc(4), CTY + CTH + sc(4)],
                    radius=sc(7), fill=(*accent, int(cha * 65)))
                gl2 = gl2.filter(ImageFilter.GaussianBlur(sc(6)))
                img = Image.alpha_composite(img.convert('RGBA'), gl2).convert('RGB')
                d   = ImageDraw.Draw(img)
                d.rounded_rectangle([bx2, by4, bx2 + bw4, CTY + CTH], radius=sc(5), fill=col)
            else:
                d.rounded_rectangle([bx2, by4, bx2 + bw4, CTY + CTH],
                                     radius=sc(5), fill=ac(accent, cha * 0.17))
    return img


def s3(img, lt):
    """IA 24/7 — chat burbujas + card"""
    accent = SCENE_ACCENT[3]
    Y3 = CY - sc(158)

    d = ImageDraw.Draw(img)

    # Badge 24/7 — spring desde arriba
    ba2 = spring(fade(0.05, 0.38, lt))
    by2 = Y3 + int(lerp(-sc(8), 0, spring(fade(0.05, 0.38, lt))))
    if ba2 > 0:
        btxt  = "  24/7 ACTIVO"
        btw3  = tw(d, btxt, F_H3) + sc(40)
        bx3   = (W - btw3) // 2
        surf  = Image.new('RGBA', (btw3, sc(38)), (0, 0, 0, 0))
        sd    = ImageDraw.Draw(surf)
        sd.rounded_rectangle([0, 0, btw3 - 1, sc(38) - 1], radius=sc(19),
                              fill=(*DBLU, int(ba2 * 112)),
                              outline=(*accent, int(ba2 * 130)), width=2)
        sd.text((sc(20), sc(9)), btxt, font=F_H3, fill=(*WHITE, int(ba2 * 218)))
        base = img.convert('RGBA')
        base.paste(surf, (bx3, by2), surf)
        img = base.convert('RGB')
        d = ImageDraw.Draw(img)

    # Burbujas de chat — spring stagger
    cy2 = Y3 + sc(50)
    for bst, btxt2, is_u in [
        (0.18, "Hola, quiero información\nsobre vuestros servicios", True),
        (0.54, "Soy el asistente de Blastudios.\nTe cuento todo ahora mismo", False),
    ]:
        ba3 = spring(fade(bst, 0.32, lt))
        if ba3 <= 0:
            cy2 += sc(72); continue
        blines = btxt2.split('\n')
        mlw    = max(tw(d, ln, F_BD) for ln in blines)
        bw5    = min(mlw + sc(28), int(W * 0.76))
        bh5    = len(blines) * sc(20) + sc(18)
        bx4    = W - PAD - bw5 if is_u else PAD
        ysl    = int(lerp(sc(10), 0, spring(fade(bst, 0.32, lt))))
        fc     = (*accent, int(ba3 * 60)) if is_u else (*DBLU, int(ba3 * 162))
        oc     = (*accent, int(ba3 * 100)) if is_u else (*accent, int(ba3 * 65))
        surf   = Image.new('RGBA', (bw5, bh5), (0, 0, 0, 0))
        sd     = ImageDraw.Draw(surf)
        sd.rounded_rectangle([0, 0, bw5 - 1, bh5 - 1], radius=sc(14), fill=fc, outline=oc, width=2)
        for li, ln in enumerate(blines):
            sd.text((sc(14), sc(9) + li * sc(20)), ln, font=F_BD, fill=(*WHITE, int(ba3 * 215)))
        base = img.convert('RGBA')
        base.paste(surf, (bx4, cy2 + ysl), surf)
        img = base.convert('RGB')
        d = ImageDraw.Draw(img)
        cy2 += bh5 + sc(10)

    # Status pulsante verde
    sta = spring(fade(0.88, 0.28, lt))
    if sta > 0:
        blink = 1.0 if (lt * 2) % 1 < 0.55 else 0.38
        d.ellipse([PAD, cy2 + sc(5), PAD + sc(8), cy2 + sc(13)],
                  fill=ac(GREEN, sta * blink))
        d.text((PAD + sc(14), cy2 + sc(2)), "IA respondiendo en segundos",
               font=F_SM, fill=ac(GREEN, sta))
        cy2 += sc(26)

    # Card de texto (si cabe antes del karaoke)
    cy3 = cy2 + sc(10)
    ch3 = sc(118)
    if cy3 + ch3 < KARA_T - sc(12):
        c_off = int(lerp(sc(14), 0, spring(fade(0.28, 0.36, lt))))
        img = glass_rect(img, PAD, cy3 + c_off, PAD + BW, cy3 + ch3 + c_off,
                         radius=sc(18), blur=12,
                         fill=(*DBLU, 70), border=(*accent, 70))
        d = ImageDraw.Draw(img)
        ta2 = spring(fade(0.30, 0.26, lt))
        if ta2 > 0:
            d.text((PAD + sc(20), cy3 + sc(14) + c_off), "AUTOMATIZACION CON IA",
                   font=F_TAG, fill=ac(accent, ta2))
        ha2 = spring(fade(0.40, 0.28, lt))
        hy4 = cy3 + sc(36) + c_off + int(lerp(sc(10), 0, spring(fade(0.40, 0.28, lt))))
        if ha2 > 0:
            t1w = tw(d, "TU NEGOCIO ", F_H3)
            d.text((PAD + sc(20), hy4), "TU NEGOCIO ", font=F_H3, fill=ac(WHITE, ha2))
            d.text((PAD + sc(20) + t1w, hy4), "NUNCA PARA", font=F_H3, fill=ac(accent, ha2))
        sa2 = spring(fade(0.50, 0.28, lt))
        if sa2 > 0:
            for i, ln in enumerate(wraptext(d, "Sistemas autonomos que atienden, venden y fidelizan.", F_SM, BW - sc(40))):
                d.text((PAD + sc(20), cy3 + sc(64) + c_off + i * sc(17)), ln,
                       font=F_SM, fill=ac(LGRAY, sa2))
    return img


def s4(img, lt):
    """Marca — No es suerte. Es sistema."""
    accent = SCENE_ACCENT[4]
    CARD_H = sc(88) if not LOGO_IMG else int(LOGO_IMG.size[1] * ((BW - sc(36)) / LOGO_IMG.size[0])) + sc(36)
    CARD_W = BW
    CARD_X = PAD
    TOTAL  = CARD_H + sc(22) + sc(72)
    CARD_Y0 = CY - TOTAL // 2

    la  = spring(fade(0.07, 0.50, lt))
    lsc = lerp(0.88, 1.0, spring(fade(0.07, 0.50, lt)))
    lyo = int(lerp(sc(16), 0, spring(fade(0.07, 0.50, lt))))
    d   = ImageDraw.Draw(img)

    if la > 0:
        pulse = 0.5 + 0.5 * math.sin(lt * 2.1)
        gs    = (0.38 + 0.16 * pulse) * la
        cx3   = CARD_X + CARD_W // 2
        cy3   = CARD_Y0 + lyo + CARD_H // 2
        for gr3 in [sc(52), sc(28)]:
            gl3 = new_layer()
            ImageDraw.Draw(gl3).rounded_rectangle(
                [cx3 - CARD_W // 2 - gr3, cy3 - CARD_H // 2 - gr3,
                 cx3 + CARD_W // 2 + gr3, cy3 + CARD_H // 2 + gr3],
                radius=sc(22) + gr3 // 2, fill=(*accent, int(gs * 22)))
            gl3 = gl3.filter(ImageFilter.GaussianBlur(gr3 // 2 + sc(8)))
            img = Image.alpha_composite(img.convert('RGBA'), gl3).convert('RGB')
            d   = ImageDraw.Draw(img)

        CARD_Y = CARD_Y0 + lyo
        card   = Image.new('RGBA', (CARD_W, CARD_H), (0, 0, 0, 0))
        cd     = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, CARD_W - 1, CARD_H - 1], radius=sc(20),
                              fill=(255, 255, 255, int(la * 252)),
                              outline=(*accent, int(la * 80)), width=sc(2))

        if LOGO_IMG:
            logo_card_w = CARD_W - sc(36)
            logo_card_h = int(LOGO_IMG.size[1] * logo_card_w / LOGO_IMG.size[0])
            if logo_card_h > CARD_H - sc(24):
                logo_card_h = CARD_H - sc(24)
                logo_card_w = int(LOGO_IMG.size[0] * logo_card_h / LOGO_IMG.size[1])
            if lsc < 0.995:
                sw = max(1, int(logo_card_w * lsc))
                sh = max(1, int(logo_card_h * lsc))
                logo_use = LOGO_IMG.resize((sw, sh), Image.LANCZOS)
            else:
                logo_use = LOGO_IMG.resize((logo_card_w, logo_card_h), Image.LANCZOS)
                sw, sh = logo_card_w, logo_card_h
            lx_off = (CARD_W - sw) // 2
            ly_off = (CARD_H - sh) // 2
            card.paste(logo_use, (lx_off, ly_off), logo_use)

        base = img.convert('RGBA')
        base.paste(card, (CARD_X, CARD_Y), card)
        img  = base.convert('RGB')
        d    = ImageDraw.Draw(img)

    tla = spring(fade(0.55, 0.42, lt))
    if tla > 0:
        tly = CARD_Y0 + CARD_H + sc(26) + lyo
        for i, line in enumerate(['"No es suerte.', 'Es sistema."']):
            ltw2 = tw(d, line, F_H3)
            lx3  = (W - ltw2) // 2
            img  = gtxt(img, (lx3, tly + i * sc(36)), line, F_H3, WHITE, accent, sc(9), tla)
            d    = ImageDraw.Draw(img)
    return img


def s5(img, lt):
    """CTA"""
    accent = SCENE_ACCENT[5]
    Y5 = CY - sc(99)
    d  = ImageDraw.Draw(img)

    lbl = "EMPIEZA HOY"
    la  = spring(fade(0.0, 0.28, lt))
    if la > 0:
        d.text((cxf(d, lbl, F_TAG), Y5), lbl, font=F_TAG, fill=ac(accent, la))

    ta3 = spring(fade(0.07, 0.36, lt))
    tyo = int(lerp(sc(14), 0, spring(fade(0.07, 0.36, lt))))
    if ta3 > 0:
        for i, line in enumerate(["¿Listo para que tu negocio", "crezca con IA?"]):
            ltw3 = tw(d, line, F_H3)
            d.text(((W - ltw3) // 2, Y5 + sc(36) + i * sc(34) + tyo), line,
                   font=F_H3, fill=ac(WHITE, ta3))

    # Boton pulsante con spring
    ba4 = spring(fade(0.22, 0.38, lt))
    BTY = Y5 + sc(132)
    if ba4 > 0:
        btxt2 = "  Escribenos ahora"
        btw4  = tw(d, btxt2, F_BD) + sc(52)
        bh6   = sc(50)
        bx5   = (W - btw4) // 2
        pulse = 0.5 + 0.5 * math.sin(lt * 3.1)
        gr4   = int((sc(14) + sc(10) * pulse) * ba4)
        gl4   = new_layer()
        ImageDraw.Draw(gl4).rounded_rectangle(
            [bx5 - gr4 // 2, BTY - gr4 // 4,
             bx5 + btw4 + gr4 // 2, BTY + bh6 + gr4 // 4],
            radius=bh6 // 2 + gr4 // 4,
            fill=(*accent, int(ba4 * 48)))
        gl4  = gl4.filter(ImageFilter.GaussianBlur(gr4 // 2 + sc(4)))
        img  = Image.alpha_composite(img.convert('RGBA'), gl4).convert('RGB')
        d    = ImageDraw.Draw(img)
        d.rounded_rectangle([bx5, BTY, bx5 + btw4, BTY + bh6],
                             radius=bh6 // 2, fill=ac(accent, ba4))
        itw3 = tw(d, btxt2, F_BD)
        d.text(((W - itw3) // 2, BTY + sc(16)), btxt2, font=F_BD, fill=ac(WHITE, ba4))

    ha3 = spring(fade(0.40, 0.35, lt))
    if ha3 > 0:
        htxt = "@blastudios  ·  blastudios.vercel.app"
        d.text((cxf(d, htxt, F_SM), BTY + sc(66)), htxt,
               font=F_SM, fill=ac(LGRAY, ha3))
    return img

# ── TIMELINE ─────────────────────────────────────────────────────
TIMES  = [(0, 4), (4, 10), (10, 17), (17, 23), (23, 28), (28, 32)]
SCENES = [s0, s1, s2, s3, s4, s5]
XFADE  = 0.48

def get_scene(t):
    for i, (s, e) in enumerate(TIMES):
        if s <= t < e: return i, t - s
    return 5, max(0., t - TIMES[5][0])

# ── AUDIO TTS ────────────────────────────────────────────────────
async def generate_audio():
    communicate   = edge_tts.Communicate(SCRIPT, voice=VOICE, rate="-5%")
    raw_sents     = []
    audio_chunks  = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "SentenceBoundary":
            raw_sents.append({
                "text":     chunk["text"],
                "start_ms": chunk["offset"]   / 10000,
                "dur_ms":   chunk["duration"] / 10000,
            })
    with open(TMP_A, 'wb') as f:
        for ch in audio_chunks: f.write(ch)

    sentences = []
    for sent in raw_sents:
        raw_words = sent["text"].split()
        total_ch  = sum(max(1, len(w.strip("¿?.,;:!\"'()"))) for w in raw_words)
        cursor    = sent["start_ms"] + 20
        eff       = max(0, sent["dur_ms"] - 40)
        words_out = []
        for w in raw_words:
            cl = w.strip("¿?.,;:!\"'()"); ch = max(1, len(cl))
            wd = eff * ch / total_ch
            words_out.append({"word": w, "start_ms": cursor, "duration_ms": wd})
            cursor += wd
        sentences.append({
            "text":     sent["text"],
            "start_ms": sent["start_ms"],
            "dur_ms":   sent["dur_ms"],
            "words":    words_out,
        })
    return sentences

# ── RENDER ────────────────────────────────────────────────────────
def render_frame(fi, sentences):
    t  = fi / FPS
    si, lt = get_scene(t)
    s_start, s_end = TIMES[si]
    t_ms = t * 1000

    base = Image.new('RGB', (W, H), BG)
    base = draw_bg(base, si, t)

    if t - s_start < XFADE:
        fa = eio((t - s_start) / XFADE)
    elif s_end - t < XFADE and si < len(SCENES) - 1:
        fa = eio((s_end - t) / XFADE)
    else:
        fa = 1.0

    curr = SCENES[si](base.copy(), lt)

    if fa >= 0.995:
        result = curr
    elif t - s_start < XFADE and si > 0:
        prev_si = si - 1
        prev_lt = TIMES[prev_si][1] - TIMES[prev_si][0] - 0.001
        prev    = SCENES[prev_si](base.copy(), prev_lt)
        result  = Image.blend(prev, curr, eio((t - s_start) / XFADE))
    else:
        result = Image.blend(base, curr, fa)

    result = render_karaoke(result, sentences, t_ms)
    result = draw_pips(result, si, lt)
    result = draw_header(result, si)
    result = draw_url(result)
    return result

# ── MAIN ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("Generando audio TTS...")
    sentences = asyncio.run(generate_audio())
    print(f"  {len(sentences)} frases  |  audio: {TMP_A}")

    print(f"\nRenderizando {W}x{H} @ {FPS}fps  {DUR}s = {FRAMES} frames")
    writer = imageio.get_writer(
        TMP_V, fps=FPS, codec='libx264', quality=None, bitrate='20M',
        output_params=['-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p']
    )
    t0 = time.time()
    for fi in range(FRAMES):
        if fi % FPS == 0:
            elapsed = time.time() - t0
            eta = elapsed / max(fi, 1) * (FRAMES - fi)
            print(f"  {fi // FPS:2d}s / {DUR}s  ({elapsed:.0f}s transcurridos, ETA {eta:.0f}s)")
        writer.append_data(np.array(render_frame(fi, sentences)))
    writer.close()
    print(f"  Video mudo listo en {time.time() - t0:.1f}s")

    print("\nCombinando audio + video...")
    if os.path.exists(OUT): os.remove(OUT)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ffmpeg_exe, '-y',
        '-i', TMP_V, '-i', TMP_A,
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-shortest', OUT
    ], check=True)
    for f in [TMP_V, TMP_A]:
        try: os.remove(f)
        except: pass

    mb = os.path.getsize(OUT) / 1_048_576
    total = time.time() - t0
    print(f"\nListo: {OUT}")
    print(f"  Tamano: {mb:.1f} MB  |  {DUR}s  |  {W}x{H} @ {FPS}fps")
    print(f"  Tiempo total: {total:.0f}s")
