"""Descarga Inter + Space Grotesk (subconjunto latino) y los incrusta en fonts.css
como data-URI, para que el PDF del producto se genere igual con o sin red.

Uso: python3 producto/inline_fonts.py
"""
import base64, os, re, urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
CSS_URL = ("https://fonts.googleapis.com/css2?"
           "family=Inter:wght@300;400;500;600;700"
           "&family=Space+Grotesk:wght@500;600;700&display=swap")
OUT = os.path.join(os.path.dirname(__file__), "fonts.css")


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def main():
    css = get(CSS_URL)
    blocks = re.findall(r"@font-face\s*\{[^}]*\}", css)
    kept = []
    for b in blocks:
        # solo el subconjunto latino basico
        rng = re.search(r"unicode-range:\s*([^;]+);", b)
        if rng and "U+0000-00FF" not in rng.group(1):
            continue
        url = re.search(r"url\((https://[^)]+)\)", b)
        if not url:
            continue
        raw = get(url.group(1), binary=True)
        b64 = base64.b64encode(raw).decode("ascii")
        kept.append(re.sub(r"url\(https://[^)]+\)",
                           f"url(data:font/woff2;base64,{b64})", b))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* Generado por inline_fonts.py - no editar a mano */\n")
        f.write("\n".join(kept))
    print(f"{len(kept)} font-faces incrustados en {OUT}")


if __name__ == "__main__":
    main()
