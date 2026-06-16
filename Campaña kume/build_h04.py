# -*- coding: utf-8 -*-
"""
Construye historia_04_pagina_web.mp4 (1080x1920, 9s):
  - PIL genera gradient background + todos los elementos UI
  - Los chunks de la web se animan en el viewport del browser mockup
  - FFmpeg compila los frames en MP4
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, os, math, shutil

STORY_DIR  = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Campaña kume'
OUT_DIR    = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\campañas instagram\kume'
OUTPUT     = os.path.join(OUT_DIR, 'historia_04_pagina_web.mp4')
FRAMES_DIR = os.path.join(OUT_DIR, '_h04_frames')
os.makedirs(FRAMES_DIR, exist_ok=True)

W, H = 1080, 1920
FPS, DUR = 30, 9
N = FPS * DUR

# ── Fuentes ────────────────────────────────────────────────────
FD = 'C:/Windows/Fonts/'
def font(name, size):
    try:    return ImageFont.truetype(FD + name, size)
    except: return ImageFont.load_default()

f_badge   = font('arialbd.ttf', 34)
f_label   = font('arial.ttf',   22)
f_num     = font('arialbd.ttf', 128)
f_title   = font('arialbd.ttf',  58)
f_url     = font('arial.ttf',   18)
f_tag     = font('arialbd.ttf', 26)
f_desc    = font('arial.ttf',   27)
f_done    = font('arialbd.ttf', 28)

# ── Colores ────────────────────────────────────────────────────
C_BG1    = (13, 31, 60)       # #0d1f3c
C_BG2    = (10, 22, 40)       # #0a1628
C_BLUE   = (37, 99, 235)      # #2563EB
C_WHITE  = (255, 255, 255)
C_SUBTLE = (255, 255, 255, 80)
C_MOCK   = (255, 255, 255, 10)
C_BAR    = (255, 255, 255, 15)
C_BORDER = (255, 255, 255, 20)
C_TAG_BG = (37, 99, 235, 38)
C_TAG_BD = (37, 99, 235, 64)
C_GREEN  = (34, 197, 94)
C_DONE   = (20, 80, 40)

def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ── Gradiente de fondo ─────────────────────────────────────────
def make_bg():
    img = Image.new('RGB', (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        r = int(C_BG1[0] + (C_BG2[0] - C_BG1[0]) * t)
        g = int(C_BG1[1] + (C_BG2[1] - C_BG1[1]) * t)
        b = int(C_BG1[2] + (C_BG2[2] - C_BG1[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return img

bg_base = make_bg()

# ── Cargar chunks y preparar strip ────────────────────────────
print("Cargando chunks...")
# Mockup layout
PAD_X   = 64          # padding izquierdo de la story
PAD_TOP = 80
MOCK_X  = PAD_X       # x inicio del browser mockup
MOCK_W  = W - PAD_X * 2         # 952px
MOCK_BAR_H  = 52      # altura de la barra de dirección
MOCK_VP_H   = 680     # altura del viewport
MOCK_BORDER = 2
MOCK_R      = 18      # border-radius del mockup

# Viewport interior
VP_X = MOCK_X + MOCK_BORDER
VP_Y_TOP = (PAD_TOP                        # padding
          + 30 + 5                         # label "ENTREGA"
          + 140 + 12                       # número "01"
          + 68 + 24                        # título "Página web"
          + MOCK_BORDER + MOCK_BAR_H)      # barra del browser
VP_W = MOCK_W - MOCK_BORDER * 2
VP_H = MOCK_VP_H

chunks = []
for i in range(2):
    c = Image.open(os.path.join(STORY_DIR, f'kume_chunk_{i}.png')).convert('RGB')
    ratio = VP_W / c.width
    c = c.resize((VP_W, int(c.height * ratio)), Image.LANCZOS)
    chunks.append(c)

strip_h = sum(c.height for c in chunks)
strip = Image.new('RGB', (VP_W, strip_h))
y0 = 0
for c in chunks:
    strip.paste(c, (0, y0))
    y0 += c.height

max_scroll = strip_h - VP_H
print(f"  VP: {VP_W}x{VP_H}  Strip: {VP_W}x{strip_h}  max_scroll={max_scroll}")

# ── Función de easing ──────────────────────────────────────────
def ease_io(t):
    return (1 - math.cos(math.pi * t)) / 2

def lerp(a, b, t):
    return a + (b - a) * t

TARGET_A = min(int(max_scroll * 0.32), max_scroll)
TARGET_B = min(int(max_scroll * 0.65), max_scroll)

KF = [
    (0.00, 0),
    (0.08, 0),
    (0.30, TARGET_A),
    (0.50, TARGET_A),
    (0.72, TARGET_B),
    (0.90, TARGET_B),
    (1.00, 0),
]

def scroll_at(t):
    for i in range(len(KF) - 1):
        t0, y0 = KF[i]; t1, y1 = KF[i+1]
        if t0 <= t <= t1:
            local = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return int(lerp(y0, y1, ease_io(local)))
    return 0

# ── Función que dibuja un frame ────────────────────────────────
def rounded_rect(draw, x0, y0, x1, y1, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)

def make_frame(scroll_y):
    img = bg_base.copy().convert('RGBA')
    draw = ImageDraw.Draw(img, 'RGBA')

    # ── Badge "bla + studios" top-right ──
    bx = W - PAD_X
    by = 52
    bla_w = int(draw.textlength('bla', font=f_badge))
    draw.text((bx - bla_w - int(draw.textlength('studios', font=f_badge)), by),
              'bla', font=f_badge, fill=C_WHITE)
    draw.text((bx - int(draw.textlength('studios', font=f_badge)), by),
              'studios', font=f_badge, fill=(*C_BLUE, 255))

    cy = PAD_TOP

    # ── "ENTREGA" label ──
    draw.text((PAD_X, cy), 'ENTREGA', font=f_label, fill=(*C_BLUE, 220), spacing=4)
    cy += 35

    # ── "01" number ──
    draw.text((PAD_X, cy), '01', font=f_num, fill=(*C_BLUE, 255))
    cy += 152

    # ── "Página web" title ──
    draw.text((PAD_X, cy), 'Página web', font=f_title, fill=C_WHITE)
    cy += 80

    # ── Browser mockup ──
    mock_top = cy
    mock_bot = cy + MOCK_BAR_H + VP_H + MOCK_BORDER * 2
    # fondo del mockup
    rounded_rect(draw, MOCK_X, mock_top, MOCK_X + MOCK_W, mock_bot,
                 MOCK_R, fill=(255,255,255,10), outline=(255,255,255,25), width=MOCK_BORDER)

    # Barra de dirección
    bar_bot = mock_top + MOCK_BAR_H
    rounded_rect(draw, MOCK_X + 1, mock_top + 1, MOCK_X + MOCK_W - 1, bar_bot,
                 MOCK_R, fill=(255,255,255,14))

    # Dots
    dot_y = mock_top + MOCK_BAR_H // 2
    dot_colors = [(239,68,68), (245,158,11), (34,197,94)]
    for i, dc in enumerate(dot_colors):
        dx = MOCK_X + 20 + i * 22
        draw.ellipse([dx - 6, dot_y - 6, dx + 6, dot_y + 6], fill=dc)

    # URL bar
    url_x0 = MOCK_X + 85; url_x1 = MOCK_X + MOCK_W - 18
    url_y0 = mock_top + 12; url_y1 = mock_top + MOCK_BAR_H - 12
    draw.rounded_rectangle([url_x0, url_y0, url_x1, url_y1], radius=5, fill=(255,255,255,18))
    draw.text(((url_x0 + url_x1)//2, (url_y0 + url_y1)//2),
              '🔒 kumepasteleria.com', font=f_url,
              fill=(255,255,255,140), anchor='mm')

    cy = bar_bot + 1  # inicio del viewport

    # ── Pegar chunk en el viewport ──
    crop = strip.crop((0, scroll_y, VP_W, scroll_y + VP_H))
    # Convertir a RGBA para pegar
    img.paste(crop.convert('RGBA'), (VP_X, cy))

    # Clip inferior del mockup (overlay negro con radio para simular overflow:hidden)
    # Dibuja negro fuera de las esquinas redondeadas del viewport
    cy_end = cy + VP_H

    cy = cy_end + MOCK_BORDER + 28  # margen tras el mockup

    # ── Tags ──
    tags = ['Moderna', 'Rápida', 'Funcional']
    tx = PAD_X
    for tag in tags:
        tw = int(draw.textlength(tag, font=f_tag)) + 28
        draw.rounded_rectangle([tx, cy, tx + tw, cy + 44], radius=22,
                                fill=(37,99,235,38), outline=(37,99,235,80), width=1)
        draw.text((tx + tw//2, cy + 22), tag, font=f_tag, fill=C_WHITE, anchor='mm')
        tx += tw + 16
    cy += 62

    # ── Descripción ──
    draw.text((PAD_X, cy),
              'Diseñada para convertir visitantes en clientes.',
              font=f_desc, fill=(255,255,255,115))
    cy += 48

    # ── Entregado badge ──
    done_w = int(draw.textlength('✓ Entregado', font=f_done)) + 48
    draw.rounded_rectangle([PAD_X, cy, PAD_X + done_w, cy + 52], radius=26,
                            fill=(20,80,40,220), outline=(34,197,94,120), width=1)
    draw.text((PAD_X + done_w//2, cy + 26), '✓ Entregado', font=f_done,
              fill=C_WHITE, anchor='mm')

    return img.convert('RGB')

# ── Generar frames ─────────────────────────────────────────────
print(f"Generando {N} frames...")
for f in range(N):
    t = f / (N - 1)
    sy = max(0, min(scroll_at(t), max_scroll))
    frame = make_frame(sy)
    frame.save(os.path.join(FRAMES_DIR, f'frame_{f:04d}.png'))
    if f % 30 == 0:
        print(f"  frame {f}/{N}  scroll={sy}")

print("Compilando con FFmpeg...")
cmd = [
    'ffmpeg', '-y',
    '-framerate', str(FPS),
    '-i', os.path.join(FRAMES_DIR, 'frame_%04d.png'),
    '-c:v', 'libx264',
    '-profile:v', 'baseline', '-level', '4.0',
    '-pix_fmt', 'yuv420p',
    '-color_range', 'tv', '-colorspace', 'bt709',
    '-color_trc', 'bt709', '-color_primaries', 'bt709',
    '-b:v', '4000k', '-maxrate', '5000k', '-bufsize', '8000k',
    '-movflags', '+faststart', '-an',
    OUTPUT,
]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("ERROR FFmpeg:\n", r.stderr[-1500:])
else:
    print(f"Guardado: {OUTPUT}  ({os.path.getsize(OUTPUT)/1e6:.2f} MB)")

shutil.rmtree(FRAMES_DIR, ignore_errors=True)
print("Listo.")
