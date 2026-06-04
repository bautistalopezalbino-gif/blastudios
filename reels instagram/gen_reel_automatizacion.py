"""
Reel Blastudios v3 — Premium iOS-style
- Spring bounce animations (damped oscillator)
- Real GaussianBlur glassmorphism para karaoke y cards
- Layout fijo: sin solapamientos, sin huecos muertos
- Crossfade entre escenas (scale + fade)
- Progress pips al estilo iOS
- Gradient blob de acento por escena
- Tipografía de impacto (2× mayor)
- Description chip entre título y karaoke
"""

import asyncio, os, math, random, subprocess, time
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np

# ── Dimensiones ──────────────────────────────────────────────────────────────
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

# ── Layout ───────────────────────────────────────────────────────────────────
# (todos en píxeles absolutos para claridad)
HDR_H    = 140     # cabecera blanca con logo
PIP_CY   = 175     # centro Y de los progress pips
CARD_T   = 198     # tope de la glass card principal
CARD_B   = 770     # base de la glass card
CARD_L   = sc(20)  # izquierda de la card  = 55px
CARD_R_X = W - sc(20)  # derecha de la card = 1025px
TITLE_Y  = CARD_B + sc(18)   # 820px — título grande
CHIP_Y   = TITLE_Y + sc(38)*2 + sc(10) + sc(18)  # ~1064px — description chip
KARA_T   = H - sc(310)       # 1062px — karaoke top  ← mucho más arriba
KARA_H   = sc(170)           # 471px — karaoke alto (grande!)
KARA_B   = KARA_T + KARA_H  # 1533px
URL_Y    = KARA_B + sc(20)   # 1588px

# ── Colores ──────────────────────────────────────────────────────────────────
BG    = (  8,   9,  14)   # iOS near-black
BLUE  = ( 37,  99, 235)
LBLU  = ( 96, 165, 250)
DBLU  = (  5,  13,  44)
WHITE = (248, 250, 252)
GRAY  = ( 98, 105, 128)
LGRAY = (160, 165, 185)
DGRAY = ( 22,  24,  36)
GREEN = ( 34, 197,  94)
AMBER = (245, 158,  11)
RED   = (220,  50,  47)
TEAL  = ( 20, 184, 166)
VIOL  = (139,  92, 246)
PINK  = (236,  72, 153)

# Por escena: color de acento para el blob de fondo
SCENE_ACCENT = [BLUE, LBLU, VIOL, PINK, GREEN, AMBER, BLUE]

# ── Fuentes ───────────────────────────────────────────────────────────────────
def _fnt(name, sz):
    try:    return ImageFont.truetype(os.path.join(FD, name), sz)
    except: return ImageFont.load_default()

def FB(s): return _fnt('segoeuib.ttf', s)
def FR(s): return _fnt('segoeui.ttf',  s)
def FL(s): return _fnt('segoeuil.ttf', s)

# Tamaños de fuente — MUCHO MÁS GRANDES que v2
F_TITLE  = FB(sc(34))   # 94px — título principal
F_H2     = FB(sc(22))   # 61px — subtítulos
F_CHIP   = FR(sc(13))   # 36px — description chip
F_SUB_N  = FR(sc(16))   # 44px — subtitle normal
F_SUB_H  = FB(sc(18))   # 50px — subtitle highlighted
F_SUB_P  = FL(sc(15))   # 42px — subtitle past
F_TAG    = FR(sc(10))   # 28px — tags pequeños
F_FRAC   = FB(sc(11))   # 30px — "1/5"
F_NUMWM  = FB(sc(90))   # 249px — número watermark

# ── Logo ─────────────────────────────────────────────────────────────────────
def _load_logo(target_h):
    img = Image.open(LOGO_PNG).convert("RGBA")
    ar  = img.width / img.height
    tw  = int(target_h * ar)
    return img.resize((tw, target_h), Image.LANCZOS)

LOGO_IMG = _load_logo(int(HDR_H * 0.64))

# ── Guión ─────────────────────────────────────────────────────────────────────
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
    # (id, label, title, chip_text, bg_type)
    ("intro", "",    "¿Sabes qué hace\ntu competencia?",  "Mientras tú duermes...",       "intro"),
    ("s1",    "01",  "Atención\nal cliente",               "Chatbot activo 24/7 · sin ti", "chat"),
    ("s2",    "02",  "Secuencias\nde email",               "Lead → cliente, solo",         "email"),
    ("s3",    "03",  "Publicación\nen redes",              "Contenido diario · sin nadie", "social"),
    ("s4",    "04",  "Facturación\nautomática",            "Cobros sin errores ni retrasos","invoice"),
    ("s5",    "05",  "Análisis en\ntiempo real",           "Saben qué funciona. Tú no.",   "chart"),
    ("cta",   "",    "Blastudios\nlo hace\npor ti.",       "blastudios.vercel.app",        "cta"),
]

# ── Easing iOS ────────────────────────────────────────────────────────────────
def _spring(t):
    """Damped spring — overshoots ~8% y vuelve suavemente (iOS feel)."""
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    omega = 22.0; zeta = 0.52
    od = omega * math.sqrt(max(0, 1 - zeta**2))
    val = 1 - math.exp(-zeta * omega * t) * (
        math.cos(od * t) + (zeta / math.sqrt(max(1e-9, 1 - zeta**2))) * math.sin(od * t)
    )
    return max(0.0, val)

def _eo(t): return 1 - (1 - min(1.0, max(0.0, t)))**3   # ease-out cúbico

def sp(t, dur=0.55):
    """Spring over `dur` seconds, t in seconds."""
    return _spring(min(t / dur, 1.0))

def fo(t, dur=0.30):
    """Ease-out fade over `dur` seconds."""
    return _eo(min(t / dur, 1.0))

def clamp(v, lo=0.0, hi=1.0): return max(lo, min(hi, v))

# ── Compositing ───────────────────────────────────────────────────────────────
def composite(base, layer):
    """Paste RGBA layer onto RGB base in-place."""
    merged = Image.alpha_composite(base.convert('RGBA'), layer)
    base.paste(merged.convert('RGB'))

def new_layer(): return Image.new('RGBA', (W, H), (0,0,0,0))

# ── Glassmorphism ─────────────────────────────────────────────────────────────
def glass_rect(img, x0, y0, x1, y1, radius,
               blur=10, fill=(255,255,255,14), border=(255,255,255,35)):
    """
    Real glassmorphism:
      1. Crop region, GaussianBlur, paste back (frosted)
      2. Semi-transparent fill overlay
      3. White hairline border
      4. Top-edge inner highlight
    """
    # --- Blur region underneath ---
    pad = blur * 2
    cx0, cy0 = max(0, x0-pad), max(0, y0-pad)
    cx1, cy1 = min(W, x1+pad), min(H, y1+pad)
    region = img.crop((cx0, cy0, cx1, cy1)).filter(ImageFilter.GaussianBlur(blur))
    mask_blur = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask_blur).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=220)
    tmp = Image.new('RGB', (W, H))
    tmp.paste(region, (cx0, cy0))
    img.paste(tmp, mask=mask_blur)

    # --- Overlay ---
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)
    # Top inner highlight
    d.rounded_rectangle([x0+2, y0+2, x1-2, min(y1, y0+radius*2+6)],
                        radius=radius, fill=(255, 255, 255, 10))
    # Border
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=border, width=2)
    composite(img, layer)

def glass_pill(img, cx, cy, pw, ph, radius,
               fill=(255,255,255,12), border=(255,255,255,40)):
    glass_rect(img, cx-pw//2, cy-ph//2, cx+pw//2, cy+ph//2, radius,
               blur=8, fill=fill, border=border)

# ── Utilidades de dibujo ──────────────────────────────────────────────────────
def rr(d, xy, r, fill=None, outline=None, ow=2):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=ow)

def txt_cx(d, cx, y, text, font, fill):
    bb = d.textbbox((0,0), text, font=font)
    d.text((cx-(bb[2]-bb[0])//2, y), text, font=font, fill=fill)
    return bb[3]-bb[1]

def glow(img, cx, cy, r, color, peak=45):
    lay = new_layer()
    d   = ImageDraw.Draw(lay)
    for i in range(6, 0, -1):
        a = int(peak * (i/6)**2)
        ri = r + sc(14)*(6-i+1)
        d.ellipse([cx-ri, cy-ri, cx+ri, cy+ri], fill=(*color[:3], a))
    composite(img, lay)

# ── Fondo: gradient blob + starfield ─────────────────────────────────────────
_rng = random.Random(42)
STARS = [((_rng.randint(0,W)), _rng.randint(0,H), _rng.random()) for _ in range(90)]

def draw_bg_base(img, scene_idx, lt, tg):
    """Gradient blob + starfield. Blob cambia de color por escena."""
    img.paste(BG, [0,0,W,H])
    accent = SCENE_ACCENT[scene_idx % len(SCENE_ACCENT)]

    # Radial gradient blob (centrado en el tercio superior)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    blob_cx = W//2 + int(sc(30) * math.sin(tg * 0.2))
    blob_cy = H // 3 + int(sc(20) * math.cos(tg * 0.15))
    pulsate = 1.0 + 0.04 * math.sin(tg * 0.8)
    for i in range(8, 0, -1):
        a  = int(22 * (i/8)**2 * fo(lt, 1.0))
        ri = int(sc(260) * (i/8) * pulsate)
        d.ellipse([blob_cx-ri, blob_cy-ri, blob_cx+ri, blob_cy+ri],
                  fill=(*accent, a))
    composite(img, layer)

    # Estrellas
    lay2 = new_layer()
    d2   = ImageDraw.Draw(lay2)
    for sx, sy, br in STARS:
        p = (math.sin(tg * 0.6 + br * 6.28) + 1) / 2
        a = int(170 * (0.06 + 0.20 * br * p))
        r2 = 1 if br < 0.55 else 2
        d2.ellipse([sx-r2, sy-r2, sx+r2, sy+r2], fill=(*WHITE, a))
    composite(img, lay2)

# ── Fondos animados por escena ────────────────────────────────────────────────
SHOT_DUR = 4.0

def _shot(lt):
    s = int(lt / SHOT_DUR); ts = lt % SHOT_DUR
    fi = min(ts / 0.4, 1.0); fo2 = max(0.0, 1-(ts-(SHOT_DUR-0.4))/0.4)
    return s, ts, min(fi, fo2)

def _panel(d, x0,y0,x1,y1, r, a, col=DGRAY):
    d.rounded_rectangle([x0,y0,x1,y1], radius=r, fill=(*col,a))

def _bubble(d, x,y,w,h, right, a, txt="", fnt=None):
    col = BLUE if right else DGRAY
    d.rounded_rectangle([x,y,x+w,y+h], radius=sc(8),
                        fill=(*col, a), outline=(*(LBLU if right else GRAY), a//2), width=1)
    if txt and fnt:
        bb = d.textbbox((0,0), txt, font=fnt)
        d.text((x+(w-(bb[2]-bb[0]))//2, y+(h-(bb[3]-bb[1]))//2), txt, font=fnt, fill=(*WHITE,a))

def bg_intro(lay, lt, tg):
    d = ImageDraw.Draw(lay); cx, cy = W//2, H//2
    for ring in range(7):
        ph = (lt*0.32 + ring*0.65) % 4.8
        a  = int(22 * max(0, 1-ph/4.8))
        ri = int(sc(40) + ph*sc(190))
        d.ellipse([cx-ri,cy-ri,cx+ri,cy+ri], outline=(*LBLU,a), width=sc(2))
    for i in range(5):
        ang = tg*0.16 + i*(2*math.pi/5)
        ro  = sc(280) + sc(25)*math.sin(tg*0.45+i*1.2)
        px  = cx+int(ro*math.cos(ang)); py = cy+int(ro*math.sin(ang)*0.55)
        p   = (math.sin(tg*1.4+i*0.85)+1)/2
        a   = int(8+18*p)
        bb  = d.textbbox((0,0), str(i+1), font=FB(sc(34)))
        d.text((px-(bb[2]-bb[0])//2, py-(bb[3]-bb[1])//2), str(i+1), font=FB(sc(34)), fill=(*BLUE,a))

def bg_chat(lay, lt, tg):
    d = ImageDraw.Draw(lay)
    shot, ts, _ = _shot(lt)
    if shot % 2 == 0:
        pan = int(sc(14)*math.sin(ts*0.38))
        for ci in range(2):
            bx = (sc(48)+ci*sc(200)) + pan
            pw, ph = sc(140), sc(265)
            py = H//2-ph//2 + int(sc(18)*math.sin(tg*0.28+ci))
            _panel(d, bx, py, bx+pw, py+ph, sc(12), 32)
            d.rounded_rectangle([bx,py,bx+pw,py+ph], radius=sc(12), outline=(*LBLU,24), width=1)
            my = py+sc(12)
            for mi,(mt,right) in enumerate([("...",False),("Hola!",True),("Precio?",False),("24h activo",True)]):
                prg = clamp((lt-mi*0.45)/0.38)
                if prg<=0: continue
                aa = int(prg*32); mw=sc(86); mh=sc(18)
                mx = bx+(pw-mw-sc(5)) if right else bx+sc(5)
                _bubble(d, mx, my, mw, mh, right, aa, mt, F_TAG)
                my += mh+sc(5)
        # Indicador 24/7
        rx = W-sc(125)+pan; ry = H//2-sc(45)
        _panel(d, rx,ry, rx+sc(95),ry+sc(68), sc(10), 26, DBLU)
        bb = d.textbbox((0,0),"24/7",font=FB(sc(17)))
        d.text((rx+(sc(95)-(bb[2]-bb[0]))//2, ry+sc(10)),"24/7",font=FB(sc(17)),fill=(*LBLU,26))
    else:
        zoom = 1.0+0.05*ts/SHOT_DUR
        pw=int(sc(195)*zoom); ph=int(sc(370)*zoom)
        bx=W//2-pw//2+int(sc(18)*math.sin(ts*0.22)); py=H//2-ph//2
        _panel(d, bx,py,bx+pw,py+ph, sc(14), 28)
        d.rounded_rectangle([bx,py,bx+pw,py+ph], radius=sc(14), outline=(*LBLU,22), width=1)
        msgs=[("Necesito información",False,0.0),("Hola! Soy el bot",True,0.4),
              ("¿Tienes descuentos?",False,0.85),("Sí, 20% hoy",True,1.3),
              ("Perfecto, me apunto",False,1.75),("¡Reserva confirmada!",True,2.2)]
        my=py+sc(18); mh=sc(23)
        for mt,right,delay in msgs:
            prg=clamp((lt-delay-shot*SHOT_DUR)/0.32)
            if prg<=0: continue
            aa=int(prg*30); mw=min(int(len(mt)*sc(5.3)), pw-sc(18))
            mx=bx+pw-mw-sc(7) if right else bx+sc(7)
            _bubble(d,mx,my,mw,mh,right,aa,mt,F_TAG)
            my+=mh+sc(7)

def bg_email(lay, lt, tg):
    d = ImageDraw.Draw(lay); cx = W//2
    shot, ts, _ = _shot(lt)
    if shot % 2 == 0:
        pan = int(sc(9)*math.sin(ts*0.32))
        stages=[("LEAD",BLUE),("EMAIL 1",LBLU),("EMAIL 2",LBLU),("CLIENTE",GREEN)]
        bw,bh=sc(125),sc(30); sy0=H//2-sc(115)+pan
        for i,(lbl,col) in enumerate(stages):
            sy=sy0+i*sc(68); prg=clamp((lt-i*0.28)/0.38); aa=int(prg*26)
            if aa<=0: continue
            _panel(d, cx-bw//2,sy, cx+bw//2,sy+bh, sc(6), aa, col)
            bb=d.textbbox((0,0),lbl,font=F_TAG)
            d.text((cx-(bb[2]-bb[0])//2, sy+(bh-(bb[3]-bb[1]))//2),lbl,font=F_TAG,fill=(*WHITE,min(aa*2,75)))
            if i<len(stages)-1:
                ay1=sy+bh+sc(2); ay2=sy+sc(64)
                d.line([(cx,ay1),(cx,ay2-sc(5))],fill=(*LBLU,int(prg*18)),width=sc(2))
                d.polygon([(cx,ay2),(cx-sc(5),ay2-sc(9)),(cx+sc(5),ay2-sc(9))],fill=(*LBLU,int(prg*18)))
        for ei in range(5):
            ph2=(tg*0.48+ei*0.85)%3.2
            ex=int(W*(ph2/3.2))-sc(38); ey=H//2+sc(125)+int(sc(28)*math.sin(ph2*3.14))
            ea=int(17*math.sin(ph2/3.2*3.14))
            if ea>0:
                ew,eh2=sc(30),sc(20)
                d.rectangle([ex,ey,ex+ew,ey+eh2],fill=(*BLUE,ea))
                d.line([(ex,ey),(ex+ew//2,ey+eh2//2),(ex+ew,ey)],fill=(*LBLU,ea),width=1)
    else:
        pan=int(sc(11)*math.cos(ts*0.28))
        metrics=[("Apertura","68%",LBLU),("Clicks","34%",GREEN),("Conversión","18%",AMBER)]
        bw2=sc(68); gap2=sc(28); mx0=W//2-(3*bw2+2*gap2)//2+pan
        for i,(nm,val,col) in enumerate(metrics):
            bx2=mx0+i*(bw2+gap2); by0=H//2+sc(55)
            p=clamp((lt-i*0.45-shot*SHOT_DUR)/0.55); aa=int(p*26)
            if aa<=0: continue
            bh2=int(sc(95)*p)
            _panel(d, bx2,by0-bh2,bx2+bw2,by0, sc(4), aa, BLUE)
            bb=d.textbbox((0,0),val,font=F_TAG)
            d.text((bx2+(bw2-(bb[2]-bb[0]))//2,by0-bh2-sc(13)),val,font=F_TAG,fill=(*col,min(aa*2,65)))
            bb2=d.textbbox((0,0),nm,font=F_TAG)
            d.text((bx2+(bw2-(bb2[2]-bb2[0]))//2,by0+sc(5)),nm,font=F_TAG,fill=(*GRAY,aa//2))

def bg_social(lay, lt, tg):
    d = ImageDraw.Draw(lay)
    shot, ts, _ = _shot(lt)
    if shot % 2 == 0:
        pan=int(sc(7)*math.sin(ts*0.38))
        cell=sc(75); gap=sc(9)
        gx0=W//2-(3*(cell+gap))//2+gap//2+pan; gy0=H//2-(4*(cell+gap))//2+gap//2
        for r2 in range(4):
            for c2 in range(3):
                delay=(r2*3+c2)*0.16; prog=clamp((lt-delay)/0.32)
                if prog<=0: continue
                aa=int(prog*20)
                gx2=gx0+c2*(cell+gap); gy2=gy0+r2*(cell+gap)
                col=DBLU if (r2+c2)%2==0 else DGRAY
                rr(d,[gx2,gy2,gx2+cell,gy2+cell],sc(6),fill=(*col,aa))
                lv=int((r2*3+c2+1)*912*min(prog,1.0))
                d.text((gx2+sc(4),gy2+cell-sc(14)),f"♥ {lv}",font=F_TAG,fill=(*RED,aa))
    else:
        pan=int(sc(9)*math.sin(ts*0.32)); cx=W//2
        days=["L","M","X","J","V","S","D"]
        cw=sc(68); sx=cx-len(days)*cw//2
        hy=H//2-sc(125)+pan
        for di,day in enumerate(days):
            dx=sx+di*cw; bb=d.textbbox((0,0),day,font=F_TAG)
            d.text((dx+(cw-(bb[2]-bb[0]))//2,hy),day,font=F_TAG,fill=(*GRAY,16))
        sched=[(0,0),(0,2),(1,1),(1,4),(2,0),(2,3),(2,6),(3,1),(3,5),(4,2),(4,4)]
        for wk,di in sched:
            if di>=len(days): continue
            p=clamp((lt-(wk*7+di)*0.11-shot*SHOT_DUR)/0.28)
            if p<=0: continue
            aa=int(p*26); ch=sc(22)
            cxc=sx+di*cw+cw//2; cyc=hy+sc(18)+wk*(ch+sc(7))
            rr(d,[cxc-sc(20),cyc,cxc+sc(20),cyc+ch],sc(4),fill=(*BLUE,aa))
        fc=int(12340*min(lt/4.0,1.0)**0.5)
        bb=d.textbbox((0,0),f"↑ {fc:,} seguidores",font=F_TAG)
        cy2=H//2+sc(175)+pan; aa2=int(min(lt/2.0,1.0)*20)
        d.text((cx-(bb[2]-bb[0])//2,cy2),f"↑ {fc:,} seguidores",font=F_TAG,fill=(*GREEN,aa2))

def bg_invoice(lay, lt, tg):
    d = ImageDraw.Draw(lay)
    shot, ts, _ = _shot(lt)
    if shot % 2 == 0:
        pan=int(sc(11)*math.sin(ts*0.38))
        offsets=[(-sc(22),0),(sc(10),sc(10)),(-sc(5),sc(20)),(sc(18),sc(30))]
        for i,(ox,oy) in enumerate(offsets):
            bx=W//2-sc(88)+ox+pan; by=H//2-sc(115)+oy
            bw2,bh2=sc(155),sc(195)
            p=clamp((lt-i*0.28)/0.38); aa=int(p*18)
            if aa<=0: continue
            rr(d,[bx,by,bx+bw2,by+bh2],sc(6),fill=(*DGRAY,aa),outline=(*LBLU,aa//2),ow=1)
            for li in range(5):
                ly=by+sc(26)+li*sc(26); lw3=bw2-sc(18)-(li%2)*sc(22)
                d.line([(bx+sc(9),ly),(bx+sc(9)+lw3,ly)],fill=(*GRAY,aa),width=1)
            amounts=["1.250€","890€","2.100€","640€"]
            bb=d.textbbox((0,0),amounts[i],font=F_TAG)
            d.text((bx+bw2-sc(38),by+bh2-sc(20)),amounts[i],font=F_TAG,fill=(*GREEN,aa))
        for ci in range(3):
            p2=clamp((lt-ci*0.55-1.0)/0.28)
            if p2<=0: continue
            aa2=int(p2*32); cr=sc(15)
            cx2=W//4*(ci+1)+pan//2; cy2=H//2+sc(95)
            d.ellipse([cx2-cr,cy2-cr,cx2+cr,cy2+cr],fill=(*GREEN,aa2))
            bb=d.textbbox((0,0),"✓",font=FB(sc(12)))
            d.text((cx2-(bb[2]-bb[0])//2,cy2-(bb[3]-bb[1])//2),"✓",font=FB(sc(12)),fill=(*WHITE,aa2))
    else:
        pan=int(sc(7)*math.cos(ts*0.28))
        bw2,bh2=sc(215),sc(290); bx=W//2-bw2//2+pan; by=H//2-bh2//2
        prg=clamp(ts/0.48); aa=int(prg*22)
        rr(d,[bx,by,bx+bw2,by+bh2],sc(8),fill=(*DGRAY,aa),outline=(*LBLU,aa//2),ow=1)
        for li in range(7):
            ly=by+sc(38)+li*sc(30); lw3=bw2-sc(22)-(li%3)*sc(18)
            d.line([(bx+sc(11),ly),(bx+sc(11)+lw3,ly)],fill=(*GRAY,aa),width=1)
        d.line([(bx+sc(11),by+bh2-sc(52)),(bx+bw2-sc(11),by+bh2-sc(52))],fill=(*LBLU,aa),width=2)
        bb=d.textbbox((0,0),"TOTAL: 2.850€",font=FB(sc(10)))
        d.text((bx+bw2-sc(11)-(bb[2]-bb[0]),by+bh2-sc(42)),"TOTAL: 2.850€",font=FB(sc(10)),fill=(*WHITE,aa))
        sp2=clamp((ts-1.5)/0.38)
        if sp2>0:
            sa=int(sp2*28); sw2=sc(88); sh2=sc(32)
            scx=bx+bw2//2+sc(28); scy=by+bh2//2
            rr(d,[scx-sw2//2,scy-sh2//2,scx+sw2//2,scy+sh2//2],sc(5),outline=(*GREEN,sa),ow=3)
            bb2=d.textbbox((0,0),"PAGADO",font=FB(sc(13)))
            d.text((scx-(bb2[2]-bb2[0])//2,scy-(bb2[3]-bb2[1])//2),"PAGADO",font=FB(sc(13)),fill=(*GREEN,sa))

def bg_chart(lay, lt, tg):
    d = ImageDraw.Draw(lay)
    shot, ts, _ = _shot(lt)
    if shot % 2 == 0:
        pan=int(sc(9)*math.sin(ts*0.32))
        kpis=[("CTR","4.8%",LBLU),("ROI","320%",GREEN),("CPC","0.42€",AMBER),("Conv.","18%",TEAL)]
        cw2=sc(112); ch2=sc(62); kx0=W//2-(4*cw2+3*sc(10))//2+pan; ky0=H//2-sc(155)
        for i,(nm,val,col) in enumerate(kpis):
            p=clamp((lt-i*0.22)/0.38); aa=int(p*26)
            kx=kx0+i*(cw2+sc(10))
            _panel(d,kx,ky0,kx+cw2,ky0+ch2,sc(8),aa,DGRAY)
            bb=d.textbbox((0,0),val,font=FB(sc(12)))
            d.text((kx+(cw2-(bb[2]-bb[0]))//2,ky0+sc(9)),val,font=FB(sc(12)),fill=(*col,aa))
            bb2=d.textbbox((0,0),nm,font=F_TAG)
            d.text((kx+(cw2-(bb2[2]-bb2[0]))//2,ky0+sc(32)),nm,font=F_TAG,fill=(*GRAY,aa))
        cy2=ky0+ch2+sc(28); ch3=sc(95); cw3=W-sc(75); cx0=sc(38)+pan//2
        d.line([(cx0,cy2+ch3),(cx0+cw3,cy2+ch3)],fill=(*GRAY,18),width=1)
        n=12; pts=[0.3,0.35,0.4,0.42,0.38,0.5,0.6,0.65,0.72,0.78,0.82,0.95]
        drawn=[]
        for pi in range(n):
            p2=clamp((lt-pi*0.14)/0.28)
            if p2<=0: continue
            aa2=int(p2*22)
            px2=cx0+int(pi/(n-1)*cw3); py2=cy2+ch3-int(pts[pi]*ch3)
            drawn.append((px2,py2,aa2))
        for i in range(1,len(drawn)):
            d.line([drawn[i-1][:2],drawn[i][:2]],fill=(*LBLU,drawn[i][2]),width=sc(2))
            rp=sc(3); d.ellipse([drawn[i][0]-rp,drawn[i][1]-rp,drawn[i][0]+rp,drawn[i][1]+rp],fill=(*LBLU,drawn[i][2]))
    else:
        pan=int(sc(9)*math.cos(ts*0.38))
        bars=[("Ene",0.4),("Feb",0.5),("Mar",0.62),("Abr",0.55),("May",0.78),("Jun",0.95)]
        bw2=sc(62); gap2=sc(18); tot=len(bars)*(bw2+gap2)
        bx0=W//2-tot//2+pan; by0=H//2+sc(58)
        for i,(lbl,hr) in enumerate(bars):
            p=clamp((lt-i*0.18-shot*SHOT_DUR)/0.45); aa=int(p*28)
            if aa<=0: continue
            bh2=int(sc(195)*hr*p); bx2=bx0+i*(bw2+gap2); by2=by0-bh2
            rr(d,[bx2,by2,bx2+bw2,by0],sc(4),fill=(*BLUE,aa))
            d.rectangle([bx2,by2,bx2+bw2,by2+sc(4)],fill=(*LBLU,aa))
            bb=d.textbbox((0,0),lbl,font=F_TAG)
            d.text((bx2+(bw2-(bb[2]-bb[0]))//2,by0+sc(5)),lbl,font=F_TAG,fill=(*GRAY,aa))
            pct=f"+{int(hr*100)}%"
            bb2=d.textbbox((0,0),pct,font=F_TAG)
            d.text((bx2+(bw2-(bb2[2]-bb2[0]))//2,by2-sc(15)),pct,font=F_TAG,fill=(*GREEN,aa))

def bg_cta(lay, lt, tg):
    d = ImageDraw.Draw(lay); cx,cy = W//2,H//2
    for ring in range(8):
        ph=(lt*0.55+ring*0.48)%3.8
        aa=int(18*max(0,1-ph/3.8))
        ri=int(sc(35)+ph*sc(265))
        d.ellipse([cx-ri,cy-ri,cx+ri,cy+ri],outline=(*BLUE,aa),width=sc(3))
    rng2=random.Random(99)
    for pi in range(35):
        ang=rng2.random()*2*math.pi+tg*0.18
        dist=rng2.random()*sc(360)*min(lt/2.0,1.0)
        px2=cx+int(dist*math.cos(ang)); py2=cy+int(dist*math.sin(ang))
        pr=sc(2)+int(sc(3)*rng2.random())
        pulse=(math.sin(tg*1.8+pi)+1)/2
        pa=int((12+22*pulse)*min(lt/1.5,1.0))
        cols=[BLUE,LBLU,WHITE]
        d.ellipse([px2-pr,py2-pr,px2+pr,py2+pr],fill=(*cols[pi%3],pa))

BG_FNS={"intro":bg_intro,"chat":bg_chat,"email":bg_email,
        "social":bg_social,"invoice":bg_invoice,"chart":bg_chart,"cta":bg_cta}

# ── Iconos (foreground) ───────────────────────────────────────────────────────
def _icon_chat(d, cx, cy, sz, lt):
    t = lt % 2.2
    bw,bh = int(sz*0.82),int(sz*0.55)
    x0=cx-bw//2; y0=cy-bh//2
    d.rounded_rectangle([x0,y0,x0+bw,y0+bh],radius=sc(12),fill=(*BLUE,230))
    d.polygon([(x0+sc(22),y0+bh),(x0+sc(8),y0+bh+sc(16)),(x0+sc(38),y0+bh)],fill=(*BLUE,230))
    for i,dx in enumerate([cx-sc(20),cx,cx+sc(20)]):
        beat=(math.sin(t*math.pi*2.8-i*1.1)+1)/2
        dy2=int(sc(5)*beat); dr=sc(6)
        d.ellipse([dx-dr,cy-dr-dy2,dx+dr,cy+dr-dy2],fill=(*WHITE,225))

def _icon_email(d, cx, cy, sz, lt):
    ew,eh=int(sz*0.80),int(sz*0.54)
    x0=cx-ew//2; y0=cy-eh//2
    d.rounded_rectangle([x0,y0,x0+ew,y0+eh],radius=sc(6),fill=(*DGRAY,225),outline=(*LBLU,200),width=sc(2))
    d.polygon([(x0,y0),(cx,cy-sc(5)),(x0+ew,y0)],fill=(*LBLU,65))
    d.line([(x0,y0),(cx,cy-sc(5)),(x0+ew,y0)],fill=(*LBLU,180),width=sc(2))
    for i in range(3):
        delay=i*0.22; prg=clamp((lt-delay)/0.38)
        if prg<=0: continue
        ax=x0+ew+sc(12)+int(sc(30)*prg); ay=cy+(i-1)*sc(16)
        aa=int(220*prg*(1-max(0,prg-0.72)/0.28))
        al=sc(18); d.line([(ax,ay),(ax+al,ay)],fill=(*LBLU,aa),width=sc(3))
        d.polygon([(ax+al,ay),(ax+al-sc(7),ay-sc(5)),(ax+al-sc(7),ay+sc(5))],fill=(*LBLU,aa))

def _icon_social(d, cx, cy, sz, lt):
    pw,ph=int(sz*0.48),int(sz*0.80)
    x0=cx-pw//2; y0=cy-ph//2
    d.rounded_rectangle([x0,y0,x0+pw,y0+ph],radius=sc(10),fill=(*DGRAY,225),outline=(*LBLU,175),width=sc(2))
    sx=x0+sc(5); sy=y0+sc(11); sw=pw-sc(10); ih=int((ph-sc(22))*0.53)
    aa=int(255*clamp(lt/0.48))
    d.rectangle([sx,sy,sx+sw,sy+ih],fill=(*DBLU,aa))
    mx=sx+sw//2; my=sy+ih//2
    d.polygon([(mx-sc(8),my-sc(10)),(mx-sc(8),my+sc(10)),(mx+sc(10),my)],fill=(*LBLU,aa))
    lv=int(1234*clamp((lt-0.3)/0.6)**0.7) if lt>0.3 else 0
    al2=int(255*clamp((lt-0.3)/0.28))
    d.text((sx+sc(4),sy+ih+sc(5)),f"♥ {lv:,}",font=F_TAG,fill=(*RED,al2))

def _icon_invoice(d, cx, cy, sz, lt):
    dw,dh=int(sz*0.66),int(sz*0.80)
    x0=cx-dw//2; y0=cy-dh//2; fold=sc(18)
    d.polygon([(x0,y0),(x0+dw-fold,y0),(x0+dw,y0+fold),(x0+dw,y0+dh),(x0,y0+dh)],fill=(*DGRAY,225))
    d.polygon([(x0+dw-fold,y0),(x0+dw,y0+fold),(x0+dw-fold,y0+fold)],fill=(*BLUE,175))
    d.polygon([(x0,y0),(x0+dw-fold,y0),(x0+dw,y0+fold),(x0+dw,y0+dh),(x0,y0+dh)],outline=(*LBLU,155),width=sc(2))
    for i,fy in enumerate([0.25,0.40,0.55,0.68]):
        aa=int(215*clamp((lt-i*0.11)/0.22))
        lx2=x0+dw-sc(9)-(sc(15)*(i%2))
        d.line([(x0+sc(9),y0+int(dh*fy)),(lx2,y0+int(dh*fy))],fill=(*GRAY,aa),width=sc(2))
    aa_ck=int(255*clamp((lt-0.45)/0.38))
    if aa_ck>0:
        cr=sc(16); ccx=x0+dw-sc(4); ccy=y0+dh-sc(6)
        d.ellipse([ccx-cr,ccy-cr,ccx+cr,ccy+cr],fill=(*GREEN,aa_ck))
        prg=clamp((lt-0.45)/0.48)
        p1=(ccx-sc(8),ccy); p2=(ccx-sc(2),ccy+sc(7)); p3=(ccx+sc(9),ccy-sc(8))
        d.line([p1,p2],fill=(255,255,255,aa_ck),width=sc(3))
        if prg>0.5: d.line([p2,p3],fill=(255,255,255,int(aa_ck*(prg*2-1))),width=sc(3))

def _icon_chart(d, cx, cy, sz, lt):
    ch=int(sz*0.70); cw=int(sz*0.85)
    x0=cx-cw//2; yb=cy+ch//2
    hs=[0.42,0.60,0.76,0.54,0.95]
    bw2=int(cw/(len(hs)*1.55)); gap2=int((cw-bw2*len(hs))/(len(hs)+1))
    for i,rh in enumerate(hs):
        prg=clamp((lt-i*0.11)/0.42); aa=int(215*prg); bh2=int(ch*rh*prg)
        bx2=x0+gap2+i*(bw2+gap2); by2=yb-bh2
        col=BLUE if i<len(hs)-1 else LBLU
        d.rectangle([bx2,by2,bx2+bw2,yb],fill=(*col,aa))
        d.rectangle([bx2,by2,bx2+bw2,by2+sc(3)],fill=(*WHITE,aa//2))
        aa2=int(215*clamp((lt-i*0.11-0.28)/0.22))
        if aa2>0:
            pct=f"{int(rh*100)}%"
            bb=d.textbbox((0,0),pct,font=F_TAG)
            d.text((bx2+(bw2-(bb[2]-bb[0]))//2,by2-sc(14)),pct,font=F_TAG,fill=(*WHITE,aa2))
    d.line([(x0,yb),(x0+cw,yb)],fill=(*GRAY,155),width=sc(2))

def _icon_intro(d, cx, cy, sz, lt):
    aa=int(215*clamp(lt/0.38))
    # Tres puntos suspensivos + ?
    bb=d.textbbox((0,0),"?",font=FB(sc(78)))
    pulse=1.0+0.04*math.sin(lt*3.5)
    # Draw scaled by pulse (approximate)
    bsz=int(sc(78)*pulse)
    bb2=d.textbbox((0,0),"?",font=FB(bsz))
    d.text((cx-(bb2[2]-bb2[0])//2, cy-(bb2[3]-bb2[1])//2),"?",font=FB(bsz),fill=(*LBLU,aa))

def _icon_cta(img, cx, cy, sz, lt):
    aa=int(255*clamp(lt/0.55))
    target_w=int(sz*1.55)
    limg=_load_logo(target_w)
    lx=cx-limg.width//2; ly=cy-limg.height//2
    lay=new_layer()
    lay.paste(limg,(lx,ly),limg)
    r2,g2,b2,a2=lay.split()
    a2m=a2.point(lambda p: int(p*aa/255))
    lay.putalpha(a2m)
    composite(img,lay)

ICON_FNS={"intro":_icon_intro,"chat":_icon_chat,"email":_icon_email,
          "social":_icon_social,"invoice":_icon_invoice,"chart":_icon_chart}

# ── Número watermark ───────────────────────────────────────────────────────────
def draw_num_watermark(img, label, lt):
    if not label: return
    aa=int(18*clamp(lt/0.45))
    d=ImageDraw.Draw(img)
    bb=d.textbbox((0,0),label,font=F_NUMWM)
    x=W//2-(bb[2]-bb[0])//2; y=CARD_T+sc(8)
    d.text((x,y),label,font=F_NUMWM,fill=(*LBLU,aa))

# ── Progress pips ─────────────────────────────────────────────────────────────
def draw_progress_pips(img, scene_idx, lt):
    """5 pips estilo iOS: punto activo = pastilla blanca, inactivos = gris pequeños."""
    # Solo para escenas s1-s5 (idx 1-5)
    if scene_idx < 1 or scene_idx > 5: return

    active = scene_idx - 1   # 0-4
    aa = int(220 * clamp(lt / 0.35))
    if aa == 0: return

    pip_r    = sc(5)    # radio de punto inactivo
    pip_pill = sc(18)   # mitad-ancho de la pastilla activa
    pip_h    = sc(5)    # alto de la pastilla
    gap      = sc(14)   # separación entre pips
    n        = 5

    # Calcular ancho total para centrar
    widths = []
    for i in range(n):
        widths.append(pip_pill*2 if i==active else pip_r*2)
    total_w = sum(widths) + gap*(n-1)
    x = W//2 - total_w//2

    layer = new_layer()
    d = ImageDraw.Draw(layer)
    for i in range(n):
        w_i = widths[i]
        cy  = PIP_CY
        if i == active:
            # pastilla blanca (spring animation del ancho)
            spring_w = int(pip_pill * (1.0 + 0.08 * math.sin(lt * 8) * max(0, 0.3-lt)/0.3))
            d.rounded_rectangle([x, cy-pip_h, x+spring_w*2, cy+pip_h],
                                 radius=pip_h, fill=(*WHITE, aa))
            x += spring_w * 2 + gap
        else:
            # punto gris
            cx_pip = x + pip_r
            d.ellipse([cx_pip-pip_r, cy-pip_r, cx_pip+pip_r, cy+pip_r],
                      fill=(*GRAY, aa // 2))
            x += pip_r*2 + gap
    composite(img, layer)

# ── Cabecera ──────────────────────────────────────────────────────────────────
def draw_header(img):
    """Barra blanca con logo PNG real, sin transparencia variable."""
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    d.rectangle([0, 0, W, HDR_H], fill=(255, 255, 255, 238))
    lx = (W - LOGO_IMG.width) // 2
    ly = (HDR_H - LOGO_IMG.height) // 2
    layer.paste(LOGO_IMG, (lx, ly), LOGO_IMG)
    composite(img, layer)

# ── Render de escena ──────────────────────────────────────────────────────────
CROSS_DUR = 0.42  # segundos de crossfade en entrada de escena

def render_scene(img, scene_idx, lt, tg, scene_times_ext):
    """Renders la escena completa sobre `img` (RGB)."""
    sid, label, title, chip_txt, bg_type = SCENE_DEFS[scene_idx]
    cx = W // 2

    # Duración de escena (para exit fade)
    if scene_idx < len(scene_times_ext) - 1:
        s_dur = (scene_times_ext[scene_idx+1] - scene_times_ext[scene_idx]) / 1000
    else:
        s_dur = 999.0

    # Alpha de entrada (spring) y salida (ease-out)
    enter_f = _spring(clamp(lt / CROSS_DUR))
    exit_f  = _eo(clamp((s_dur - lt) / 0.35)) if lt > s_dur - 0.5 else 1.0
    alpha_f = min(enter_f, exit_f)

    # ── Fondo animado
    bg_lay = new_layer()
    BG_FNS.get(bg_type, bg_intro)(bg_lay, lt, tg)
    # Fade in del fondo con spring
    r2,g2,b2,a2=bg_lay.split()
    a2m=a2.point(lambda p: int(p*alpha_f))
    bg_lay.putalpha(a2m)
    composite(img, bg_lay)

    # ── Número watermark
    draw_num_watermark(img, label, lt)

    # ── Glass card (icon container) con spring-slide desde abajo
    slide_y = int(sc(55) * (1.0 - _spring(clamp(lt / 0.5))))
    card_t  = CARD_T + slide_y
    card_b  = CARD_B + slide_y
    card_aa = int(alpha_f * 255)
    if card_aa > 5:
        glass_rect(img, CARD_L, card_t, CARD_R_X, card_b,
                   radius=sc(22), blur=12,
                   fill=(255, 255, 255, int(12*alpha_f)),
                   border=(255, 255, 255, int(38*alpha_f)))

    # ── Icono dentro de la card
    icon_cy = (card_t + card_b) // 2
    icon_sz = int((card_b - card_t) * 0.50)
    glow(img, cx, icon_cy, icon_sz // 2,
         SCENE_ACCENT[scene_idx % len(SCENE_ACCENT)], peak=int(35 * alpha_f))
    d = ImageDraw.Draw(img)
    if bg_type == "cta":
        _icon_cta(img, cx, icon_cy, icon_sz, lt)
        d = ImageDraw.Draw(img)
    elif bg_type in ICON_FNS:
        ICON_FNS[bg_type](d, cx, icon_cy, icon_sz, lt)

    # ── Título (spring desde abajo, delay 0.05s)
    title_slide = int(sc(45) * (1.0 - _spring(clamp((lt - 0.06) / 0.52))))
    title_aa    = int(alpha_f * 255)
    ty = TITLE_Y + title_slide
    d  = ImageDraw.Draw(img)
    for line in title.split('\n'):
        bb = d.textbbox((0,0), line, font=F_TITLE)
        lh = bb[3] - bb[1]
        d.text((cx-(bb[2]-bb[0])//2, ty), line, font=F_TITLE, fill=(*WHITE, title_aa))
        ty += lh + sc(4)

    # ── Description chip (spring desde abajo, delay 0.14s)
    chip_slide = int(sc(38) * (1.0 - _spring(clamp((lt - 0.14) / 0.48))))
    chip_aa    = int(alpha_f * 220)
    chip_y     = CHIP_Y + chip_slide
    if chip_aa > 10 and chip_txt:
        bb = d.textbbox((0,0), chip_txt, font=F_CHIP)
        cw = bb[2]-bb[0]; ch = bb[3]-bb[1]
        pw2 = cw + sc(28); ph2 = ch + sc(14)
        glass_rect(img, cx-pw2//2, chip_y, cx+pw2//2, chip_y+ph2,
                   radius=ph2//2, blur=8,
                   fill=(255,255,255,int(8*alpha_f)),
                   border=(255,255,255,int(28*alpha_f)))
        d = ImageDraw.Draw(img)
        d.text((cx-cw//2, chip_y+sc(7)), chip_txt, font=F_CHIP, fill=(*LGRAY, chip_aa))

# ── Karaoke ───────────────────────────────────────────────────────────────────
def render_karaoke(img, sentences, t_ms):
    if not sentences: return
    active = None
    for sent in sentences:
        if sent['start_ms'] <= t_ms <= sent['start_ms']+sent['dur_ms']+500:
            active = sent; break
    if active is None:
        for sent in reversed(sentences):
            if t_ms > sent['start_ms']:
                active = sent; break
    if active is None: return

    words = active['words']

    # Glass bar con blur real
    glass_rect(img, sc(12), KARA_T, W-sc(12), KARA_B,
               radius=sc(18), blur=14,
               fill=(0, 0, 0, 175),
               border=(255, 255, 255, 28))

    d = ImageDraw.Draw(img)
    max_lw = (W - sc(12)*2) - sc(48)

    # Layout en líneas
    lines = [[]]
    lw_acc = 0
    for wi, wo in enumerate(words):
        is_cur = wo['start_ms'] <= t_ms < wo['start_ms']+wo['duration_ms']+60
        f = F_SUB_H if is_cur else F_SUB_N
        bb = d.textbbox((0,0), wo['word']+' ', font=f)
        ww = bb[2]-bb[0]
        if lw_acc+ww > max_lw and lines[-1]:
            lines.append([]); lw_acc = 0
        lines[-1].append(wi); lw_acc += ww

    cur_line = 0
    for li, idxs in enumerate(lines):
        for wi in idxs:
            wo = words[wi]
            if wo['start_ms'] <= t_ms < wo['start_ms']+wo['duration_ms']+60:
                cur_line = li
    disp = lines[max(0, cur_line-1):cur_line+2]

    line_h  = sc(40)
    tot_h   = len(disp) * line_h
    y_start = KARA_T + (KARA_H - tot_h) // 2

    for idxs in disp:
        # Calcular ancho total de línea
        lw_tot = 0
        for wi in idxs:
            wo  = words[wi]
            isc = wo['start_ms'] <= t_ms < wo['start_ms']+wo['duration_ms']+60
            f   = F_SUB_H if isc else F_SUB_N
            bb  = d.textbbox((0,0), wo['word']+' ', font=f)
            lw_tot += bb[2]-bb[0]
        x = W//2 - lw_tot//2

        for wi in idxs:
            wo   = words[wi]
            isc  = wo['start_ms'] <= t_ms < wo['start_ms']+wo['duration_ms']+60
            past = wo['start_ms']+wo['duration_ms'] < t_ms

            if isc:
                f = F_SUB_H; col = LBLU
                bb = d.textbbox((0,0), wo['word'], font=f)
                ww = bb[2]-bb[0]; wh = bb[3]-bb[1]
                hl = new_layer()
                dhl = ImageDraw.Draw(hl)
                dhl.rounded_rectangle([x-sc(4), y_start-sc(3),
                                        x+ww+sc(4), y_start+wh+sc(3)],
                                       radius=sc(5), fill=(*BLUE, 70))
                composite(img, hl)
                d = ImageDraw.Draw(img)
            elif past:
                f = F_SUB_P; col = WHITE
            else:
                f = F_SUB_N; col = GRAY

            bb = d.textbbox((0,0), wo['word']+' ', font=f)
            d.text((x, y_start), wo['word'], font=f, fill=col)
            x += bb[2]-bb[0]
        y_start += line_h

# ── URL bar ───────────────────────────────────────────────────────────────────
def draw_url(img):
    d = ImageDraw.Draw(img)
    url = "blastudios.vercel.app"
    bb  = d.textbbox((0,0), url, font=F_TAG)
    d.text((W//2-(bb[2]-bb[0])//2, URL_Y), url, font=F_TAG, fill=(*GRAY, 180))

# ── Audio ─────────────────────────────────────────────────────────────────────
async def generate_audio():
    print("Generando audio...")
    communicate = edge_tts.Communicate(SCRIPT, voice=VOICE, rate="+5%")
    raw_sents=[]; audio_chunks=[]
    async for chunk in communicate.stream():
        if chunk["type"]=="audio": audio_chunks.append(chunk["data"])
        elif chunk["type"]=="SentenceBoundary":
            raw_sents.append({"text":chunk["text"],
                               "start_ms":chunk["offset"]/10000,
                               "dur_ms":chunk["duration"]/10000})
    audio_bytes=b"".join(audio_chunks)
    with open(TMP_A,"wb") as f: f.write(audio_bytes)
    print(f"  Audio: {len(audio_bytes)//1024} KB, {len(raw_sents)} oraciones")

    sentences=[]; flat_words=[]
    for sent in raw_sents:
        rw=sent["text"].split()
        if not rw: continue
        total_ch=sum(max(1,len(w.strip("¿?.,;:!\"'()"))) for w in rw)
        cursor=sent["start_ms"]+20; eff=max(0,sent["dur_ms"]-40)
        sw=[]
        for w in rw:
            cl=w.strip("¿?.,;:!\"'()"); ch=max(1,len(cl))
            wd=eff*ch/total_ch
            e={"word":w,"start_ms":cursor,"duration_ms":wd}
            sw.append(e); flat_words.append(e); cursor+=wd
        sentences.append({"text":sent["text"],"start_ms":sent["start_ms"],
                           "dur_ms":sent["dur_ms"],"words":sw})
    print(f"  Palabras: {len(flat_words)}")
    return flat_words, sentences

# ── Scene timing ──────────────────────────────────────────────────────────────
def compute_scene_times(flat_words):
    nc=0; m=[False]*7; ss=[None]*7
    for w in flat_words:
        wt=w["word"].strip("¿?.,;:!\"'()")
        if not m[0] and wt=="Sabes":
            ss[0]=max(0,w["start_ms"]-100); m[0]=True
        if wt=="Número" and nc<5:
            si=nc+1
            if not m[si]: ss[si]=w["start_ms"]; m[si]=True
            nc+=1
        if not m[6] and wt=="Blastudios":
            ss[6]=w["start_ms"]; m[6]=True
    last_ms=flat_words[-1]["start_ms"]+flat_words[-1]["duration_ms"]
    for i in range(7):
        if ss[i] is None: ss[i]=last_ms*i/7
    return ss

# ── Render loop ───────────────────────────────────────────────────────────────
def render_video(flat_words, sentences, total_ms):
    total_frames = int(math.ceil(total_ms/1000*FPS)) + FPS
    print(f"\nRenderizando {total_frames} frames ({total_ms/1000:.1f}s)...")

    scene_times = compute_scene_times(flat_words)
    print(f"  Escenas (ms): {[int(x) for x in scene_times]}")
    ste = list(scene_times) + [total_ms + 5000]

    writer = imageio.get_writer(
        TMP_V, fps=FPS, codec='libx264', quality=None, bitrate='20M',
        output_params=['-preset','slow','-crf','16','-pix_fmt','yuv420p']
    )
    t0 = time.time()

    for fi in range(total_frames):
        t_ms = fi / FPS * 1000
        tg   = t_ms / 1000

        # Scene index
        si = 0
        for k in range(len(ste)-1):
            if k < len(SCENE_DEFS) and t_ms >= ste[k]: si = k
        si  = min(si, len(SCENE_DEFS)-1)
        lt  = (t_ms - ste[si]) / 1000

        # ── Frame base ──
        img = Image.new('RGB', (W,H), BG)
        draw_bg_base(img, si, lt, tg)
        render_scene(img, si, lt, tg, ste)
        render_karaoke(img, sentences, t_ms)
        draw_progress_pips(img, si, lt)
        draw_header(img)
        draw_url(img)

        writer.append_data(np.array(img))

        if fi % 60 == 0:
            el  = time.time()-t0
            eta = el/max(fi,1)*(total_frames-fi)
            print(f"  {fi+1}/{total_frames} ({(fi+1)/total_frames*100:.0f}%) ETA {eta:.0f}s", end='\r')

    writer.close()
    print(f"\n  Video: {TMP_V}")

# ── Combine ───────────────────────────────────────────────────────────────────
def combine_av():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    print("Combinando audio + video...")
    r = subprocess.run(
        [ff,'-y','-i',TMP_V,'-i',TMP_A,
         '-c:v','copy','-c:a','aac','-b:a','192k','-shortest',OUT],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("FFMPEG error:", r.stderr[-400:]); raise RuntimeError("ffmpeg failed")
    print(f"  Reel: {OUT}  ({os.path.getsize(OUT)/1024/1024:.1f} MB)")

def cleanup():
    for f in [TMP_V, TMP_A]:
        try:
            if os.path.exists(f): os.remove(f)
        except: pass

# ── Entry ─────────────────────────────────────────────────────────────────────
async def main():
    os.makedirs(DIR, exist_ok=True)
    flat_words, sentences = await generate_audio()
    if not flat_words: print("ERROR: sin palabras"); return
    last = flat_words[-1]
    total_ms = last["start_ms"]+last["duration_ms"]+1000
    print(f"  Duracion: {total_ms/1000:.1f}s")
    render_video(flat_words, sentences, total_ms)
    combine_av()
    cleanup()
    print("LISTO:", OUT)

if __name__ == "__main__":
    asyncio.run(main())