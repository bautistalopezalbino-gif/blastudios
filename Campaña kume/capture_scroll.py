from playwright.sync_api import sync_playwright
from PIL import Image
import time

OUT = r'C:\Users\EMILIANO JAVIER LOPE\Desktop\blastudios\Campaña kume'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})

    print("Navegando a kumepasteleria.com...")
    page.goto("https://kumepasteleria.com", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # Obtener altura total de la pagina
    total_height = page.evaluate("document.body.scrollHeight")
    print(f"Altura total de la pagina: {total_height}px")

    # Scroll lento para activar lazy loading
    print("Haciendo scroll para activar lazy loading...")
    step = 400
    pos = 0
    while pos < total_height:
        page.evaluate(f"window.scrollTo(0, {pos})")
        page.wait_for_timeout(300)
        pos += step

    # Volver al inicio y esperar que cargue todo
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(3000)

    # Scroll final completo para asegurar que todo cargo
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1500)

    # Screenshot completo
    full_path = OUT + r'\kume_fullpage.png'
    page.screenshot(path=full_path, full_page=True)
    print(f"Screenshot guardado: {full_path}")

    browser.close()

# Dividir en 3 chunks
print("Dividiendo en chunks...")
img = Image.open(full_path)
print(f"Dimensiones: {img.size}")
h = img.height
chunk_h = h // 3

for i in range(3):
    top = i * chunk_h
    bottom = (i + 1) * chunk_h if i < 2 else h
    crop = img.crop((0, top, img.width, bottom))
    path = OUT + f'\\kume_chunk_{i}.png'
    crop.save(path, optimize=True)
    print(f"chunk_{i}: {top}px - {bottom}px guardado ({crop.size})")

print("Listo.")
