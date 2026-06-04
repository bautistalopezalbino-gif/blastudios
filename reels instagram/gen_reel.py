#!/usr/bin/env python3
"""Generador de Reel Blastudios – 30s MP4  (v3: logo real desde JPG)"""
import os, math, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

# ── CONFIG ────────────────────────────────────────────────────────
W, H   = 390, 692
FPS    = 30
DUR    = 30
FRAMES = FPS * DUR
OUT    = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram\reel_blastudios_beneficios.mp4"
FD     = r"C:\Windows\Fonts"
CY     = H // 2   # centro vertical = 346

# ── COLORES ──────────────────────────────────────────────────────
BG    = (19,  19,  22)
BLUE  = (37,  99,  235)
DBLU  = (13,  27,  62)
WHITE = (248, 250, 252)
LGRAY = (185, 188, 200)
GREEN = (34,  197,  94)

# ── FUENTES ──────────────────────────────────────────────────────
def fnt(name, sz):
    p = os.path.join(FD, name)
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()

FB = lambda s: fnt('segoeuib.ttf', s)
FR = lambda s: fnt('segoeui.ttf',  s)
FL = lambda s: fnt('segoeuil.ttf', s)

# ── ASSETS: logo renderizado desde coordenadas SVG exactas ────────
def _make_logo_img(target_w=300):
    """Renderiza el logo Blastudios desde las coordenadas del SVG a 3x y escala."""
    SVG_W, SVG_H = 520.0, 110.0
    s  = target_w / SVG_W
    th = max(1, int(SVG_H * s))
    R  = 3.0                    # supersampling para anti-aliasing
    sc = s * R
    rw = max(1, int(SVG_W * sc))
    rh = max(1, int(SVG_H * sc))

    surf = Image.new('RGBA', (rw, rh), (0, 0, 0, 0))
    d    = ImageDraw.Draw(surf)

    DNAV  = (13,  31,  60)
    WITE  = (255, 255, 255)
    BBLUE = (37,  99,  235)

    # Icono: rect(5,5)-(105,105) rx=20
    d.rounded_rectangle([5*sc, 5*sc, 105*sc, 105*sc],
                         radius=max(1, int(20*sc)), fill=DNAV)
    # Barra: rect(30,17)-(42,93) rx=6
    d.rounded_rectangle([30*sc, 17*sc, 42*sc, 93*sc],
                         radius=max(1, int(6*sc)), fill=WITE)
    # Círculo exterior: cx=61,cy=76,r=19
    cx_, cy_ = 61*sc, 76*sc
    d.ellipse([cx_-19*sc, cy_-19*sc, cx_+19*sc, cy_+19*sc], fill=WITE)
    # Círculo interior: r=10
    d.ellipse([cx_-10*sc, cy_-10*sc, cx_+10*sc, cy_+10*sc], fill=DNAV)

    # Texto "bla" bold + "studios" light — baseline SVG y=78, x=125
    mfpt = max(10, int(58 * sc))
    fb3  = FB(mfpt); fl3 = FL(mfpt)
    bla_bb = d.textbbox((0, 0), "bla", font=fb3)
    bla_w  = bla_bb[2] - bla_bb[0]
    tx_    = int(125 * sc)
    by_    = int(78  * sc)
    d.text((tx_,        by_), "bla",     font=fb3, fill=DNAV,  anchor="ls")
    d.text((tx_+bla_w,  by_), "studios", font=fl3, fill=DNAV,  anchor="ls")

    # Tagline — baseline SVG y=100, x=127
    tfpt = max(6, int(13 * sc))
    ftag = FB(tfpt)
    d.text((int(127*sc), int(100*sc)), "DIGITAL MARKETING AGENCY",
           font=ftag, fill=BBLUE, anchor="ls")

    return surf.resize((target_w, th), Image.LANCZOS)

LOGO_FULL = _make_logo_img(300)
LOGO_W, LOGO_H = LOGO_FULL.size

F_H1   = FB(34)   # titular grande
F_H2   = FB(26)   # titular medio
F_H3   = FB(21)   # titular pequeño
F_NUM  = FB(64)   # número grande
F_BD   = FR(14)   # cuerpo
F_SM   = FR(12)   # cuerpo pequeño
F_TAG  = FB(11)   # label uppercase
# Logo: "bla" bold 28pt / "studios" light 28pt — mismo tamaño, distinto peso
F_LB   = FB(28)
F_LL   = FL(28)

# ── MATH ─────────────────────────────────────────────────────────
def eo(t):        return 1-(1-_c(t))**3
def eio(t):       t=_c(t); return t*t*(3-2*t)
def _c(v):        return max(0., min(1., v))
def lerp(a,b,t):  return a+(b-a)*t
def fade(s,d,t):  return _c((t-s)/d) if d>0 else (1. if t>=s else 0.)

# ── HELPERS ───────────────────────────────────────────────────────
def tw(d, txt, f):
    b = d.textbbox((0,0), txt, font=f); return b[2]-b[0]

def th(d, txt, f):
    b = d.textbbox((0,0), txt, font=f); return b[3]-b[1]

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

def glass(img, x, y, w, h, r=18, ba=0.42, oa=0.20):
    surf = Image.new('RGBA', (w, h), (0,0,0,0))
    d2 = ImageDraw.Draw(surf)
    d2.rounded_rectangle([0,0,w-1,h-1], radius=r,
                          fill=(*DBLU, int(ba*255)),
                          outline=(*BLUE, int(oa*255)), width=1)
    base = img.convert('RGBA')
    base.paste(surf, (x, y), surf)
    return base.convert('RGB')

def orb(img, x, y, rad, col, s=0.28):
    sz = rad*2
    o = Image.new('RGBA', (sz,sz), (0,0,0,0))
    od = ImageDraw.Draw(o)
    for r in range(rad, 0, max(1, rad//22)):
        a = int(s * 255 * ((1-r/rad)**0.55))
        od.ellipse([rad-r,rad-r,rad+r,rad+r], fill=(*col, a))
    o = o.filter(ImageFilter.GaussianBlur(rad//4))
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

# ── FONDO ────────────────────────────────────────────────────────
def bg(t):
    img = Image.new('RGB', (W,H), BG)
    p1  = math.sin(t*0.65)*16
    p2  = math.cos(t*0.48)*13
    img = orb(img, -10+int(p1), -20, 200, BLUE, 0.25)
    img = orb(img, W+10+int(p2), H-10, 170, BLUE, 0.19)
    img = orb(img, W//2, CY+int(p1*0.4), 150, DBLU, 0.28)
    return img

# ── BARRA DE PROGRESO ─────────────────────────────────────────────
def prog(img, t):
    d = ImageDraw.Draw(img)
    bw = int(W * min(t/DUR, 1.0))
    if bw > 0:
        d.rectangle([0,0,bw,3], fill=BLUE)
        if bw < W:
            d.rectangle([max(0,bw-5),0,bw+1,3], fill=(130,170,255))
    return img

# ═══════════════════════════════════════════════════════════════════
# ESCENAS — todos los bloques centrados en CY=346
# ═══════════════════════════════════════════════════════════════════

# ── S0: HOOK ─────────────────────────────────────────────────────
# Bloque: línea1(32) + gap(14) + línea2(32) + gap(22) + typewriter(26) = 126px
# Inicio = CY - 63 = 283
def s0(img, lt):
    d = ImageDraw.Draw(img)
    Y0 = CY - 63          # 283

    ma  = eo(fade(0.08, 0.4, lt))
    yo  = int(lerp(16, 0, eo(fade(0.08, 0.4, lt))))

    for i, line in enumerate(["¿Tu negocio", "trabaja para ti..."]):
        lx = cx(d, line, F_H2)
        ly = Y0 + i*46 + yo
        img = gtxt(img, (lx, ly), line, F_H2, WHITE, BLUE, 11, ma)
        d = ImageDraw.Draw(img)

    full  = "...¿o tú para él?"
    spd   = len(full) / 1.1
    nc    = int(min((lt-0.65)*spd, len(full))) if lt > 0.65 else 0
    typed = full[:nc]
    if typed:
        ta  = eo(fade(0.65, 0.18, lt))
        fw  = tw(d, full, F_H3)
        lx2 = (W - fw) // 2
        img = gtxt(img, (lx2, Y0+114+yo), typed, F_H3, BLUE, BLUE, 9, ta)
        d = ImageDraw.Draw(img)
    if lt > 0.65 and nc < len(full) and (lt*1.8)%1 < 0.55:
        fw   = tw(d, full,  F_H3)
        typw = tw(d, typed, F_H3) if typed else 0
        cx2  = (W-fw)//2 + typw + 3
        d.rectangle([cx2, Y0+116+yo, cx2+2, Y0+136+yo], fill=BLUE)
    return img

# ── S1: WEB ───────────────────────────────────────────────────────
# Bloque: browser(162) + gap(18) + card(136) = 316px  →  inicio = CY-158 = 188
def s1(img, lt):
    PAD = 24
    BRY = CY - 158        # 188  – browser top
    CRY = BRY + 162 + 18  # 368  – card top
    CRH = 136

    d = ImageDraw.Draw(img)
    bw2 = W - PAD*2

    # Browser mock
    br_a = eo(fade(0.05, 0.36, lt))
    br_y = BRY + int(lerp(18, 0, eo(fade(0.05, 0.36, lt))))
    if br_a > 0:
        img = glass(img, PAD, br_y, bw2, 162, 14, ba=0.50*br_a, oa=0.20*br_a)
        d = ImageDraw.Draw(img)
        d.rectangle([PAD, br_y, PAD+bw2, br_y+26], fill=ac((18,38,90), br_a))
        for i, dc in enumerate([(220,80,70),(220,170,50),(50,190,80)]):
            dx = PAD+12+i*14
            d.ellipse([dx-4, br_y+9, dx+4, br_y+17], fill=ac(dc, br_a))
        d.rounded_rectangle([PAD+52, br_y+5, PAD+bw2-8, br_y+21], radius=4, fill=ac((30,35,58), br_a))
        d.text((PAD+58, br_y+7), "blastudios.com.ar", font=F_SM, fill=ac((155,160,178), br_a))
        hy = br_y+32
        d.rounded_rectangle([PAD+8, hy, PAD+bw2-8, hy+52], radius=8, fill=ac((22,50,118), br_a))
        htxt = "TU MARCA  ·  ONLINE  ·  AHORA"
        d.text((cx(d, htxt, F_TAG, PAD+8, bw2-16), hy+19), htxt, font=F_TAG, fill=ac((172,178,198), br_a))
        shim = (lt*0.45)%1.0; ry2 = hy+60
        for rw3 in [bw2-38, bw2-62, bw2-98]:
            d.rounded_rectangle([PAD+8,ry2,PAD+8+rw3,ry2+7], radius=3, fill=ac((46,52,72), br_a))
            sx = PAD+8+int((rw3+55)*shim)-28
            sx1,sx2 = max(PAD+8,sx), min(PAD+8+rw3,sx+32)
            if sx2>sx1: d.rounded_rectangle([sx1,ry2,sx2,ry2+7], radius=3, fill=ac((65,95,190), br_a*0.6))
            ry2 += 14

    # Card de texto
    img = glass(img, PAD, CRY, W-PAD*2, CRH)
    d = ImageDraw.Draw(img)
    ta = eo(fade(0.17, 0.26, lt))
    if ta > 0:
        d.text((PAD+20, CRY+15), "DISEÑO WEB", font=F_TAG, fill=ac(BLUE, ta))
    ha = eo(fade(0.27, 0.28, lt))
    hy2 = CRY+36+int(lerp(10, 0, eo(fade(0.27, 0.28, lt))))
    if ha > 0:
        t1w = tw(d, "WEB QUE ", F_H3)
        d.text((PAD+20,    hy2), "WEB QUE ",  font=F_H3, fill=ac(WHITE, ha))
        d.text((PAD+20+t1w,hy2), "CONVIERTE", font=F_H3, fill=ac(BLUE,  ha))
    sa = eo(fade(0.37, 0.28, lt))
    if sa > 0:
        for i,ln in enumerate(wrap(d, "Diseñamos experiencias que transforman visitas en clientes reales.", F_SM, W-PAD*2-40)):
            d.text((PAD+20, CRY+66+i*17), ln, font=F_SM, fill=ac(LGRAY, sa))
    return img

# ── S2: MÉTRICAS ─────────────────────────────────────────────────
# Bloque: card(210) + gap(14) + chart(74) = 298px  →  inicio = CY-149 = 197
def s2(img, lt):
    PAD = 24
    CRY = CY - 149        # 197
    CRH = 210
    CTY = CRY + CRH + 14  # 421  – chart top
    CTH = 74

    img = glass(img, PAD, CRY, W-PAD*2, CRH)
    d = ImageDraw.Draw(img)

    ta = eo(fade(0.05, 0.26, lt))
    if ta > 0:
        d.text((PAD+20, CRY+14), "CAMPAÑAS DIGITALES", font=F_TAG, fill=ac(BLUE, ta))

    # Contador animado
    ca  = eo(fade(0.09, 0.33, lt))
    cv  = int(min((lt-0.09)/1.05*247, 247)) if lt > 0.09 else 0
    if ca > 0:
        ns  = str(cv)
        ny  = CRY + 40 + int(lerp(14, 0, eo(fade(0.09, 0.33, lt))))
        gl  = Image.new('RGBA', (W,H), (0,0,0,0))
        gd  = ImageDraw.Draw(gl)
        gd.text((PAD+20, ny), ns, font=F_NUM, fill=(*BLUE, int(ca*75)))
        gl  = gl.filter(ImageFilter.GaussianBlur(13))
        img = Image.alpha_composite(img.convert('RGBA'), gl).convert('RGB')
        d   = ImageDraw.Draw(img)
        d.text((PAD+20, ny), ns, font=F_NUM, fill=ac(BLUE, ca))
        d.text((PAD+22+tw(d,ns,F_NUM), ny+24), "%", font=F_H2, fill=ac(WHITE, ca))

    ha  = eo(fade(0.18, 0.28, lt))
    hy3 = CRY+136+int(lerp(10, 0, eo(fade(0.18, 0.28, lt))))
    if ha > 0:
        t1w = tw(d, "RESULTADOS ", F_H3)
        d.text((PAD+20,     hy3), "RESULTADOS ", font=F_H3, fill=ac(WHITE, ha))
        d.text((PAD+20+t1w, hy3), "MEDIBLES",    font=F_H3, fill=ac(BLUE,  ha))

    sa = eo(fade(0.28, 0.26, lt))
    if sa > 0:
        for i,ln in enumerate(wrap(d, "Campañas basadas en datos — sin malgastar tu presupuesto.", F_SM, W-PAD*2-40)):
            d.text((PAD+20, CRY+163+i*17), ln, font=F_SM, fill=ac(LGRAY, sa))

    # Chart de barras
    cha  = eo(fade(0.14, 0.48, lt))
    grow = eo(fade(0.14, 0.52, lt))
    if cha > 0:
        bw4 = (W-PAD*2 - 8*4) // 5
        for bi, bv in enumerate([0.28, 0.44, 0.60, 0.76, 1.0]):
            bx2 = PAD + bi*(bw4+8)
            bh4 = int(CTH*bv*grow)
            by4 = CTY+CTH-bh4
            if bh4 <= 0: continue
            if bi == 4:
                col = ac(BLUE, cha)
                d.rounded_rectangle([bx2,by4,bx2+bw4,CTY+CTH], radius=5, fill=col)
                gl2 = Image.new('RGBA',(W,H),(0,0,0,0))
                ImageDraw.Draw(gl2).rounded_rectangle([bx2-4,by4-4,bx2+bw4+4,CTY+CTH+4], radius=7, fill=(*BLUE,int(cha*65)))
                gl2 = gl2.filter(ImageFilter.GaussianBlur(6))
                img = Image.alpha_composite(img.convert('RGBA'), gl2).convert('RGB')
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([bx2,by4,bx2+bw4,CTY+CTH], radius=5, fill=col)
            else:
                d.rounded_rectangle([bx2,by4,bx2+bw4,CTY+CTH], radius=5, fill=tuple(int(c*cha*0.17) for c in BLUE))
    return img

# ── S3: IA 24/7 ───────────────────────────────────────────────────
# Bloque: badge(38)+gap(12)+bbl1(56)+gap(10)+bbl2(56)+gap(10)+status(20)+gap(12)+card(136) = 350px
# Inicio = CY-175 = 171
def s3(img, lt):
    PAD  = 24
    Y3   = CY - 175   # 171 – badge top

    d = ImageDraw.Draw(img)

    # Badge 24/7
    ba2 = eo(fade(0.05, 0.36, lt))
    by2 = Y3 + int(lerp(-6, 0, eo(fade(0.05, 0.36, lt))))
    if ba2 > 0:
        btxt  = "  24/7 ACTIVO"
        btw3  = tw(d, btxt, F_H3) + 40
        bx3   = (W - btw3) // 2
        surf  = Image.new('RGBA', (btw3, 38), (0,0,0,0))
        sd    = ImageDraw.Draw(surf)
        sd.rounded_rectangle([0,0,btw3-1,37], radius=19,
                              fill=(*DBLU, int(ba2*112)),
                              outline=(*BLUE, int(ba2*130)), width=1)
        sd.text((20, 9), btxt, font=F_H3, fill=(*WHITE, int(ba2*218)))
        base = img.convert('RGBA')
        base.paste(surf, (bx3, by2), surf)
        img = base.convert('RGB')
        d = ImageDraw.Draw(img)

    # Burbujas de chat
    cy2 = Y3 + 50   # 221
    for bst, btxt2, is_u in [
        (0.18, "Hola, quiero información\nsobre vuestros servicios", True),
        (0.54, "¡Hola! Soy el asistente de\nBlastudios. Te cuento todo", False),
    ]:
        ba3 = eo(fade(bst, 0.30, lt))
        if ba3 <= 0:
            cy2 += 66; continue
        blines = btxt2.split('\n')
        mlw = max(tw(d, ln, F_BD) for ln in blines)
        bw5 = min(mlw+28, int(W*0.76))
        bh5 = len(blines)*19 + 18
        bx4 = W-PAD-bw5 if is_u else PAD
        ysl = int(lerp(8, 0, eo(fade(bst, 0.30, lt))))
        fc  = (*BLUE, int(ba3*58)) if is_u else (*DBLU, int(ba3*162))
        oc  = (*BLUE, int(ba3*98)) if is_u else (*BLUE, int(ba3*62))
        surf = Image.new('RGBA', (bw5, bh5), (0,0,0,0))
        sd   = ImageDraw.Draw(surf)
        sd.rounded_rectangle([0,0,bw5-1,bh5-1], radius=14, fill=fc, outline=oc, width=1)
        for li, ln in enumerate(blines):
            sd.text((14, 9+li*19), ln, font=F_BD, fill=(*WHITE, int(ba3*212)))
        base = img.convert('RGBA')
        base.paste(surf, (bx4, cy2+ysl), surf)
        img = base.convert('RGB')
        d = ImageDraw.Draw(img)
        cy2 += bh5 + 10

    # Status verde
    sta = eo(fade(0.93, 0.26, lt))
    if sta > 0:
        blink = 1.0 if (lt*2)%1 < 0.55 else 0.35
        d.ellipse([PAD, cy2+5, PAD+8, cy2+13], fill=ac(GREEN, sta*blink))
        d.text((PAD+14, cy2+2), "IA respondiendo en segundos", font=F_SM, fill=ac(GREEN, sta))
        cy2 += 24

    # Card de texto (debajo de los chats)
    cy3 = cy2 + 10
    ch3 = 136
    if cy3 + ch3 < H - 6:
        img = glass(img, PAD, cy3, W-PAD*2, ch3)
        d = ImageDraw.Draw(img)
        ta2 = eo(fade(0.26, 0.26, lt))
        if ta2 > 0:
            d.text((PAD+20, cy3+14), "AUTOMATIZACIÓN CON IA", font=F_TAG, fill=ac(BLUE, ta2))
        ha2 = eo(fade(0.36, 0.28, lt))
        hy4 = cy3+36+int(lerp(10, 0, eo(fade(0.36, 0.28, lt))))
        if ha2 > 0:
            t1w = tw(d, "TU NEGOCIO ", F_H3)
            d.text((PAD+20,     hy4), "TU NEGOCIO ", font=F_H3, fill=ac(WHITE, ha2))
            d.text((PAD+20+t1w, hy4), "NUNCA PARA",  font=F_H3, fill=ac(BLUE,  ha2))
        sa2 = eo(fade(0.47, 0.28, lt))
        if sa2 > 0:
            for i,ln in enumerate(wrap(d, "Sistemas autónomos que atienden, venden y fidelizan mientras tú descansas.", F_SM, W-PAD*2-40)):
                d.text((PAD+20, cy3+64+i*17), ln, font=F_SM, fill=ac(LGRAY, sa2))
    return img

# ── S4: LOGO (SVG renderizado a Pillow) ──────────────────────────
# Card blanca con logo exacto + tagline en oscuro debajo
def s4(img, lt):
    PAD4   = 18
    lw, lh = LOGO_W, LOGO_H          # 300 x ~63
    CARD_W = lw + PAD4 * 2           # 336
    CARD_H = lh + PAD4 * 2
    CARD_X = (W - CARD_W) // 2

    # Bloque total: CARD_H + 22 + 66
    TOTAL_H = CARD_H + 22 + 66
    CARD_Y0 = CY - TOTAL_H // 2

    la  = eo(fade(0.07, 0.48, lt))
    lsc = lerp(0.88, 1.0, eo(fade(0.07, 0.48, lt)))
    lyo = int(lerp(14, 0, eo(fade(0.07, 0.48, lt))))

    d = ImageDraw.Draw(img)

    if la > 0:
        # Glow pulsante azul detrás de la card
        pulse = 0.5 + 0.5 * math.sin(lt * 2.1)
        gs    = (0.40 + 0.17 * pulse) * la
        cx3   = CARD_X + CARD_W // 2
        cy3   = CARD_Y0 + lyo + CARD_H // 2
        for gr3 in [55, 30]:
            gl3 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl3).rounded_rectangle(
                [cx3-CARD_W//2-gr3, cy3-CARD_H//2-gr3,
                 cx3+CARD_W//2+gr3, cy3+CARD_H//2+gr3],
                radius=22+gr3//2, fill=(*BLUE, int(gs*24)))
            gl3 = gl3.filter(ImageFilter.GaussianBlur(gr3//2+8))
            img = Image.alpha_composite(img.convert('RGBA'), gl3).convert('RGB')
            d   = ImageDraw.Draw(img)

        # Card blanca
        CARD_Y = CARD_Y0 + lyo
        card   = Image.new('RGBA', (CARD_W, CARD_H), (0, 0, 0, 0))
        cd     = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, CARD_W-1, CARD_H-1], radius=20,
                              fill=(255, 255, 255, int(la * 252)),
                              outline=(*BLUE, int(la * 80)), width=2)

        # Logo con animación de escala en entrada
        if lsc < 0.995:
            sw = max(1, int(lw * lsc))
            sh = max(1, int(lh * lsc))
            logo_use = LOGO_FULL.resize((sw, sh), Image.LANCZOS)
            lx_off   = (CARD_W - sw) // 2
            ly_off   = (CARD_H - sh) // 2
        else:
            logo_use = LOGO_FULL
            lx_off, ly_off = PAD4, PAD4

        card.paste(logo_use, (lx_off, ly_off), logo_use)

        base = img.convert('RGBA')
        base.paste(card, (CARD_X, CARD_Y), card)
        img  = base.convert('RGB')
        d    = ImageDraw.Draw(img)

    # Tagline sobre el fondo oscuro (aparece con delay)
    tla = eo(fade(0.60, 0.40, lt))
    if tla > 0:
        tly = CARD_Y0 + CARD_H + 22 + lyo
        for i, line in enumerate(['"No es suerte.', 'Es sistema."']):
            ltw2 = tw(d, line, F_H3)
            lx3  = (W - ltw2) // 2
            img  = gtxt(img, (lx3, tly + i*32), line, F_H3, WHITE, BLUE, 9, tla)
            d    = ImageDraw.Draw(img)
    return img

# ── S5: CTA ───────────────────────────────────────────────────────
# Bloque: label(14)+gap(22)+title(60)+gap(22)+btn(48)+gap(18)+handle(14) = 198px
# Inicio = CY-99 = 247
def s5(img, lt):
    Y5  = CY - 99    # 247
    d   = ImageDraw.Draw(img)

    # Label superior
    lbl = "EMPIEZA HOY"
    d.text((cx(d, lbl, F_TAG), Y5), lbl, font=F_TAG, fill=BLUE)

    # Título (dos líneas)
    ta3 = eo(fade(0.07, 0.34, lt))
    tyo = int(lerp(12, 0, eo(fade(0.07, 0.34, lt))))
    if ta3 > 0:
        for i, line in enumerate(["¿Listo para que tu negocio", "crezca con IA?"]):
            ltw3 = tw(d, line, F_H3)
            d.text(((W-ltw3)//2, Y5+36+i*32+tyo), line, font=F_H3, fill=ac(WHITE, ta3))

    # Botón
    ba4 = eo(fade(0.24, 0.36, lt))
    BTY = Y5 + 130   # 377
    if ba4 > 0:
        btxt2 = "  Escribenos ahora"
        btw4  = tw(d, btxt2, F_BD) + 52
        bh6   = 48
        bx5   = (W - btw4) // 2
        pulse = 0.5 + 0.5*math.sin(lt*3.0)
        gr4   = int((15+10*pulse) * ba4)
        gl4   = Image.new('RGBA', (W,H), (0,0,0,0))
        ImageDraw.Draw(gl4).rounded_rectangle(
            [bx5-gr4//2, BTY-gr4//4, bx5+btw4+gr4//2, BTY+bh6+gr4//4],
            radius=bh6//2+gr4//4, fill=(*BLUE, int(ba4*46)))
        gl4   = gl4.filter(ImageFilter.GaussianBlur(gr4//2+4))
        img   = Image.alpha_composite(img.convert('RGBA'), gl4).convert('RGB')
        d     = ImageDraw.Draw(img)
        d.rounded_rectangle([bx5, BTY, bx5+btw4, BTY+bh6], radius=bh6//2, fill=ac(BLUE, ba4))
        itw3  = tw(d, btxt2, F_BD)
        d.text(((W-itw3)//2, BTY+14), btxt2, font=F_BD, fill=ac(WHITE, ba4))

    # Handle
    ha3 = eo(fade(0.42, 0.33, lt))
    if ha3 > 0:
        htxt = "@blastudios  ·  linktr.ee/blastudios"
        d.text((cx(d, htxt, F_SM), BTY+64), htxt, font=F_SM, fill=ac((135,138,152), ha3))
    return img

# ── TIMELINE ─────────────────────────────────────────────────────
TIMES  = [(0,3),(3,9),(9,15),(15,21),(21,26),(26,30)]
SCENES = [s0, s1, s2, s3, s4, s5]
XFADE  = 0.44

def get_sc(t):
    for i,(s,e) in enumerate(TIMES):
        if s<=t<e: return i, t-s
    return 5, max(0., t-TIMES[5][0])

def render_frame(fi):
    t            = fi / FPS
    si, lt       = get_sc(t)
    s_start, s_end = TIMES[si]
    base         = bg(t)

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
        result = Image.blend(base, curr, fa)

    return prog(result, t)

# ── MAIN ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"Generando reel Blastudios  {W}x{H} @ {FPS}fps  {DUR}s = {FRAMES} frames")
    print(f"Destino: {OUT}\n")

    writer = imageio_ffmpeg.write_frames(
        OUT, (W, H), fps=FPS,
        codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p', bitrate='5M',
    )
    writer.send(None)

    t0 = time.time()
    for fi in range(FRAMES):
        if fi % FPS == 0:
            print(f"  {fi//FPS:2d}s / {DUR}s  ({time.time()-t0:.1f}s)")
        writer.send(np.array(render_frame(fi)).tobytes())

    writer.close()
    elapsed = time.time() - t0
    mb = os.path.getsize(OUT) / 1_048_576
    print(f"\nCompletado en {elapsed:.1f}s  —  {mb:.1f} MB  —  {OUT}")
