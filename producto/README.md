# Producto digital · Kit Blastudios nº01

Fuente del PDF que se vende en `/kit/`.

| Archivo | Qué es |
|---------|--------|
| `kit_30dias.html` | Maquetación del PDF (12 páginas A4). **Aquí se edita el contenido.** |
| `fonts.css` | Inter + Space Grotesk incrustadas en base64. Generado, no editar a mano. |
| `inline_fonts.py` | Regenera `fonts.css` descargando las fuentes de Google Fonts. |
| `build_pdf.js` | Renderiza el HTML a `kit-blastudios-30dias.pdf` con Chromium. |
| `kit-blastudios-30dias.pdf` | El entregable. |

## Regenerar el PDF

```bash
# solo la primera vez, o si cambian las fuentes
python3 producto/inline_fonts.py

node producto/build_pdf.js
```

`build_pdf.js` usa `puppeteer-core`. Si no encuentra Chromium, pásale la ruta:

```bash
CHROME_PATH=/ruta/a/chrome node producto/build_pdf.js
```

## Después de regenerar

Hay que copiar el PDF nuevo a la carpeta de entrega y refrescar las vistas previas
que usa la página de venta:

```bash
cp producto/kit-blastudios-30dias.pdf kit/d/k30d-bls-7f3a91/
```

Las imágenes de `kit/preview/` son capturas de las páginas 1, 4, 6, 8, 9 y 11 del propio HTML.
