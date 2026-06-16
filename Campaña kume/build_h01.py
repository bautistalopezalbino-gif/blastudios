# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import subprocess, os

HTML     = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Campaña kume\stories_kume.html'
OUT_DIR  = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\campañas instagram\kume'
FRAME    = os.path.join(OUT_DIR, '_h01_frame.png')
OUTPUT   = os.path.join(OUT_DIR, 'historia_01_hook.mp4')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1080, "height": 1920})
    page.goto(f'file:///{HTML.replace(chr(92), "/")}', wait_until='networkidle')
    # Story 1 ya está activa por defecto (class="story s1 active")
    page.wait_for_timeout(1500)  # esperar animaciones CSS
    # Capturar solo el div de la story (sin el viewer wrapper)
    story = page.locator('#s1')
    story.screenshot(path=FRAME)
    browser.close()

print(f'Frame guardado: {FRAME}')

# Crear video de 5s a 30fps desde el frame estático
cmd = [
    'ffmpeg', '-y',
    '-loop', '1',
    '-i', FRAME,
    '-t', '5',
    '-c:v', 'libx264',
    '-profile:v', 'baseline',
    '-level', '4.0',
    '-pix_fmt', 'yuv420p',
    '-vf', 'scale=1080:1920:flags=lanczos',
    '-color_range', 'tv',
    '-colorspace', 'bt709',
    '-color_trc', 'bt709',
    '-color_primaries', 'bt709',
    '-b:v', '4000k',
    '-maxrate', '5000k',
    '-bufsize', '8000k',
    '-r', '30',
    '-movflags', '+faststart',
    '-an',
    OUTPUT,
]
import subprocess
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print('ERROR FFmpeg:')
    print(result.stderr[-1000:])
else:
    size_mb = os.path.getsize(OUTPUT) / 1_048_576
    print(f'Video guardado: {OUTPUT} ({size_mb:.2f} MB)')

os.remove(FRAME)
print('Listo.')
