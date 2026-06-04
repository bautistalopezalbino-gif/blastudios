#!/usr/bin/env python3
"""
Reel BLASTUDIOS — "La Evolucion de la IA"
390x692  |  30fps  |  50s  |  Sin audio (anadir en CapCut)

Escenas:
  S0  0- 5s  HOOK      "Tu competencia ya no usa ChatGPT. Usa agentes."
  S1  5-17s  PROBLEMA  "IA sin sistema != ROI"
  S2 17-33s  EVOLUCION Las 4 etapas de la IA
  S3 33-46s  SOLUCION  BLASTUDIOS + checklist
  S4 46-50s  CTA       "Escribenos IA por DM"
"""

import os, math, time, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

# ── CONFIG ──────────────────────────────────────────────────────────────
W, H    = 390, 692
FPS     = 30
DUR     = 50
FRAMES  = FPS * DUR
OUT     = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram\reel_evolucion_ia.mp4"
FD      = r"C:\Windows\Fonts"
CX      = W // 2    # 195
CY      = H // 2    # 346

# ── COLORES ─────────────────────────────────────────────────────────────
BG    = (  8,   9,  14)
BLUE  = ( 37,  99, 235)
LBLU  = ( 96, 165, 250)
DBLU  = ( 13,  27,  62)
WHITE = (248, 250, 252)
LGRAY = (160, 165, 185)
GRAY  = ( 98, 105, 128)
GREEN = ( 34, 197,  94)
RED   = (220,  50,  47)

# ── FUENTES ─────────────────────────────────────────────────────────────
def fnt(name, sz):
    p = os.path.join(FD, name)
    return ImageFont.truetype(p, sz) if os.path.exists(p) else ImageFont.load_default()

FB = lambda s: fnt('segoeuib.ttf', s)
FR = lambda s: fnt('segoeui.ttf',  s)
FL = lambda s: fnt('segoeuil.ttf', s)

# Tamanos calibrados para 390x692
F_HUGE = FB(38)   # hook grande
F_H1   = FB(28)   # titular principal
F_H2   = FB(22)   # subtitular
F_H3   = FB(18)   # medio
F_BD   = FR(13)   # cuerpo
F_SM   = FR(11)   # pequeno
F_TAG  = FB( 9)   # label caps
F_NUM  = FB(48)   # numero watermark

# ── LOGO ────────────────────────────────────────────────────────────────
def make_logo(target_w=260):
    SVG_W, SVG_H = 520.0, 110.0
    s   = target_w / SVG_W
    th  = max(1, int(SVG_H * s))
    R   = 3.0; sc2 = s * R
    rw  = max(1, int(SVG_W * sc2))
    rh  = max(1, int(SVG_H * sc2))
    surf = Image.new('RGBA', (rw, rh), (0, 0, 0, 0))
    d    = ImageDraw.Draw(surf)
    DNAV=(13,31,60); WITE=(255,255,255); BBLUE=(37,99,235)
    d.rounded_rectangle([5*sc2,5*sc2,105*sc2,105*sc2], radius=max(1,int(20*sc2)), fill=DNAV)
    d.rounded_rectangle([30*sc2,17*sc2,42*sc2,93*sc2],  radius=max(1,int(6*sc2)),  fill=WITE)
    cx_, cy_ = 61*sc2, 76*sc2
    d.ellipse([cx_-19*sc2,cy_-19*sc2,cx_+19*sc2,cy_+19*sc2], fill=WITE)
    d.ellipse([cx_-10*sc2,cy_-10*sc2,cx_+10*sc2,cy_+10*sc2], fill=DNAV)
    mfpt = max(10, int(58*sc2))
    fb3=FB(mfpt); fl3=FL(mfpt)
    bb = d.textbbox((0,0),"bla",font=fb3)
    bla_w=bb[2]-bb[0]
    tx_,by_=int(125*sc2),int(78*sc2)
    d.text((tx_,      by_),"bla",     font=fb3,fill=DNAV,anchor="ls")
    d.text((tx_+bla_w,by_),"studios", font=fl3,fill=DNAV,anchor="ls")
    tfpt=max(6,int(13*sc2))
    d.text((int(127*sc2),int(100*sc2)),"DIGITAL MARKETING AGENCY",
           font=FB(tfpt),fill=BBLUE,anchor="ls")
    return surf.resize((target_w, th), Image.LANCZOS)

LOGO   = make_logo(260)
LOGO_W = LOGO.width
LOGO_H = LOGO.height

# Starfield fijo
_RNG  = random.Random(42)
STARS = [(_RNG.randint(0,W),_RNG.randint(0,H),_RNG.random()) for _ in range(70)]

# ── MATH ─────────────────────────────────────────────────────────────────
def _c(v): return max(0.0, min(1.0, float(v)))
def eo(t):  return 1-(1-_c(t))**3
def eio(t): t=_c(t); return t*t*(3-2*t)
def lerp(a,b,t): return a+(b-a)*_c(t)
def fade(s,d,t): return _c((t-s)/d) if d>0 else (1.0 if t>=s else 0.0)

def spring(t, start=0.0, dur=0.5):
    t=_c((t-start)/dur)
    if t<=0: return 0.0
    if t>=1: return 1.0
    omega=22.0; zeta=0.52
    od=omega*math.sqrt(max(0,1-zeta**2))
    val=1-math.exp(-zeta*omega*t)*(
        math.cos(od*t)+(zeta/math.sqrt(max(1e-9,1-zeta**2)))*math.sin(od*t))
    return max(0.0, val)

# ── DRAW HELPERS ─────────────────────────────────────────────────────────
def _tw(d,txt,f):  b=d.textbbox((0,0),txt,font=f); return b[2]-b[0]
def _th(d,txt,f):  b=d.textbbox((0,0),txt,font=f); return b[3]-b[1]
def _cx(d,txt,f):  return (W-_tw(d,txt,f))//2

def wrap(d,txt,f,maxw):
    words=txt.split(); lines,cur=[],""
    for w in words:
        test=(cur+" "+w).strip()
        if _tw(d,test,f)<=maxw: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines or [txt]

def otxt(img,pos,txt,font,col,a=1.0):
    if a<=0.01: return img
    lay=Image.new('RGBA',img.size,(0,0,0,0))
    ImageDraw.Draw(lay).text(pos,txt,font=font,fill=(*col[:3],int(a*255)))
    return Image.alpha_composite(img.convert('RGBA'),lay).convert('RGB')

def gtxt(img,pos,txt,font,col,gcol=None,gr=8,a=1.0):
    if a<=0.01: return img
    if gcol is None: gcol=col
    gl=Image.new('RGBA',img.size,(0,0,0,0))
    ImageDraw.Draw(gl).text(pos,txt,font=font,fill=(*gcol[:3],int(a*75)))
    gl=gl.filter(ImageFilter.GaussianBlur(gr))
    base=Image.alpha_composite(img.convert('RGBA'),gl)
    return otxt(base.convert('RGB'),pos,txt,font,col,a)

def glass(img,x,y,w,h,r=14,ba=0.42,oa=0.22):
    surf=Image.new('RGBA',(w,h),(0,0,0,0))
    ImageDraw.Draw(surf).rounded_rectangle([0,0,w-1,h-1],radius=r,
        fill=(*DBLU,int(ba*255)),outline=(*BLUE,int(oa*255)),width=1)
    base=img.convert('RGBA'); base.paste(surf,(x,y),surf)
    return base.convert('RGB')

def glow_rect(img,x0,y0,x1,y1,col,a=25,blur=14):
    lay=Image.new('RGBA',(W,H),(0,0,0,0))
    ImageDraw.Draw(lay).rounded_rectangle([x0,y0,x1,y1],radius=16,fill=(*col[:3],a))
    lay=lay.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img.convert('RGBA'),lay).convert('RGB')

def orb(img,x,y,rad,col,s=0.28):
    sz=rad*2
    o=Image.new('RGBA',(sz,sz),(0,0,0,0))
    od=ImageDraw.Draw(o)
    for r in range(rad,0,max(1,rad//18)):
        a=int(s*255*((1-r/rad)**0.55))
        od.ellipse([rad-r,rad-r,rad+r,rad+r],fill=(*col[:3],a))
    o=o.filter(ImageFilter.GaussianBlur(rad//4))
    base=img.convert('RGBA')
    px,py=x-rad,y-rad
    ox2,oy2,ow2,oh2=0,0,sz,sz
    if px<0:     ox2=-px; ow2=sz+px; px=0
    if py<0:     oy2=-py; oh2=sz+py; py=0
    if px+ow2>W: ow2=W-px
    if py+oh2>H: oh2=H-py
    if ow2>0 and oh2>0:
        crop=o.crop([ox2,oy2,ox2+ow2,oy2+oh2])
        base.paste(crop,(px,py),crop)
    return base.convert('RGB')

# ── BACKGROUND ───────────────────────────────────────────────────────────
def draw_bg(t,accent=BLUE):
    img=Image.new('RGB',(W,H),BG)
    p1=math.sin(t*0.65)*16
    p2=math.cos(t*0.48)*13
    img=orb(img,-10+int(p1),-20,190,accent,0.22)
    img=orb(img,W+10+int(p2),H-10,160,BLUE,0.16)
    img=orb(img,CX,CY+int(p1*0.4),145,DBLU,0.25)
    lay=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(lay)
    for sx,sy,br in STARS:
        p=(math.sin(t*0.6+br*6.28)+1)/2
        a=int(100*(0.06+0.20*br*p))
        r2=1 if br<0.55 else 2
        d.ellipse([sx-r2,sy-r2,sx+r2,sy+r2],fill=(*WHITE,a))
    return Image.alpha_composite(img.convert('RGBA'),lay).convert('RGB')

def draw_progress(img,t):
    d=ImageDraw.Draw(img)
    bw=int(W*min(t/DUR,1.0))
    if bw>0:
        d.rectangle([0,0,bw,3],fill=BLUE)
        if bw<W:
            d.rectangle([max(0,bw-5),0,bw+1,3],fill=(130,170,255))
    return img

def draw_header(img,a=1.0):
    if a<0.01: return img
    BAR_H=58
    lay=Image.new('RGBA',(W,BAR_H),(0,0,0,0))
    d=ImageDraw.Draw(lay)
    d.rectangle([0,0,W,BAR_H],fill=(0,0,0,int(a*210)))
    lx=(W-LOGO_W)//2; ly=(BAR_H-LOGO_H)//2
    lay.paste(LOGO,(lx,ly),LOGO)
    base=img.convert('RGBA')
    merged=base.copy(); merged.paste(lay,(0,0),lay)
    return merged.convert('RGB')

# ── BADGE helper ─────────────────────────────────────────────────────────
def badge(img,text,y,a,col=BLUE,text_col=WHITE):
    d=ImageDraw.Draw(img)
    tw=_tw(d,text,F_TAG)+18
    bx=(W-tw)//2
    surf=Image.new('RGBA',(tw,26),(0,0,0,0))
    sd=ImageDraw.Draw(surf)
    sd.rounded_rectangle([0,0,tw-1,25],radius=13,
        fill=(*col[:3],int(a*72)),outline=(*col[:3],int(a*150)),width=1)
    sd.text((9,8),text,font=F_TAG,fill=(*text_col[:3],int(a*220)))
    base=img.convert('RGBA'); base.paste(surf,(bx,y),surf)
    return base.convert('RGB')

# ═══════════════════════════════════════════════════════════════════════════
# ESCENAS
# ═══════════════════════════════════════════════════════════════════════════

# ── S0: HOOK  0-5s ──────────────────────────────────────────────────────
def s0(img, lt):
    d=ImageDraw.Draw(img)

    # Badge "2025 · AI UPDATE"
    a_b=spring(lt,0.05,0.38)
    if a_b>0:
        img=badge(img,"  2025 · AI UPDATE  ",72,a_b)
        d=ImageDraw.Draw(img)

    # "Tu competencia / ya no usa"
    a1=spring(lt,0.12,0.46)
    yo1=int(lerp(24,0,spring(lt,0.12,0.46)))
    if a1>0:
        for i,ln in enumerate(["Tu competencia","ya no usa"]):
            lx=_cx(d,ln,F_H1)
            img=gtxt(img,(lx,136+i*38+yo1),ln,F_H1,WHITE,BLUE,10,a1)
            d=ImageDraw.Draw(img)

    # "ChatGPT" con tachado
    a2=spring(lt,0.38,0.42)
    if a2>0:
        txt="ChatGPT"
        lx=_cx(d,txt,F_HUGE)
        ty=226
        yo2=int(lerp(16,0,spring(lt,0.38,0.42)))
        img=gtxt(img,(lx,ty+yo2),txt,F_HUGE,GRAY,GRAY,7,a2*0.65)
        d=ImageDraw.Draw(img)
        mid_y=ty+yo2+_th(d,txt,F_HUGE)//2
        x2=lx+_tw(d,txt,F_HUGE)
        d.line([(lx,mid_y),(x2,mid_y)],fill=(*BLUE,int(a2*230)),width=4)

    # "Usa agentes." en azul
    a3=spring(lt,0.65,0.46)
    if a3>0:
        txt="Usa agentes."
        lx=_cx(d,txt,F_HUGE)
        ty2=296
        yo3=int(lerp(16,0,spring(lt,0.65,0.46)))
        img=glow_rect(img,18,ty2+yo3-6,W-18,ty2+yo3+_th(d,txt,F_HUGE)+6,BLUE,24,14)
        img=gtxt(img,(lx,ty2+yo3),txt,F_HUGE,BLUE,LBLU,14,a3)
        d=ImageDraw.Draw(img)

    # Sublinea
    a4=spring(lt,0.84,0.38)
    if a4>0:
        ln="La IA evolucionó. ¿Y tú?"
        lx=_cx(d,ln,F_BD)
        d.text((lx,360),ln,font=F_BD,fill=(*LGRAY,int(a4*170)))

    return img

# ── S1: PROBLEMA  5-17s (lt=0..12) ──────────────────────────────────────
def s1(img, lt):
    PAD=20
    d=ImageDraw.Draw(img)

    # Badge rojo
    a_b=spring(lt,0.05,0.34)
    if a_b>0:
        img=badge(img,"  EL PROBLEMA  ",72,a_b,RED)
        d=ImageDraw.Draw(img)

    # Card 1: la situacion
    cy1=100; ch1=192
    a_c1=spring(lt,0.08,0.42)
    yo1=int(lerp(24,0,spring(lt,0.08,0.42)))
    if a_c1>0:
        img=glass(img,PAD,cy1+yo1,W-PAD*2,ch1,r=16,ba=0.44*a_c1,oa=0.24*a_c1)
        d=ImageDraw.Draw(img)

        # "Muchas empresas / probaron la IA."
        a_t1=spring(lt,0.16,0.30)
        if a_t1>0:
            for i,ln in enumerate(["Muchas empresas","probaron la IA."]):
                lx=_cx(d,ln,F_H2)
                img=gtxt(img,(lx,cy1+yo1+14+i*34),ln,F_H2,WHITE,BLUE,9,a_t1)
                d=ImageDraw.Draw(img)

        # Subtexto
        a_t2=spring(lt,0.38,0.30)
        if a_t2>0:
            for i,ln in enumerate(["Escribieron prompts.","Obtuvieron respuestas."]):
                lx=_cx(d,ln,F_BD)
                d.text((lx,cy1+yo1+98+i*22),ln,font=F_BD,fill=(*LGRAY,int(a_t2*180)))

        # "Pero no resultados." en rojo
        a_t3=spring(lt,0.58,0.36)
        if a_t3>0:
            ln="Pero no resultados."
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,cy1+yo1+152),ln,F_H2,RED,RED,10,a_t3)
            d=ImageDraw.Draw(img)

    # Card 2: la ecuacion
    cy2=308; ch2=76
    a_c2=spring(lt,0.65,0.42)
    yo2=int(lerp(18,0,spring(lt,0.65,0.42)))
    if a_c2>0:
        img=glow_rect(img,PAD-8,cy2+yo2-8,W-PAD+8,cy2+yo2+ch2+8,BLUE,int(a_c2*28),14)
        img=glass(img,PAD,cy2+yo2,W-PAD*2,ch2,r=14,ba=0.52*a_c2,oa=0.32*a_c2)
        d=ImageDraw.Draw(img)
        # Dos lineas para que quepa
        for i,(ln,col) in enumerate([("IA sin sistema",LGRAY),("no genera ROI.",BLUE)]):
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,cy2+yo2+10+i*32),ln,F_H2,col,BLUE,9,a_c2)
            d=ImageDraw.Draw(img)

    # Subtitulo
    a_sub=spring(lt,0.82,0.36)
    if a_sub>0:
        ln="Solo genera frustracion."
        lx=_cx(d,ln,F_BD)
        d.text((lx,cy2+ch2+16),ln,font=F_BD,fill=(*LGRAY,int(a_sub*165)))

    return img

# ── S2: EVOLUCION  17-33s (lt=0..16) ────────────────────────────────────
ETAPAS=[
    ("01","CHATBOTS",          "Respondian preguntas.",          LGRAY, 0.08),
    ("02","AUTOMATIZACIONES",  "Ejecutaban tareas.",              LGRAY, 0.26),
    ("03","AGENTES IA",        "Piensan. Actuan. Deciden.",       LBLU,  0.48),
    ("04","EQUIPOS AGENTES",   "Trabajan solos. Sin ti. 24/7.",   BLUE,  0.70),
]
_CH  = 82    # alto de cada card
_GAP = 9     # espacio entre cards
_PAD = 20

def s2(img, lt):
    d=ImageDraw.Draw(img)

    # Titulo seccion
    a_ttl=spring(lt,0.03,0.36)
    if a_ttl>0:
        ttl="LAS 4 ETAPAS DE LA IA"
        lx=_cx(d,ttl,F_TAG)
        d.text((lx,72),ttl,font=F_TAG,fill=(*BLUE,int(a_ttl*230)))

    total_h=len(ETAPAS)*_CH+(len(ETAPAS)-1)*_GAP
    start_y=CY-total_h//2+28   # 346-195+28 = 179

    for i,(num,label,desc,col,delay) in enumerate(ETAPAS):
        a=spring(lt,delay,0.42)
        if a<=0.01: continue
        cy=start_y+i*(_CH+_GAP)
        yo=int(lerp(20,0,spring(lt,delay,0.42)))
        is_last=(i==3)

        if is_last and a>0.3:
            img=glow_rect(img,_PAD-5,cy+yo-5,W-_PAD+5,cy+yo+_CH+5,BLUE,int(a*30),12)

        ba=(0.54 if is_last else 0.38)*a
        oa=(0.36 if is_last else 0.18)*a
        img=glass(img,_PAD,cy+yo,W-_PAD*2,_CH,r=13,ba=ba,oa=oa)
        d=ImageDraw.Draw(img)

        # Numero watermark (fondo)
        d.text((_PAD+6,cy+yo+4),num,font=F_NUM,fill=(*col[:3],int(a*35)))

        # Label y desc
        a_l=spring(lt,delay+0.08,0.26)
        if a_l>0:
            d.text((_PAD+68,cy+yo+14),label,font=F_H3,fill=(*col[:3],int(a_l*228)))

        a_d=spring(lt,delay+0.18,0.26)
        if a_d>0:
            d.text((_PAD+68,cy+yo+48),desc,font=F_BD,fill=(*LGRAY,int(a_d*180)))

        # Flecha conectora (excepto la ultima)
        if i<len(ETAPAS)-1:
            a_arr=spring(lt,delay+0.24,0.26)
            if a_arr>0:
                y1=cy+yo+_CH+2; y2=y1+_GAP-3
                d.line([(CX,y1),(CX,y2-7)],fill=(*BLUE,int(a_arr*110)),width=2)
                d.polygon([(CX,y2),(CX-7,y2-10),(CX+7,y2-10)],
                          fill=(*BLUE,int(a_arr*110)))

    return img

# ── S3: SOLUCION BLASTUDIOS  33-46s (lt=0..13) ───────────────────────────
PUNTOS=[
    ("Agentes captan y califican leads",  0.18),
    ("Workflows cierran ventas solas",     0.36),
    ("Operaciones autonomas 24 horas",     0.54),
]

def s3(img, lt):
    PAD=20
    d=ImageDraw.Draw(img)

    # Logo card
    LOGO_CY=82; LOGO_CH=58
    a_lg=spring(lt,0.05,0.46)
    yo_lg=int(lerp(16,0,spring(lt,0.05,0.46)))
    if a_lg>0:
        pulse=0.5+0.5*math.sin(lt*2.1)
        img=glow_rect(img,PAD-10,LOGO_CY+yo_lg-8,W-PAD+10,LOGO_CY+yo_lg+LOGO_CH+8,
                      BLUE,int((0.26+0.10*pulse)*a_lg*28),16)
        card=Image.new('RGBA',(W-PAD*2,LOGO_CH),(0,0,0,0))
        cd=ImageDraw.Draw(card)
        cd.rounded_rectangle([0,0,W-PAD*2-1,LOGO_CH-1],radius=16,
            fill=(255,255,255,int(a_lg*246)),outline=(*BLUE,int(a_lg*90)),width=2)
        lx2=(W-PAD*2-LOGO_W)//2; ly2=(LOGO_CH-LOGO_H)//2
        card.paste(LOGO,(lx2,max(0,ly2)),LOGO)
        base=img.convert('RGBA'); base.paste(card,(PAD,LOGO_CY+yo_lg),card)
        img=base.convert('RGB'); d=ImageDraw.Draw(img)

    # Headline
    head_y=LOGO_CY+LOGO_CH+20
    a_h=spring(lt,0.22,0.38)
    yo_h=int(lerp(12,0,spring(lt,0.22,0.38)))
    if a_h>0:
        for i,(ln,col) in enumerate([("BLASTUDIOS construye",WHITE),("esos sistemas.",BLUE)]):
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,head_y+yo_h+i*34),ln,F_H2,col,BLUE,9,a_h)
            d=ImageDraw.Draw(img)

    # Checklist
    ck_y=head_y+80
    for i,(txt,delay) in enumerate(PUNTOS):
        a=spring(lt,delay,0.38)
        if a<=0.01: continue
        cy=ck_y+i*76; yo=int(lerp(12,0,spring(lt,delay,0.38)))
        img=glass(img,PAD,cy+yo,W-PAD*2,60,r=12,ba=0.44*a,oa=0.22*a)
        d=ImageDraw.Draw(img)

        # Circulo check
        cr=14; ccx=PAD+30; ccy=cy+yo+30
        d.ellipse([ccx-cr,ccy-cr,ccx+cr,ccy+cr],fill=(*BLUE,int(a*210)))

        # Checkmark
        a_ck=spring(lt,delay+0.14,0.22)
        if a_ck>0:
            p1=(ccx-6,ccy); p2=(ccx-1,ccy+6); p3=(ccx+8,ccy-7)
            d.line([p1,p2],fill=(*WHITE,int(a_ck*255)),width=3)
            if a_ck>0.55:
                d.line([p2,p3],fill=(*WHITE,int(min(1,(a_ck-0.5)*2)*255)),width=3)

        # Texto (con wrap)
        a_tx=spring(lt,delay+0.10,0.26)
        if a_tx>0:
            lines=wrap(d,txt,F_H3,W-PAD*2-62)
            for j,ln in enumerate(lines):
                d.text((PAD+54,cy+yo+14+j*22),ln,font=F_H3,
                       fill=(*WHITE,int(a_tx*218)))

    # Tagline
    tag_y=ck_y+len(PUNTOS)*76+12
    a_tag=spring(lt,0.78,0.36)
    if a_tag>0:
        for i,ln in enumerate(['"No es suerte.',  'Es sistema."']):
            lx=_cx(d,ln,F_H3)
            img=gtxt(img,(lx,tag_y+i*26),ln,F_H3,WHITE,BLUE,8,a_tag)
            d=ImageDraw.Draw(img)

    return img

# ── S4: CTA  46-50s (lt=0..4) ────────────────────────────────────────────
def s4(img, lt):
    PAD=20
    d=ImageDraw.Draw(img)

    # Encabezado
    a1=spring(lt,0.05,0.42)
    if a1>0:
        yo1=int(lerp(18,0,spring(lt,0.05,0.42)))
        for i,(ln,col) in enumerate([("Si quieres implementar",WHITE),("IA de verdad,",WHITE)]):
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,108+yo1+i*36),ln,F_H2,col,BLUE,9,a1)
            d=ImageDraw.Draw(img)

    # Boton grande
    BTN_Y=196; BTN_H=56
    a2=spring(lt,0.24,0.46)
    if a2>0:
        yo2=int(lerp(20,0,spring(lt,0.24,0.46)))
        pulse=0.5+0.5*math.sin(lt*3.0)
        gs=int((18+8*pulse)*a2)
        img=glow_rect(img,PAD-gs//2,BTN_Y+yo2-gs//3,W-PAD+gs//2,
                      BTN_Y+yo2+BTN_H+gs//3,BLUE,int(a2*50),gs//2+5)
        d.rounded_rectangle([PAD,BTN_Y+yo2,W-PAD,BTN_Y+yo2+BTN_H],
                             radius=BTN_H//2,fill=(*BLUE,int(a2*238)))
        # "Escribenos  IA"
        p1="Escribenos  "; p2="IA"
        tw1=_tw(d,p1,F_H1); tw2=_tw(d,p2,F_H1)
        tx=CX-(tw1+tw2)//2
        ty=BTN_Y+yo2+(BTN_H-_th(d,p1,F_H1))//2
        d.text((tx,ty),p1,font=F_H1,fill=(*WHITE,int(a2*230)))
        img=gtxt(img,(tx+tw1,ty),p2,F_H1,WHITE,WHITE,8,a2)
        d=ImageDraw.Draw(img)

    # "por DM o comentarios"
    a3=spring(lt,0.46,0.36)
    if a3>0:
        ln="por DM o en comentarios"
        lx=_cx(d,ln,F_BD)
        d.text((lx,BTN_Y+BTN_H+16),ln,font=F_BD,fill=(*LGRAY,int(a3*180)))

    # Online indicator + handle
    a4=spring(lt,0.60,0.36)
    if a4>0:
        hy=BTN_Y+BTN_H+50
        blink=1.0 if (lt*2)%1<0.55 else 0.38
        d.ellipse([CX-90,hy+5,CX-82,hy+13],fill=(*GREEN,int(a4*blink*220)))
        d.text((CX-78,hy+2),"En linea ahora",font=F_SM,fill=(*GREEN,int(a4*210)))
        handle="@blastudios._"
        lx=_cx(d,handle,F_H2)
        img=gtxt(img,(lx,hy+26),handle,F_H2,WHITE,BLUE,9,a4)
        d=ImageDraw.Draw(img)

    # "Te mostramos que automatizas esta semana"
    a5=spring(lt,0.75,0.36)
    if a5>0:
        text="Te mostramos que automatizas esta semana."
        for i,ln in enumerate(wrap(d,text,F_BD,W-40)):
            lx=_cx(d,ln,F_BD)
            d.text((lx,BTN_Y+BTN_H+104+i*22),ln,font=F_BD,
                   fill=(*LGRAY,int(a5*180)))

    return img

# ── TIMELINE & RENDER ───────────────────────────────────────────────────
TIMES   = [(0,5),(5,17),(17,33),(33,46),(46,50)]
SCENES  = [s0, s1, s2, s3, s4]
ACCENTS = [BLUE, RED, LBLU, BLUE, GREEN]
XFADE   = 0.50

def get_scene(t):
    for i,(s,e) in enumerate(TIMES):
        if s<=t<e: return i, t-s
    return len(SCENES)-1, max(0.0, t-TIMES[-1][0])

def render_frame(fi):
    t=fi/FPS
    si,lt=get_scene(t)
    s_start,s_end=TIMES[si]
    base=draw_bg(t,ACCENTS[si%len(ACCENTS)])

    if t-s_start<XFADE:
        fa=eio((t-s_start)/XFADE)
    elif s_end-t<XFADE and si<len(SCENES)-1:
        fa=eio((s_end-t)/XFADE)
    else:
        fa=1.0

    curr=SCENES[si](base.copy(),lt)

    if fa>=0.995:
        result=curr
    elif t-s_start<XFADE and si>0:
        prev_si=si-1
        prev_lt=TIMES[prev_si][1]-TIMES[prev_si][0]-0.001
        prev=SCENES[prev_si](base.copy(),prev_lt)
        result=Image.blend(prev,curr,eio((t-s_start)/XFADE))
    else:
        result=Image.blend(base,curr,fa)

    result=draw_header(result,min(1.0,t*3))
    result=draw_progress(result,t)
    return result

# ── MAIN ────────────────────────────────────────────────────────────────
if __name__=='__main__':
    print("="*56)
    print(" Reel BLASTUDIOS - La Evolucion de la IA")
    print(f" {W}x{H}  |  {FPS}fps  |  {DUR}s  |  {FRAMES} frames")
    print(f" Salida: {OUT}")
    print("="*56)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    writer=imageio_ffmpeg.write_frames(
        OUT,(W,H),fps=FPS,
        codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',bitrate='5M',
        macro_block_size=1,
    )
    writer.send(None)

    t0=time.time()
    for fi in range(FRAMES):
        if fi%FPS==0:
            el=time.time()-t0
            eta=el/max(fi,1)*(FRAMES-fi)
            pct=fi/FRAMES*100
            done=int(pct/5); left=20-done
            bar='#'*done+'-'*left
            msg=f"  [{bar}] {pct:5.1f}%  {fi//FPS:3d}s/{DUR}s  ETA {eta:4.0f}s  "
            sys.stdout.write(msg+'\r'); sys.stdout.flush()
        writer.send(np.array(render_frame(fi)).tobytes())

    writer.close()
    elapsed=time.time()-t0
    mb=os.path.getsize(OUT)/1_048_576
    print(f"\n\n  Completado en {elapsed:.1f}s  -  {mb:.1f} MB")
    print(f"  {OUT}")
