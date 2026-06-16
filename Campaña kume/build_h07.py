# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import subprocess, os, sys

SRC     = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Campaña kume\WhatsApp Video 2026-06-03 at 01.15.37.mp4'
OUT_DIR = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\campañas instagram\kume'
OVERLAY = os.path.join(OUT_DIR, '_h07_overlay.png')
OUTPUT  = os.path.join(OUT_DIR, 'historia_07_video_local.mp4')

W, H = 1080, 1920

# ── 1. Crear overlay PNG transparente ─────────────────────────
overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(overlay)

# Gradiente oscuro en la mitad inferior
for y in range(H // 2, H):
    alpha = int(200 * (y - H // 2) / (H // 2))
    draw.rectangle([(0, y), (W, y + 1)], fill=(0, 0, 0, alpha))

# Gradiente oscuro sutil en la parte superior (para que el badge se lea)
for y in range(0, 200):
    alpha = int(140 * (1 - y / 200))
    draw.rectangle([(0, y), (W, y + 1)], fill=(0, 0, 0, alpha))

# Fuentes
FONT_DIR = 'C:/Windows/Fonts/'
try:
    f_bold   = ImageFont.truetype(FONT_DIR + 'arialbd.ttf',  40)
    f_caption= ImageFont.truetype(FONT_DIR + 'arialbd.ttf',  46)
    f_sub    = ImageFont.truetype(FONT_DIR + 'arial.ttf',    24)
except Exception as e:
    print(f'Error cargando fuentes: {e}')
    sys.exit(1)

# ── Badge "bla" + "studios" ────────────────────────────────────
BX, BY = 54, 68
draw.text((BX, BY), 'bla', font=f_bold, fill=(255, 255, 255, 255))
bla_w = int(draw.textlength('bla', font=f_bold))
draw.text((BX + bla_w, BY), 'studios', font=f_bold, fill=(37, 99, 235, 255))

# ── Caption ────────────────────────────────────────────────────
CAPTION = 'Así quedó todo en funcionamiento.'
SUB     = 'blastudios · diseño + tecnología'

cap_x, cap_y = 54, H - 250
draw.text((cap_x, cap_y), CAPTION, font=f_caption, fill=(255, 255, 255, 255))
draw.text((cap_x, cap_y + 68), SUB, font=f_sub, fill=(255, 255, 255, 160))

overlay.save(OVERLAY, 'PNG')
print(f'Overlay guardado: {OVERLAY}')

# ── 2. Componer con FFmpeg ─────────────────────────────────────
cmd = [
    'ffmpeg', '-y',
    '-i', SRC,
    '-i', OVERLAY,
    '-filter_complex',
    '[0:v]scale=1080:1920:flags=lanczos,setsar=1:1[v];[v][1:v]overlay=0:0[out]',
    '-map', '[out]',
    '-map', '0:a',
    '-c:v', 'libx264',
    '-profile:v', 'baseline',
    '-level', '4.0',
    '-pix_fmt', 'yuv420p',
    '-color_range', 'tv',
    '-colorspace', 'bt709',
    '-color_trc', 'bt709',
    '-color_primaries', 'bt709',
    '-b:v', '4000k',
    '-maxrate', '5000k',
    '-bufsize', '8000k',
    '-r', '30',
    '-movflags', '+faststart',
    '-c:a', 'aac',
    '-b:a', '128k',
    '-ar', '44100',
    '-ac', '2',
    OUTPUT,
]
print('Ejecutando FFmpeg...')
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print('ERROR FFmpeg:')
    print(result.stderr[-2000:])
    sys.exit(1)

print(f'Video guardado: {OUTPUT}')
size_mb = os.path.getsize(OUTPUT) / 1_048_576
print(f'Tamaño: {size_mb:.2f} MB')

# Limpiar overlay temporal
os.remove(OVERLAY)
print('Listo.')
