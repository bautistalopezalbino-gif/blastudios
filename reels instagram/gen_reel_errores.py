#!/usr/bin/env python3
"""Generador de Reel Blastudios – Errores de Negocio – 30s MP4 1080×1920
   Visual Storyteller methodology: Hook → 4 Errores+Solución → Logo/CTA
"""
import os, math, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

# ── CONFIG ────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
DUR    = 30
FRAMES = FPS * DUR
OUT    = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram\reel_blastudios_errores.mp4"
FD     = r"C:\Windows\Fonts"
CY     = H // 2          # 960
SCALE  = W / 390         # 2.7692 — factor respecto al layout base 390px

def sc(v):
    """Escala un valor de píxeles del layout 390px al ancho actual."""
    return int(round(v * SCALE))

# ── COLORES ───────────────────────────────────────────────────────
BG    = (19,  19,  22)
BLUE  = (37,  99,  235)
DBLU  = (13,  27,  62)
WHITE = (248, 250, 252)
LGRAY = (185, 188, 200)
RED   = (220,  50,  47)
DRED  = (48,   8,   8)

# ── FUENTES ───────────────────────────────────────────────────────
def fnt(name, sz):
    p = os.path.join(FD, name)
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()

FB = lambda s: fnt('segoeuib.ttf', s)
FR = lambda s: fnt('segoeui.ttf',  s)
FL = lambda s: fnt('segoeuil.ttf', s)

# ── ASSETS: logo desde coordenadas SVG ────────────────────────────
def _make_logo_img(target_w):
    SVG_W, SVG_H = 520.0, 110.0
    s  = target_w / SVG_W
    th = max(1, int(SVG_H * s))
    R  = 3.0
    fsc = s * R
    rw  = max(1, int(SVG_W * fsc))
    rh  = max(1, int(SVG_H * fsc))
    surf = Image.new('RGBA', (rw, rh), (0, 0, 0, 0))
    d    = ImageDraw.Draw(surf)
    DNAV  = (13, 31, 60)
    WITE  = (255, 255, 255)
    BBLUE = (37, 99, 235)
    d.rounded_rectangle([5*fsc, 5*fsc, 105*fsc, 105*fsc], radius=max(1, int(20*fsc)), fill=DNAV)
    d.rounded_rectangle([30*fsc, 17*fsc, 42*fsc, 93*fsc],  radius=max(1, int(6*fsc)),  fill=WITE)
    cx_, cy_ = 61*fsc, 76*fsc
    d.ellipse([cx_-19*fsc, cy_-19*fsc, cx_+19*fsc, cy_+19*fsc], fill=WITE)
    d.ellipse([cx_-10*fsc, cy_-10*fsc, cx_+10*fsc, cy_+10*fsc], fill=DNAV)
    mfpt = max(10, int(58*fsc))
    fb3 = FB(mfpt); fl3 = FL(mfpt)
    bla_bb = d.textbbox((0,0), "bla", font=fb3)
    bla_w  = bla_bb[2]-bla_bb[0]
    tx_ = int(125*fsc); by_ = int(78*fsc)
    d.text((tx_,       by_), "bla",     font=fb3, fill=DNAV,  anchor="ls")
    d.text((tx_+bla_w, by_), "studios", font=fl3, fill=DNAV,  anchor="ls")
    tfpt = max(6, int(13*fsc))
    d.text((int(127*fsc), int(100*fsc)), "DIGITAL MARKETING AGENCY",
           font=FB(tfpt), fill=BBLUE, anchor="ls")
    return surf.resize((target_w, th), Image.LANCZOS)

LOGO_FULL = _make_logo_img(sc(280))
LOGO_W, LOGO_H = LOGO_FULL.size

# Fuentes escaladas al nuevo ancho
F_H2  = FB(sc(26))   # titular grande
F_H3  = FB(sc(21))   # titular medio
F_H4  = FB(sc(18))   # titular pequeño (cards)
F_BD  = FR(sc(14))   # cuerpo
F_SM  = FR(sc(12))   # cuerpo pequeño
F_TAG = FB(sc(11))   # label uppercase

# ── MATH ──────────────────────────────────────────────────────────
def eo(t):       return 1-(1-_c(t))**3
def eio(t):      t=_c(t); return t*t*(3-2*t)
def _c(v):       return max(0., min(1., v))
def lerp(a,b,t): return a+(b-a)*t
def fade(s,d,t): return _c((t-s)/d) if d>0 else (1. if t>=s else 0.)

# ── HELPERS ───────────────────────────────────────────────────────
def tw(d, txt, f):
    b = d.textbbox((0,0), txt, font=f); return b[2]-b[0]

def cx(d, txt, f, ox=0, ow=W):
    return ox + (ow - tw(d, txt, f)) // 2

def wrap(d, txt, f, maxw):
    words = txt.split(); lines, cur = [], ""
    for w in words:
        test = (cur+" "+w).strip()
        if tw(d, test, f) <= maxw: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def ac(col, a):
    return tuple(int(c*a) for c in col)

def otxt(img, pos, txt, font, col, a=1.0):
    if a <= 0.01: return img
    lay = Image.new('RGBA', img.size, (0,0,0,0))
    ImageDraw.Draw(lay).text(pos, txt, font=font, fill=(*col, int(a*255)))
    return Image.alpha_composite(img.convert('RGBA'), lay).convert('RGB')

def gtxt(img, pos, txt, font, col, gcol, gr=10, a=1.0):
    if a <= 0.01: return img
    gl = Image.new('RGBA', img.size, (0,0,0,0))
    ImageDraw.Draw(gl).text(pos, txt, font=font, fill=(*gcol, int(a*85)))
    gl = gl.filter(ImageFilter.GaussianBlur(gr))
    base = Image.alpha_composite(img.convert('RGBA'), gl)
    return otxt(base.convert('RGB'), pos, txt, font, col, a)

def glass_card(img, x, y, w, h, r=16, ba=0.42, oa=0.22, fc=None, oc=None):
    if fc is None: fc = DBLU
    if oc is None: oc = BLUE
    surf = Image.new('RGBA', (w, h), (0,0,0,0))
    d2   = ImageDraw.Draw(surf)
    d2.rounded_rectangle([0,0,w-1,h-1], radius=r,
                          fill=(*fc, int(ba*255)),
                          outline=(*oc, int(oa*255)), width=2)
    base = img.convert('RGBA')
    base.paste(surf, (x, y), surf)
    return base.convert('RGB')

def orb(img, x, y, rad, col, s=0.28):
    sz  = rad*2
    o   = Image.new('RGBA', (sz,sz), (0,0,0,0))
    od  = ImageDraw.Draw(o)
    for r in range(rad, 0, max(1, rad//22)):
        a = int(s*255*((1-r/rad)**0.55))
        od.ellipse([rad-r,rad-r,rad+r,rad+r], fill=(*col, a))
    o    = o.filter(ImageFilter.GaussianBlur(rad//4))
    base = img.convert('RGBA')
    px, py = x-rad, y-rad
    ox2,oy2,ow2,oh2 = 0,0,sz,sz
    if px<0:  ox2=-px; ow2=sz+px; px=0
    if py<0:  oy2=-py; oh2=sz+py; py=0
    if px+ow2>W: ow2=W-px
    if py+oh2>H: oh2=H-py
    if ow2>0 and oh2>0:
        crop = o.crop([ox2,oy2,ox2+ow2,oy2+oh2])
        base.paste(crop, (px,py), crop)
    return base.convert('RGB')

# ── ICONOS pre-renderizados ───────────────────────────────────────
ICON_S = sc(36)

def _mk_x_icon():
    s    = ICON_S
    surf = Image.new('RGBA', (s,s), (0,0,0,0))
    d    = ImageDraw.Draw(surf)
    d.ellipse([1,1,s-2,s-2], fill=(*RED, 215), outline=(*RED, 255), width=max(2, s//18))
    p  = s//4; lw = max(2, s//7)
    d.line([(p,p),(s-p,s-p)], fill=(255,255,255,228), width=lw)
    d.line([(s-p,p),(p,s-p)], fill=(255,255,255,228), width=lw)
    return surf

def _mk_chk_icon():
    s    = ICON_S
    surf = Image.new('RGBA', (s,s), (0,0,0,0))
    d    = ImageDraw.Draw(surf)
    d.ellipse([1,1,s-2,s-2], fill=(*BLUE, 215), outline=(*BLUE, 255), width=max(2, s//18))
    lw = max(2, s//7)
    p1 = (int(s*0.24), int(s*0.52))
    p2 = (int(s*0.44), int(s*0.70))
    p3 = (int(s*0.76), int(s*0.32))
    d.line([p1,p2], fill=(255,255,255,228), width=lw)
    d.line([p2,p3], fill=(255,255,255,228), width=lw)
    return surf

X_ICON  = _mk_x_icon()
CHK_ICO = _mk_chk_icon()

def paste_icon(img, icon, icx, icy, a):
    if a <= 0.01: return img
    ico = icon.copy()
    if a < 0.99:
        r,g,b,al = ico.split()
        al  = al.point(lambda x: int(x*a))
        ico = Image.merge('RGBA', (r,g,b,al))
    base = img.convert('RGBA')
    base.paste(ico, (icx - ICON_S//2, icy - ICON_S//2), ico)
    return base.convert('RGB')

# ── FONDO ─────────────────────────────────────────────────────────
def mk_bg(t):
    img = Image.new('RGB', (W,H), BG)
    p1  = math.sin(t*0.65)*sc(16)
    p2  = math.cos(t*0.48)*sc(13)
    img = orb(img, -sc(10)+int(p1), -sc(20),      sc(200), BLUE, 0.18)
    img = orb(img, W+sc(10)+int(p2), H-sc(10),    sc(170), BLUE, 0.14)
    img = orb(img, W//2, CY+int(p1*0.4),           sc(150), DBLU, 0.22)
    return img

# ── BARRA DE PROGRESO ─────────────────────────────────────────────
def prog(img, t):
    d  = ImageDraw.Draw(img)
    bh = sc(3)
    bw = int(W * min(t/DUR, 1.0))
    if bw > 0:
        d.rectangle([0,0,bw,bh], fill=BLUE)
        if bw < W:
            d.rectangle([max(0,bw-sc(5)),0,bw+1,bh], fill=(130,170,255))
    return img

# ═══════════════════════════════════════════════════════════════════
# ESCENAS
# ═══════════════════════════════════════════════════════════════════

# ── S0: HOOK  0-3s ────────────────────────────────────────────────
def s0(img, lt):
    d  = ImageDraw.Draw(img)
    Y0 = CY - sc(95)

    ma = eo(fade(0.06, 0.38, lt))
    yo = int(lerp(sc(18), 0, eo(fade(0.06, 0.38, lt))))

    for i, line in enumerate(["¿Tu negocio comete", "estos errores?"]):
        lx  = cx(d, line, F_H2)
        img = gtxt(img, (lx, Y0 + i*sc(44) + yo), line, F_H2, WHITE, BLUE, sc(11), ma)
        d   = ImageDraw.Draw(img)

    sub_a = eo(fade(0.54, 0.34, lt))
    if sub_a > 0:
        sub = "La mayoría de negocios los tiene."
        img = otxt(img, (cx(d, sub, F_BD), Y0+sc(108)+yo), sub, F_BD, LGRAY, sub_a)
        d   = ImageDraw.Draw(img)

    # 4 puntos rojos animados
    dots_a = eo(fade(0.74, 0.26, lt))
    if dots_a > 0:
        ds = sc(14)
        dy = Y0 + sc(150) + yo
        for i in range(4):
            da2  = eo(fade(0.74+i*0.05, 0.18, lt)) * dots_a
            dx   = W//2 - sc(45) + i*sc(30)
            surf = Image.new('RGBA', (ds, ds), (0,0,0,0))
            ImageDraw.Draw(surf).ellipse([0,0,ds-1,ds-1], fill=(*RED, int(da2*200)))
            base = img.convert('RGBA')
            base.paste(surf, (dx, dy), surf)
            img  = base.convert('RGB')
            d    = ImageDraw.Draw(img)

    return img


# ── Layout constants para escenas de error ───────────────────────
PAD     = sc(22)
IPAD    = sc(14)
ICON_CX = PAD + IPAD + ICON_S//2        # center x del icono
TITX    = PAD + IPAD + ICON_S + sc(10)  # x del título (junto al icono)
TXTX    = PAD + IPAD                    # x del texto descriptivo
CARD_W  = W - PAD*2
TXT_W   = CARD_W - IPAD*2
ERR_H   = sc(163)
SOL_H   = sc(150)
BADGE_H = sc(28)
GAP     = sc(14)
TOTAL_H = BADGE_H + GAP + ERR_H + GAP + SOL_H
Y_TOP   = CY - TOTAL_H//2


def error_scene(img, lt, num, err_title, err_desc, sol_title, sol_desc):
    d = ImageDraw.Draw(img)

    badge_y = Y_TOP
    err_y   = badge_y + BADGE_H + GAP
    sol_y   = err_y   + ERR_H   + GAP

    # ── Badge "ERROR #N" ─────────────────────────────────────────
    ba = eo(fade(0.06, 0.28, lt))
    if ba > 0:
        yoff = int(lerp(sc(-8), 0, eo(fade(0.06, 0.28, lt))))
        btxt = f"  ERROR #{num}  "
        btw  = tw(d, btxt, F_TAG) + sc(24)
        bx   = (W - btw) // 2
        surf = Image.new('RGBA', (btw, BADGE_H), (0,0,0,0))
        sd   = ImageDraw.Draw(surf)
        sd.rounded_rectangle([0,0,btw-1,BADGE_H-1], radius=sc(14),
                              fill=(*DRED, int(ba*55)),
                              outline=(*RED, int(ba*185)), width=2)
        sd.text((sc(12), sc(7)), btxt, font=F_TAG, fill=(*RED, int(ba*230)))
        base = img.convert('RGBA')
        base.paste(surf, (bx, badge_y+yoff), surf)
        img  = base.convert('RGB')
        d    = ImageDraw.Draw(img)

    # ── Tarjeta de ERROR (roja) ──────────────────────────────────
    ca = eo(fade(0.16, 0.38, lt))
    if ca > 0:
        ey  = int(lerp(sc(12), 0, eo(fade(0.16, 0.38, lt))))
        img = glass_card(img, PAD, err_y+ey, CARD_W, ERR_H, r=sc(16),
                         ba=0.36*ca, oa=0.26*ca, fc=DRED, oc=RED)
        d   = ImageDraw.Draw(img)

        ia = eo(fade(0.22, 0.26, lt))
        if ia > 0:
            img = paste_icon(img, X_ICON, ICON_CX, err_y+ey+sc(22), ia*ca)
            d   = ImageDraw.Draw(img)

        ta = eo(fade(0.26, 0.30, lt))
        if ta > 0:
            d.text((TITX, err_y+ey+sc(10)), err_title, font=F_H4, fill=ac(WHITE, ta*ca))

        da = eo(fade(0.44, 0.30, lt))
        if da > 0:
            for i, ln in enumerate(wrap(d, err_desc, F_SM, TXT_W)):
                d.text((TXTX, err_y+ey+sc(56)+i*sc(17)), ln,
                       font=F_SM, fill=ac(LGRAY, da*ca))

        div_a = eo(fade(0.68, 0.24, lt))
        if div_a > 0:
            dw = int(TXT_W * div_a)
            d.rectangle([TXTX, err_y+ey+sc(124), TXTX+dw, err_y+ey+sc(126)],
                        fill=ac(RED, 0.40*ca))

        imp_a = eo(fade(0.74, 0.24, lt))
        if imp_a > 0:
            imp = "Resultado: ventas perdidas, presupuesto desperdiciado"
            d.text((TXTX, err_y+ey+sc(132)), imp,
                   font=F_SM, fill=ac(RED, imp_a*0.75*ca))

    # ── Tarjeta de SOLUCIÓN (azul) ───────────────────────────────
    sa = eo(fade(1.5, 0.42, lt))
    if sa > 0:
        sy  = int(lerp(sc(14), 0, eo(fade(1.5, 0.42, lt))))
        img = glass_card(img, PAD, sol_y+sy, CARD_W, SOL_H, r=sc(16),
                         ba=0.40*sa, oa=0.22*sa, fc=DBLU, oc=BLUE)
        d   = ImageDraw.Draw(img)

        # Glow azul pulsante
        pulse = 0.5 + 0.5*math.sin(lt*2.6)
        gs    = (0.20 + 0.09*pulse)*sa
        gl5   = Image.new('RGBA', (W,H), (0,0,0,0))
        ImageDraw.Draw(gl5).rounded_rectangle(
            [PAD-sc(10), sol_y+sy-sc(10), W-PAD+sc(10), sol_y+sy+SOL_H+sc(10)],
            radius=sc(22), fill=(*BLUE, int(gs*22)))
        gl5 = gl5.filter(ImageFilter.GaussianBlur(sc(14)))
        img = Image.alpha_composite(img.convert('RGBA'), gl5).convert('RGB')
        d   = ImageDraw.Draw(img)

        la2 = eo(fade(1.56, 0.26, lt))
        if la2 > 0:
            d.text((TITX, sol_y+sy+sc(8)), "LA SOLUCIÓN:",
                   font=F_TAG, fill=ac(BLUE, la2*sa))

        cha = eo(fade(1.62, 0.26, lt))
        if cha > 0:
            img = paste_icon(img, CHK_ICO, ICON_CX, sol_y+sy+sc(40), cha*sa)
            d   = ImageDraw.Draw(img)

        sta = eo(fade(1.66, 0.28, lt))
        if sta > 0:
            d.text((TITX, sol_y+sy+sc(28)), sol_title,
                   font=F_H4, fill=ac(WHITE, sta*sa))

        sda = eo(fade(1.82, 0.30, lt))
        if sda > 0:
            for i, ln in enumerate(wrap(d, sol_desc, F_SM, TXT_W)):
                d.text((TXTX, sol_y+sy+sc(66)+i*sc(17)), ln,
                       font=F_SM, fill=ac(LGRAY, sda*sa))

    return img


# ── S1: Error 1  (3-9s) ───────────────────────────────────────────
def s1(img, lt):
    return error_scene(img, lt, 1,
        "Sin presencia digital",
        "No apareces en Google ni en redes. Tus clientes te buscan online y encuentran a tu competencia.",
        "Web + SEO que te posiciona",
        "Diseñamos tu web profesional y te ponemos en el top de búsquedas para que te encuentren primero.")

# ── S2: Error 2  (9-15s) ──────────────────────────────────────────
def s2(img, lt):
    return error_scene(img, lt, 2,
        "Publicar sin estrategia",
        "Publicar por publicar no vende. Sin plan editorial tu audiencia no crece y no conviertes.",
        "Contenido que genera ventas",
        "Creamos tu calendario editorial y producimos piezas que convierten seguidores en clientes reales.")

# ── S3: Error 3  (15-21s) ─────────────────────────────────────────
def s3(img, lt):
    return error_scene(img, lt, 3,
        "Atender clientes tú solo",
        "Responder manualmente cada mensaje es imposible. Pierdes ventas mientras duermes o trabajas.",
        "IA que vende por ti 24/7",
        "Implementamos asistentes de IA que responden, cualifican y cierran ventas mientras tú descansas.")

# ── S4: Error 4  (21-26s) ─────────────────────────────────────────
def s4(img, lt):
    return error_scene(img, lt, 4,
        "Invertir sin datos",
        "Sin métricas claras, tu publicidad es un tiro al aire. No sabes qué funciona y sigues gastando.",
        "Campañas medibles y rentables",
        "Cada euro invertido tiene seguimiento. Optimizamos en tiempo real para maximizar tu retorno.")

# ── S5: Logo + CTA  (26-30s) ──────────────────────────────────────
def s5(img, lt):
    PAD5   = sc(18)
    lw, lh = LOGO_W, LOGO_H
    CW5    = lw + PAD5*2
    CH5    = lh + PAD5*2
    CX5    = (W - CW5)//2
    BLOC_H = CH5 + sc(28) + sc(30) + sc(10) + sc(18)
    CY5    = CY - BLOC_H//2

    la     = eo(fade(0.06, 0.50, lt))
    lsc    = lerp(0.88, 1.0, eo(fade(0.06, 0.50, lt)))
    anim_y = int(lerp(sc(14), 0, eo(fade(0.06, 0.50, lt))))

    d = ImageDraw.Draw(img)

    if la > 0:
        pulse = 0.5 + 0.5*math.sin(lt*2.1)
        gs    = (0.40 + 0.17*pulse)*la
        icx3  = CX5 + CW5//2
        icy3  = CY5 + anim_y + CH5//2
        for gr3 in [sc(55), sc(30)]:
            gl3 = Image.new('RGBA', (W,H), (0,0,0,0))
            ImageDraw.Draw(gl3).rounded_rectangle(
                [icx3-CW5//2-gr3, icy3-CH5//2-gr3,
                 icx3+CW5//2+gr3, icy3+CH5//2+gr3],
                radius=sc(22)+gr3//2, fill=(*BLUE, int(gs*24)))
            gl3 = gl3.filter(ImageFilter.GaussianBlur(gr3//2+sc(8)))
            img = Image.alpha_composite(img.convert('RGBA'), gl3).convert('RGB')
            d   = ImageDraw.Draw(img)

        CARD_Y = CY5 + anim_y
        card   = Image.new('RGBA', (CW5, CH5), (0,0,0,0))
        cd     = ImageDraw.Draw(card)
        cd.rounded_rectangle([0,0,CW5-1,CH5-1], radius=sc(20),
                              fill=(255,255,255,int(la*252)),
                              outline=(*BLUE, int(la*80)), width=3)
        if lsc < 0.995:
            sw = max(1, int(lw*lsc)); sh = max(1, int(lh*lsc))
            lu = LOGO_FULL.resize((sw,sh), Image.LANCZOS)
            lx_in = (CW5-sw)//2; ly_in = (CH5-sh)//2
        else:
            lu = LOGO_FULL; lx_in, ly_in = PAD5, PAD5
        card.paste(lu, (lx_in, ly_in), lu)
        base = img.convert('RGBA')
        base.paste(card, (CX5, CARD_Y), card)
        img  = base.convert('RGB')
        d    = ImageDraw.Draw(img)

    # Tagline — puede ser 1 o 2 líneas
    tla = eo(fade(0.42, 0.40, lt))
    if tla > 0:
        tly   = CY5 + CH5 + sc(28) + anim_y
        line  = "Nosotros los solucionamos todos."
        lines = wrap(d, line, F_H3, W - PAD*2)
        for i, ln in enumerate(lines):
            img = gtxt(img, (cx(d, ln, F_H3), tly+i*sc(32)), ln,
                       F_H3, WHITE, BLUE, sc(9), tla)
            d   = ImageDraw.Draw(img)

    # Handle
    ha = eo(fade(0.65, 0.30, lt))
    if ha > 0:
        hly  = CY5 + CH5 + sc(28) + sc(50) + anim_y
        htxt = "@blastudios  ·  blastudios.vercel.app"
        d.text((cx(d, htxt, F_SM), hly), htxt,
               font=F_SM, fill=ac((135,138,152), ha))

    return img


# ── TIMELINE ──────────────────────────────────────────────────────
TIMES  = [(0,3),(3,9),(9,15),(15,21),(21,26),(26,30)]
SCENES = [s0, s1, s2, s3, s4, s5]
XFADE  = 0.42

def get_sc(t):
    for i,(s,e) in enumerate(TIMES):
        if s<=t<e: return i, t-s
    return 5, max(0., t-TIMES[5][0])

def render_frame(fi):
    t              = fi / FPS
    si, lt         = get_sc(t)
    s_start, s_end = TIMES[si]
    base           = mk_bg(t)

    if t - s_start < XFADE:
        fa = eio((t - s_start) / XFADE)
    elif s_end - t < XFADE and si < len(SCENES)-1:
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
        result  = Image.blend(base, curr, fa)

    return prog(result, t)

# ── MAIN ──────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"Generando reel errores HD  {W}x{H} @ {FPS}fps  {DUR}s = {FRAMES} frames")
    print(f"SCALE = {SCALE:.3f}  (1080p nativo — sin reescalado por codec)")
    print(f"Destino: {OUT}\n")

    writer = imageio_ffmpeg.write_frames(
        OUT, (W, H), fps=FPS,
        codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p',
        bitrate='18M',
        output_params=['-preset', 'slow', '-crf', '18'],
    )
    writer.send(None)

    t0 = time.time()
    for fi in range(FRAMES):
        if fi % FPS == 0:
            print(f"  {fi//FPS:2d}s / {DUR}s  ({time.time()-t0:.1f}s)")
        writer.send(np.array(render_frame(fi)).tobytes())

    writer.close()
    elapsed = time.time()-t0
    mb = os.path.getsize(OUT)/1_048_576
    print(f"\nCompletado en {elapsed:.1f}s  —  {mb:.1f} MB  —  {OUT}")
