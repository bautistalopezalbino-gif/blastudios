# Inventario de assets

Ruta **sin captura**: no se rastreó ningún sitio. Los tokens de marca provienen del
código fuente de `index.html` del repositorio de blastudios, que es la fuente
autoritativa (la home desplegada es una SPA con loader y el scraping daría tokens
peores). Los dos assets siguientes se tomaron del propio repositorio.

| Archivo | Qué es | Dónde encaja |
|---|---|---|
| `capture/assets/blastudios-logo-dark.svg` | Logotipo blastudios completo (icono + wordmark + tagline), variante para fondo oscuro. | Marca héroe del frame 06. **Es el que se usa en el reel.** |
| `capture/assets/blastudios-logo.svg` | Logotipo blastudios original del repo. Tinta `#0D1F3C` sobre transparente: pensado para fondo claro, **invisible sobre el negro de la marca**. No usar en el reel. | Referencia de origen únicamente. |
| `capture/assets/blastudios-icono.svg` | Isotipo de blastudios para Instagram, vectorial. | Alternativa compacta si el logotipo completo no cabe en el CTA. |

No hay fotografías ni capturas de pantalla en este proyecto: es una pieza de
tipografía cinética íntegramente construida en HTML.

## Nota sobre el logotipo

El logotipo original de `Fotos/blastudios-logo.svg` está construido para fondo claro: tanto el cuadro
del icono como el wordmark van en `#0D1F3C`, que sobre `#000000` desaparece. Se derivó
`blastudios-logo-dark.svg` cambiando únicamente lo mínimo: el wordmark pasa a `#F5F5F7`, las marcas
interiores del icono a `#F5F5F7`, y el cuadro navy recibe un filo de 2px en `#2563EB` para separarse
del fondo. La geometría, las proporciones y el `viewBox` no se tocan.

**El SVG lleva `<text>` real, no trazados.** Tiene que ir *inline en el DOM* para que la webfont Inter
del proyecto le aplique; referenciado desde un `<img>` no cargaría la fuente y el wordmark caería a la
tipografía del sistema.
