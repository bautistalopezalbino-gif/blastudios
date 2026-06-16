#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reel BLASTUDIOS v2 - La Evolucion de la IA
1080x1920 | 30fps | 55s | BoxBlur (x4 mas rapido que GaussianBlur)

v2: resolucion IG estandar, pips iOS, strikethrough animado,
    flechas animadas en etapas, simetria perfecta, vignette cinematica
"""
import os, math, time, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

# ── CONFIG ──────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
DUR    = 55
FRAMES = FPS * DUR
SCALE  = W / 390.0

def sc(v): return max(1, int(round(v * SCALE)))

OUT = r"c:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\reels instagram\reel_evolucion_ia.mp4"
FD  = r"C:\Windows\Fonts"
CX  = W // 2
CY  = H // 2

HDR_H  = sc(50)
PIP_Y  = HDR_H + sc(22)
PAD    = sc(24)
CW     = W - PAD * 2
SAFE_Y = HDR_H + sc(36)

# ── COLORES ─────────────────────────────────────────────────────────
BG    = (  8,   9,  14)
BLUE  = ( 37,  99, 235)
LBLU  = ( 96, 165, 250)
DBLU  = ( 13,  27,  62)
WHITE = (248, 250, 252)
LGRAY = (160, 165, 185)
GRAY  = ( 98, 105, 128)
GREEN = ( 34, 197,  94)
RED   = (220,  50,  47)

# ── FUENTES ─────────────────────────────────────────────────────────
def fnt(n, s):
    p = os.path.join(FD, n)
    return ImageFont.truetype(p, s) if os.path.exists(p) else ImageFont.load_default()

FB = lambda s: fnt('segoeuib.ttf', s)
FR = lambda s: fnt('segoeui.ttf',  s)
FL = lambda s: fnt('segoeuil.ttf', s)

F_HUGE = FB(sc(43))
F_H1   = FB(sc(30))
F_H2   = FB(sc(23))
F_H3   = FB(sc(18))
F_BD   = FR(sc(14))
F_SM   = FR(sc(11))
F_TAG  = FB(sc(10))
F_NUM  = FB(sc(52))

# ── LOGO ────────────────────────────────────────────────────────────
def make_logo(u=270):
    tw = sc(u)
    SW, SH = 520.0, 110.0
    s = tw/SW; th = max(1, int(SH*s))
    R = 3.0; k = s*R
    rw = max(1, int(SW*k)); rh = max(1, int(SH*k))
    img = Image.new('RGBA', (rw, rh), (0,0,0,0))
    d   = ImageDraw.Draw(img)
    DN=(13,31,60); WH=(255,255,255); BL=(37,99,235)
    d.rounded_rectangle([5*k,5*k,105*k,105*k], radius=max(1,int(20*k)), fill=DN)
    d.rounded_rectangle([30*k,17*k,42*k,93*k],  radius=max(1,int(6*k)),  fill=WH)
    cx_,cy_=61*k,76*k
    d.ellipse([cx_-19*k,cy_-19*k,cx_+19*k,cy_+19*k], fill=WH)
    d.ellipse([cx_-10*k,cy_-10*k,cx_+10*k,cy_+10*k], fill=DN)
    mf=max(10,int(58*k)); fb=FB(mf); fl=FL(mf)
    bb=d.textbbox((0,0),'bla',font=fb); bw=bb[2]-bb[0]
    tx,by=int(125*k),int(78*k)
    d.text((tx,by),'bla',font=fb,fill=DN,anchor='ls')
    d.text((tx+bw,by),'studios',font=fl,fill=DN,anchor='ls')
    tf=max(6,int(13*k))
    d.text((int(127*k),int(100*k)),'DIGITAL MARKETING AGENCY',font=FB(tf),fill=BL,anchor='ls')
    return img.resize((tw,th),Image.LANCZOS)

LOGO   = make_logo(270)
LOGO_W = LOGO.width
LOGO_H = LOGO.height

_RNG  = random.Random(42)
STARS = [(_RNG.randint(0,W), _RNG.randint(0,H), _RNG.random()) for _ in range(90)]

# ── MATH ────────────────────────────────────────────────────────────
def _c(v): return max(0.0, min(1.0, float(v)))
def eo(t): return 1-(1-_c(t))**3
def eio(t): t=_c(t); return t*t*(3-2*t)
def lerp(a,b,t): return a+(b-a)*_c(t)

def spring(t, s=0.0, d=0.50):
    t=_c((t-s)/max(d,1e-4))
    if t<=0: return 0.0
    if t>=1: return 1.0
    omega=22.0; zeta=0.52
    od=omega*math.sqrt(max(0,1-zeta**2))
    v=1-math.exp(-zeta*omega*t)*(
        math.cos(od*t)+(zeta/math.sqrt(max(1e-9,1-zeta**2)))*math.sin(od*t))
    return max(0.0, v)

# ── DRAW HELPERS ────────────────────────────────────────────────────
def _tw(d,t,f): b=d.textbbox((0,0),t,font=f); return b[2]-b[0]
def _th(d,t,f): b=d.textbbox((0,0),t,font=f); return b[3]-b[1]
def _cx(d,t,f): return (W-_tw(d,t,f))//2

def wrap(d,txt,f,mw):
    ws=txt.split(); lines,cur=[],''
    for w in ws:
        t2=(cur+' '+w).strip()
        if _tw(d,t2,f)<=mw: cur=t2
        else:
            if cur: lines.append(cur); cur=w
            else: lines.append(w)
    if cur: lines.append(cur)
    return lines or [txt]

def _nl(): return Image.new('RGBA',(W,H),(0,0,0,0))

def _cp(img,lay):
    return Image.alpha_composite(img.convert('RGBA'),lay).convert('RGB')

def otxt(img,pos,txt,font,col,a=1.0):
    if a<=0.01: return img
    lay=_nl(); ImageDraw.Draw(lay).text(pos,txt,font=font,fill=(*col[:3],int(a*255)))
    return _cp(img,lay)

def gtxt(img,pos,txt,font,col,gc=None,gr=None,a=1.0):
    if a<=0.01: return img
    if gc is None: gc=BLUE
    if gr is None: gr=sc(7)
    gl=_nl(); ImageDraw.Draw(gl).text(pos,txt,font=font,fill=(*gc[:3],int(a*70)))
    gl=gl.filter(ImageFilter.BoxBlur(gr))
    return otxt(_cp(img,gl),pos,txt,font,col,a)

def glass(img,x,y,w,h,r=None,ba=0.42,oa=0.22,ac=None):
    if r  is None: r =sc(16)
    if ac is None: ac=BLUE
    s=Image.new('RGBA',(w,h),(0,0,0,0))
    ImageDraw.Draw(s).rounded_rectangle([0,0,w-1,h-1],radius=r,
        fill=(*DBLU,int(ba*255)),outline=(*ac,int(oa*255)),width=max(1,sc(1)))
    b=img.convert('RGBA'); b.paste(s,(x,y),s)
    return b.convert('RGB')

def glow_rect(img,x0,y0,x1,y1,col,st=28,layers=4):
    lay=_nl(); d=ImageDraw.Draw(lay)
    for i in range(layers,0,-1):
        e=i*sc(5); a=int(st*(i/layers)**1.8)
        d.rounded_rectangle([x0-e,y0-e,x1+e,y1+e],radius=sc(16)+e,fill=(*col[:3],a))
    return _cp(img,lay)

def orb(img,x,y,rad,col,st=0.24):
    sz=rad*2
    o=Image.new('RGBA',(sz,sz),(0,0,0,0)); od=ImageDraw.Draw(o)
    for r in range(rad,0,max(1,rad//18)):
        a=int(st*255*((1-r/rad)**0.55))
        od.ellipse([rad-r,rad-r,rad+r,rad+r],fill=(*col[:3],a))
    o=o.filter(ImageFilter.BoxBlur(max(1,rad//5)))
    b=img.convert('RGBA')
    px,py=x-rad,y-rad
    ox,oy,ow,oh=0,0,sz,sz
    if px<0:     ox=-px; ow=sz+px; px=0
    if py<0:     oy=-py; oh=sz+py; py=0
    if px+ow>W:  ow=W-px
    if py+oh>H:  oh=H-py
    if ow>0 and oh>0:
        b.paste(o.crop([ox,oy,ox+ow,oy+oh]),(px,py),o.crop([ox,oy,ox+ow,oy+oh]))
    return b.convert('RGB')

# ── VIGNETTE pre-calculada ───────────────────────────────────────────
def _make_vignette():
    lay=_nl(); d=ImageDraw.Draw(lay)
    for i in range(18,0,-1):
        px=int(W*i/36); py=int(H*i/36)
        a=int(55*(i/18)**2)
        d.ellipse([px,py,W-px,H-py],fill=(0,0,0,a))
    return lay.filter(ImageFilter.BoxBlur(sc(25)))

VIGNETTE = _make_vignette()

# ── BACKGROUND ──────────────────────────────────────────────────────
def draw_bg(t, acc=BLUE):
    img=Image.new('RGB',(W,H),BG)
    p1=math.sin(t*0.65)*sc(15); p2=math.cos(t*0.48)*sc(12)
    img=orb(img,int(sc(-10)+p1),int(sc(-20)),sc(185),acc,0.19)
    img=orb(img,int(W+sc(8)+p2),int(H-sc(8)),sc(160),BLUE,0.14)
    img=orb(img,CX,int(CY+p1*0.4),sc(138),DBLU,0.21)
    lay=_nl(); d=ImageDraw.Draw(lay)
    for sx,sy,br in STARS:
        p=(math.sin(t*0.6+br*6.28)+1)/2
        a=int(80*(0.06+0.18*br*p))
        r2=max(1,sc(1)) if br<0.55 else max(1,sc(2))
        d.ellipse([sx-r2,sy-r2,sx+r2,sy+r2],fill=(*WHITE,a))
    img=_cp(img,lay)
    return _cp(img,VIGNETTE)

# ── CHROME ──────────────────────────────────────────────────────────
def draw_header(img,a=1.0):
    if a<0.01: return img
    lay=Image.new('RGBA',(W,HDR_H),(0,0,0,0))
    d=ImageDraw.Draw(lay); d.rectangle([0,0,W,HDR_H],fill=(0,0,0,int(a*218)))
    lay.paste(LOGO,((W-LOGO_W)//2,(HDR_H-LOGO_H)//2),LOGO)
    b=img.convert('RGBA'); m=b.copy(); m.paste(lay,(0,0),lay)
    return m.convert('RGB')

def draw_pips(img,si,lt):
    n=5; pr=sc(4); ppw=sc(18); ph=sc(4); gap=sc(12)
    aa=int(192*_c(lt/0.30))
    if aa==0: return img
    ws=[ppw*2 if i==si else pr*2 for i in range(n)]
    tw_=sum(ws)+gap*(n-1); x=CX-tw_//2
    lay=_nl(); d=ImageDraw.Draw(lay)
    for i in range(n):
        if i==si:
            d.rounded_rectangle([x,PIP_Y-ph,x+ppw*2,PIP_Y+ph],radius=ph,fill=(*WHITE,aa))
            x+=ppw*2+gap
        else:
            c=x+pr; d.ellipse([c-pr,PIP_Y-pr,c+pr,PIP_Y+pr],fill=(*GRAY,aa//2))
            x+=pr*2+gap
    return _cp(img,lay)

def draw_progress(img,t):
    d=ImageDraw.Draw(img); bw=int(W*min(t/DUR,1.0))
    if bw>0:
        d.rectangle([0,0,bw,sc(3)],fill=BLUE)
        if bw<W: d.rectangle([max(0,bw-sc(4)),0,bw+sc(1),sc(3)],fill=(130,170,255))
    return img

def draw_handle(img,a=1.0):
    if a<0.01: return img
    d=ImageDraw.Draw(img); txt='@blastudios._'
    d.text((_cx(d,txt,F_SM),H-sc(22)),txt,font=F_SM,fill=(*LGRAY,int(a*115)))
    return img

def draw_badge(img,text,y,a,col=BLUE):
    d=ImageDraw.Draw(img)
    tw_=_tw(d,text,F_TAG)+sc(20); bh=sc(30)
    bx=(W-tw_)//2
    s=Image.new('RGBA',(tw_,bh),(0,0,0,0)); sd=ImageDraw.Draw(s)
    sd.rounded_rectangle([0,0,tw_-1,bh-1],radius=bh//2,
        fill=(*col[:3],int(a*62)),outline=(*col[:3],int(a*138)),width=max(1,sc(1)))
    sd.text((sc(10),sc(9)),text,font=F_TAG,fill=(*WHITE,int(a*208)))
    b=img.convert('RGBA'); b.paste(s,(bx,y),s)
    return b.convert('RGB')

# ════════════════════════════════════════════════════════════════════
# ESCENAS
# ════════════════════════════════════════════════════════════════════

# S0 — HOOK  0-6s ────────────────────────────────────────────────────
def s0(img,lt):
    d=ImageDraw.Draw(img)
    a_b=spring(lt,0.05,0.34)
    if a_b>0:
        img=draw_badge(img,'  2025 · AI UPDATE  ',SAFE_Y+sc(4),a_b); d=ImageDraw.Draw(img)

    a1=spring(lt,0.12,0.44); yo1=int(lerp(sc(22),0,spring(lt,0.12,0.44)))
    if a1>0:
        for i,ln in enumerate(['Tu competencia','ya no usa']):
            lx=_cx(d,ln,F_H1)
            img=gtxt(img,(lx,CY-sc(132)+i*sc(42)+yo1),ln,F_H1,WHITE,BLUE,sc(9),a1)
            d=ImageDraw.Draw(img)

    a2=spring(lt,0.35,0.40); yo2=int(lerp(sc(14),0,spring(lt,0.35,0.40)))
    if a2>0:
        txt='ChatGPT'; lx=_cx(d,txt,F_HUGE); ty=CY-sc(46)
        img=gtxt(img,(lx,ty+yo2),txt,F_HUGE,GRAY,GRAY,sc(6),a2*0.58); d=ImageDraw.Draw(img)
        a_s=spring(lt,0.52,0.28)
        if a_s>0:
            mid_y=ty+yo2+_th(d,txt,F_HUGE)//2
            x2=lx+int(_tw(d,txt,F_HUGE)*a_s)
            d.line([(lx,mid_y),(x2,mid_y)],fill=(*BLUE,int(a2*238)),width=sc(4))

    a3=spring(lt,0.64,0.44); yo3=int(lerp(sc(14),0,spring(lt,0.64,0.44)))
    if a3>0:
        txt='Usa agentes.'; lx=_cx(d,txt,F_HUGE); ty2=CY+sc(30)
        img=glow_rect(img,PAD,ty2+yo3-sc(8),W-PAD,ty2+yo3+_th(d,txt,F_HUGE)+sc(8),BLUE,int(a3*24))
        img=gtxt(img,(lx,ty2+yo3),txt,F_HUGE,BLUE,LBLU,sc(14),a3); d=ImageDraw.Draw(img)

    a4=spring(lt,0.82,0.34)
    if a4>0:
        ln='La IA evoluciono. Y tu?'; lx=_cx(d,ln,F_BD)
        d.text((lx,CY+sc(100)),ln,font=F_BD,fill=(*LGRAY,int(a4*158)))
    return img

# S1 — PROBLEMA  6-18s ───────────────────────────────────────────────
def s1(img,lt):
    d=ImageDraw.Draw(img)
    a_b=spring(lt,0.05,0.32)
    if a_b>0:
        img=draw_badge(img,'  EL PROBLEMA  ',SAFE_Y+sc(4),a_b,RED); d=ImageDraw.Draw(img)

    cy1=SAFE_Y+sc(42); ch1=sc(198)
    a_c1=spring(lt,0.08,0.42); yo_c=int(lerp(sc(22),0,spring(lt,0.08,0.42)))
    if a_c1>0:
        img=glass(img,PAD,cy1+yo_c,CW,ch1,r=sc(16),ba=0.44*a_c1,oa=0.24*a_c1); d=ImageDraw.Draw(img)
        a_t1=spring(lt,0.16,0.30)
        if a_t1>0:
            for i,ln in enumerate(['Muchas empresas','probaron la IA.']):
                lx=_cx(d,ln,F_H2)
                img=gtxt(img,(lx,cy1+yo_c+sc(14)+i*sc(36)),ln,F_H2,WHITE,BLUE,sc(8),a_t1)
                d=ImageDraw.Draw(img)
        a_t2=spring(lt,0.36,0.28)
        if a_t2>0:
            for i,ln in enumerate(['Escribieron prompts.','Obtuvieron respuestas.']):
                lx=_cx(d,ln,F_BD)
                d.text((lx,cy1+yo_c+sc(104)+i*sc(24)),ln,font=F_BD,fill=(*LGRAY,int(a_t2*175)))
        a_t3=spring(lt,0.56,0.34)
        if a_t3>0:
            ln='Pero no resultados.'; lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,cy1+yo_c+sc(160)),ln,F_H2,RED,RED,sc(9),a_t3); d=ImageDraw.Draw(img)

    cy2=cy1+ch1+sc(14); ch2=sc(88)
    a_c2=spring(lt,0.65,0.42); yo_c2=int(lerp(sc(18),0,spring(lt,0.65,0.42)))
    if a_c2>0:
        img=glow_rect(img,PAD-sc(8),cy2+yo_c2-sc(8),W-PAD+sc(8),cy2+yo_c2+ch2+sc(8),BLUE,int(a_c2*25))
        img=glass(img,PAD,cy2+yo_c2,CW,ch2,r=sc(14),ba=0.52*a_c2,oa=0.32*a_c2); d=ImageDraw.Draw(img)
        for i,(ln,col) in enumerate([('IA sin sistema',LGRAY),('no genera ROI.',BLUE)]):
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,cy2+yo_c2+sc(10)+i*sc(36)),ln,F_H2,col,BLUE,sc(9),a_c2)
            d=ImageDraw.Draw(img)

    a_s=spring(lt,0.82,0.32)
    if a_s>0:
        ln='Solo genera frustracion.'; lx=_cx(d,ln,F_BD)
        d.text((lx,cy2+ch2+sc(14)),ln,font=F_BD,fill=(*LGRAY,int(a_s*160)))
    return img

# S2 — EVOLUCION  18-34s ─────────────────────────────────────────────
ETAPAS=[
    ('01','CHATBOTS',           'Respondian preguntas.',         LGRAY, 0.08),
    ('02','AUTOMATIZACIONES',   'Ejecutaban tareas.',             LGRAY, 0.26),
    ('03','AGENTES IA',         'Piensan. Actuan. Deciden.',      LBLU,  0.48),
    ('04','EQUIPOS DE AGENTES', 'Trabajan solos. Sin ti. 24/7.', BLUE,  0.70),
]
_CH=sc(90); _GAP=sc(10); _TOT=4*_CH+3*_GAP

def s2(img,lt):
    d=ImageDraw.Draw(img)
    a_ttl=spring(lt,0.03,0.32)
    start_y=CY-_TOT//2+sc(24)
    if a_ttl>0:
        ttl='LAS 4 ETAPAS DE LA IA'; lx=_cx(d,ttl,F_TAG)
        d.text((lx,start_y-sc(38)),ttl,font=F_TAG,fill=(*BLUE,int(a_ttl*225)))

    for i,(num,label,desc,col,delay) in enumerate(ETAPAS):
        a=spring(lt,delay,0.42)
        if a<=0.01: continue
        cy=start_y+i*(_CH+_GAP); yo=int(lerp(sc(20),0,spring(lt,delay,0.42)))
        is_last=(i==3)
        if is_last and a>0.22:
            img=glow_rect(img,PAD-sc(7),cy+yo-sc(7),W-PAD+sc(7),cy+yo+_CH+sc(7),BLUE,int(a*30))
        img=glass(img,PAD,cy+yo,CW,_CH,r=sc(14),
                  ba=(0.54 if is_last else 0.38)*a,
                  oa=(0.36 if is_last else 0.18)*a, ac=col)
        d=ImageDraw.Draw(img)
        d.text((PAD+sc(8),cy+yo+sc(4)),num,font=F_NUM,fill=(*col[:3],int(a*32)))
        a_l=spring(lt,delay+0.08,0.26)
        if a_l>0:
            d.text((PAD+sc(78),cy+yo+sc(14)),label,font=F_H3,fill=(*col[:3],int(a_l*222)))
        a_d=spring(lt,delay+0.18,0.26)
        if a_d>0:
            d.text((PAD+sc(78),cy+yo+sc(54)),desc,font=F_BD,fill=(*LGRAY,int(a_d*175)))
        if i<3:
            a_arr=spring(lt,delay+0.26,0.26)
            if a_arr>0:
                ax=CX; y1=cy+yo+_CH+sc(1); y2=y1+_GAP-sc(2)
                seg=int((y2-y1-sc(9))*a_arr)
                d.line([(ax,y1),(ax,min(y1+seg,y2-sc(9)))],fill=(*BLUE,int(a_arr*100)),width=max(1,sc(2)))
                if a_arr>0.82:
                    tip=int((a_arr-0.82)/0.18*100)
                    d.polygon([(ax,y2),(ax-sc(7),y2-sc(10)),(ax+sc(7),y2-sc(10))],fill=(*BLUE,tip))
    return img

# S3 — SOLUCION  34-47s ──────────────────────────────────────────────
PUNTOS=[
    ('Agentes captan y califican leads',  0.18),
    ('Workflows cierran ventas solas',    0.36),
    ('Operaciones autonomas 24 horas',    0.54),
]

def s3(img,lt):
    d=ImageDraw.Draw(img)
    LC_Y=SAFE_Y+sc(8); LC_H=sc(64)
    a_lg=spring(lt,0.05,0.46); yo_lg=int(lerp(sc(16),0,spring(lt,0.05,0.46)))
    if a_lg>0:
        pulse=0.5+0.5*math.sin(lt*2.1)
        img=glow_rect(img,PAD-sc(10),LC_Y+yo_lg-sc(8),W-PAD+sc(10),LC_Y+yo_lg+LC_H+sc(8),
                      BLUE,int((0.24+0.10*pulse)*a_lg*28))
        card=Image.new('RGBA',(CW,LC_H),(0,0,0,0)); cd=ImageDraw.Draw(card)
        cd.rounded_rectangle([0,0,CW-1,LC_H-1],radius=sc(18),
            fill=(255,255,255,int(a_lg*245)),outline=(*BLUE,int(a_lg*85)),width=max(1,sc(2)))
        card.paste(LOGO,((CW-LOGO_W)//2,max(0,(LC_H-LOGO_H)//2)),LOGO)
        b=img.convert('RGBA'); b.paste(card,(PAD,LC_Y+yo_lg),card)
        img=b.convert('RGB'); d=ImageDraw.Draw(img)

    HY=LC_Y+LC_H+sc(22)
    a_h=spring(lt,0.22,0.38); yo_h=int(lerp(sc(12),0,spring(lt,0.22,0.38)))
    if a_h>0:
        for i,(ln,col) in enumerate([('BLASTUDIOS construye',WHITE),('esos sistemas.',BLUE)]):
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,HY+yo_h+i*sc(38)),ln,F_H2,col,BLUE,sc(9),a_h); d=ImageDraw.Draw(img)

    CK_Y=HY+sc(88); IH=sc(72)
    for i,(txt,delay) in enumerate(PUNTOS):
        a=spring(lt,delay,0.38)
        if a<=0.01: continue
        cy=CK_Y+i*(IH+sc(10)); yo=int(lerp(sc(12),0,spring(lt,delay,0.38)))
        img=glass(img,PAD,cy+yo,CW,IH,r=sc(13),ba=0.44*a,oa=0.22*a); d=ImageDraw.Draw(img)
        cr=sc(16); ccx=PAD+sc(38); ccy=cy+yo+IH//2
        d.ellipse([ccx-cr,ccy-cr,ccx+cr,ccy+cr],fill=(*BLUE,int(a*208)))
        a_ck=spring(lt,delay+0.14,0.22)
        if a_ck>0:
            p1=(ccx-sc(6),ccy); p2=(ccx-sc(1),ccy+sc(6)); p3=(ccx+sc(8),ccy-sc(7))
            d.line([p1,p2],fill=(*WHITE,int(a_ck*255)),width=max(1,sc(3)))
            if a_ck>0.5: d.line([p2,p3],fill=(*WHITE,int(min(1,(a_ck-.5)*2)*255)),width=max(1,sc(3)))
        a_tx=spring(lt,delay+0.10,0.26)
        if a_tx>0:
            for j,ln in enumerate(wrap(d,txt,F_H3,CW-sc(82))):
                d.text((PAD+sc(64),cy+yo+sc(14)+j*sc(30)),ln,font=F_H3,fill=(*WHITE,int(a_tx*214)))

    TG_Y=CK_Y+len(PUNTOS)*(IH+sc(10))+sc(14)
    a_tg=spring(lt,0.78,0.36)
    if a_tg>0:
        for i,ln in enumerate(['"No es suerte.',  '"Es sistema."']):
            lx=_cx(d,ln,F_H3)
            img=gtxt(img,(lx,TG_Y+i*sc(32)),ln,F_H3,WHITE,BLUE,sc(8),a_tg); d=ImageDraw.Draw(img)
    return img

# S4 — CTA  47-55s ───────────────────────────────────────────────────
def s4(img,lt):
    d=ImageDraw.Draw(img)
    a1=spring(lt,0.05,0.42); yo1=int(lerp(sc(18),0,spring(lt,0.05,0.42)))
    if a1>0:
        for i,ln in enumerate(['Si quieres implementar','IA de verdad,']):
            lx=_cx(d,ln,F_H2)
            img=gtxt(img,(lx,CY-sc(154)+yo1+i*sc(42)),ln,F_H2,WHITE,BLUE,sc(9),a1)
            d=ImageDraw.Draw(img)

    BTY=CY-sc(66); BTH=sc(68)
    a2=spring(lt,0.24,0.46); yo2=int(lerp(sc(18),0,spring(lt,0.24,0.46)))
    if a2>0:
        pulse=0.5+0.5*math.sin(lt*2.8); gs=int((sc(18)+sc(9)*pulse)*a2)
        img=glow_rect(img,PAD-gs//2,BTY+yo2-gs//3,W-PAD+gs//2,BTY+yo2+BTH+gs//3,BLUE,int(a2*48))
        d.rounded_rectangle([PAD,BTY+yo2,W-PAD,BTY+yo2+BTH],radius=BTH//2,fill=(*BLUE,int(a2*238)))
        p1='Escribenos  '; p2='IA'
        tw1=_tw(d,p1,F_H1); tw2=_tw(d,p2,F_H1)
        tx=CX-(tw1+tw2)//2; ty=BTY+yo2+(BTH-_th(d,p1,F_H1))//2
        d.text((tx,ty),p1,font=F_H1,fill=(*WHITE,int(a2*225)))
        img=gtxt(img,(tx+tw1,ty),p2,F_H1,WHITE,WHITE,sc(8),a2); d=ImageDraw.Draw(img)

    a3=spring(lt,0.46,0.34)
    if a3>0:
        ln='por DM o en comentarios'; lx=_cx(d,ln,F_BD)
        d.text((lx,BTY+BTH+sc(18)),ln,font=F_BD,fill=(*LGRAY,int(a3*172)))

    a4=spring(lt,0.60,0.34)
    if a4>0:
        hy=BTY+BTH+sc(64)
        blink=1.0 if (lt*2)%1<0.55 else 0.38
        pr=sc(5); dcx=CX-sc(100)
        d.ellipse([dcx-pr,hy+sc(5),dcx+pr,hy+sc(5)+pr*2],fill=(*GREEN,int(a4*blink*212)))
        d.text((CX-sc(90),hy+sc(2)),'En linea ahora',font=F_SM,fill=(*GREEN,int(a4*202)))
        lx=_cx(d,'@blastudios._',F_H2)
        img=gtxt(img,(lx,hy+sc(30)),'@blastudios._',F_H2,WHITE,BLUE,sc(9),a4)
        d=ImageDraw.Draw(img)

    a5=spring(lt,0.75,0.34)
    if a5>0:
        text='Te mostramos que automatizas esta semana.'
        for i,ln in enumerate(wrap(d,text,F_BD,W-sc(80))):
            lx=_cx(d,ln,F_BD)
            d.text((lx,BTY+BTH+sc(122)+i*sc(26)),ln,font=F_BD,fill=(*LGRAY,int(a5*172)))
    return img

# ── TIMELINE ────────────────────────────────────────────────────────
TIMES   = [(0,6),(6,18),(18,34),(34,47),(47,55)]
SCENES  = [s0,s1,s2,s3,s4]
ACCENTS = [BLUE,RED,LBLU,BLUE,GREEN]
XFADE   = 0.50

def get_scene(t):
    for i,(s,e) in enumerate(TIMES):
        if s<=t<e: return i,t-s
    return len(SCENES)-1,max(0.0,t-TIMES[-1][0])

def render_frame(fi):
    t=fi/FPS; si,lt=get_scene(t)
    ss,se=TIMES[si]
    base=draw_bg(t,ACCENTS[si%len(ACCENTS)])
    fa=eio((t-ss)/XFADE) if t-ss<XFADE else (eio((se-t)/XFADE) if se-t<XFADE and si<len(SCENES)-1 else 1.0)
    curr=SCENES[si](base.copy(),lt)
    if fa>=0.995:
        result=curr
    elif t-ss<XFADE and si>0:
        prev_lt=TIMES[si-1][1]-TIMES[si-1][0]-0.001
        prev=SCENES[si-1](base.copy(),prev_lt)
        result=Image.blend(prev,curr,eio((t-ss)/XFADE))
    else:
        result=Image.blend(base,curr,fa)
    result=draw_header(result,min(1.0,t*3))
    result=draw_pips(result,si,lt)
    result=draw_handle(result,min(1.0,max(0,(t-0.5)*2)))
    result=draw_progress(result,t)
    return result

# ── MAIN ────────────────────────────────────────────────────────────
if __name__=='__main__':
    print('='*60)
    print(' Reel BLASTUDIOS v2 - La Evolucion de la IA')
    print(f' {W}x{H} | {FPS}fps | {DUR}s | {FRAMES} frames')
    print(f' Salida: {OUT}')
    print('='*60)
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    writer=imageio_ffmpeg.write_frames(
        OUT,(W,H),fps=FPS,codec='libx264',
        pix_fmt_in='rgb24',pix_fmt_out='yuv420p',
        bitrate='14M',macro_block_size=1)
    writer.send(None)
    t0=time.time()
    for fi in range(FRAMES):
        if fi%FPS==0:
            el=time.time()-t0; eta=el/max(fi,1)*(FRAMES-fi); pct=fi/FRAMES*100
            bar='#'*int(pct/5)+'-'*(20-int(pct/5))
            sys.stdout.write(f'  [{bar}] {pct:5.1f}%  {fi//FPS:3d}s/{DUR}s  ETA {eta:4.0f}s  \r')
            sys.stdout.flush()
        writer.send(np.array(render_frame(fi)).tobytes())
    writer.close()
    el=time.time()-t0; mb=os.path.getsize(OUT)/1_048_576
    print(f'\n\n  Completado en {el:.1f}s - {mb:.1f} MB\n  {OUT}')
