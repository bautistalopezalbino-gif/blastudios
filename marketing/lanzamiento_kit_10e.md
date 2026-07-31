# Lanzamiento · Kit Blastudios nº01 (10 €)

> **Objetivo:** cerrar la primera venta de 10 € lo antes posible y dejar montado un producto
> que siga vendiendo solo.
> **Activo:** `kit/index.html` (página de venta) + `producto/kit-blastudios-30dias.pdf` (12 págs.)
> **URL una vez desplegado:** `blastudios.vercel.app/kit/`

---

## 1. ACTIVAR EL COBRO (5 minutos, una sola vez)

La página **ya funciona sin configurar nada**: si no hay pasarela, el botón abre un modal con
Bizum al **648 021 435** + WhatsApp. Con eso se puede cobrar hoy mismo.

Para cobrar en automático con tarjeta:

1. Entra en `dashboard.stripe.com` → **Payment links** → **New**.
2. Producto: `Kit Blastudios · 30 días de contenido con IA`. Precio: `10,00 EUR`, pago único.
3. En *After payment* → **Redirect customers to a URL** → pega `https://blastudios.vercel.app/kit/gracias.html`.
4. Copia el enlace `https://buy.stripe.com/...`.
5. Ábrelo en `kit/index.html` y pégalo en la línea `stripe: ""` del bloque `const PAGO`.

Alternativa sin Stripe: pon tu `paypal.me` en la línea `paypal: ""`. Si dejas ambas vacías,
sigue funcionando con Bizum.

> El PDF vive en `kit/d/k30d-bls-7f3a91/kit-blastudios-30dias.pdf`. La ruta no está enlazada
> desde ninguna parte pública, pero tampoco está protegida: si en algún momento el kit vende
> en volumen, conviene moverlo a una entrega con enlace firmado (Gumroad, Lemon Squeezy o
> el propio Stripe con *file delivery*).

---

## 2. PRIMERA VENTA: EL CAMINO MÁS CORTO

El orden importa. De más caliente a más frío:

| Orden | Dónde | Por qué funciona | Esfuerzo |
|-------|-------|------------------|----------|
| 1 | **DM a clientes y contactos que ya te conocen** | Ya confían. 10 € no es una decisión, es un sí o un no. | 15 min |
| 2 | **Stories con encuesta** | Te da lista de interesados antes de vender. | 10 min |
| 3 | **Post en el feed (carrusel)** | Se queda en el perfil y sigue vendiendo. | 20 min |
| 4 | **Grupos de negocio local / WhatsApp de comerciantes** | Público exacto: dueños de negocio en Valencia. | 10 min |

**Regla:** no anuncies el kit sin decir el precio. A 10 € el precio *es* el argumento.

---

## 3. DM PARA CONTACTOS Y CLIENTES (el que cierra)

No pegues el enlace en el primer mensaje. Pregunta antes.

**Mensaje 1**
```
Hola [nombre]! Oye, he montado una cosa y me sirve mucho tu opinión.

He hecho un PDF con un calendario de 30 días de contenido para negocios
como el tuyo: qué publicar cada día, 12 prompts de IA listos y la estructura
de reel que usamos nosotros. Lo he puesto a 10 € para que no sea una barrera.

¿Te lo paso y me dices qué te parece?
```

**Mensaje 2 (si dice que sí)**
```
Genial. Aquí lo tienes: blastudios.vercel.app/kit

Son 10 € por Bizum al 648 021 435 o con tarjeta desde la web, como te venga mejor.
En cuanto lo veas, dime sin filtros qué te sobra y qué te falta.
```

**Si dice "ya lo miraré"**
```
Sin problema. Si te acuerdas la semana que viene sigue ahí.
Y si lo ves y no te sirve, te devuelvo los 10 € sin preguntar nada.
```

---

## 4. SECUENCIA DE 5 STORIES

| # | Visual | Texto | Interacción |
|---|--------|-------|-------------|
| 1 | Fondo negro, texto grande | «¿Cuántas veces has abierto Instagram para publicar y lo has cerrado sin publicar nada?» | Encuesta: *Muchas / Todos los días* |
| 2 | Mockup de la portada del kit | «Por eso he hecho esto: 30 días ya decididos. No eliges qué publicar, solo lo publicas.» | — |
| 3 | Captura de la página del calendario | «Día 1: el error nº1 de tu sector. Día 2: stories del día normal. Día 3: antes y después… así hasta 30.» | — |
| 4 | Captura de la página de prompts | «Y 12 prompts listos para copiar. Los mismos que usamos nosotros.» | — |
| 5 | Fondo azul #2563EB, precio grande | «10 €. Pago único. Descarga inmediata.» | Sticker enlace → blastudios.vercel.app/kit |

Publícalas seguidas, no repartidas. La secuencia funciona junta.

---

## 5. CARRUSEL PARA EL FEED (7 slides)

1. **Portada** — «30 días de contenido, ya decididos.» (subtítulo: *para negocios que llevan solos sus redes*)
2. «El problema nunca fue el tiempo. Fue la pantalla en blanco.»
3. «Publicar a ratos es casi lo mismo que no publicar: el algoritmo deja de enseñarte a gente nueva.»
4. «Dentro: calendario de 30 días con formato, tema y ángulo ya decididos.»
5. «12 prompts listos para copiar. Escritos para que no suene a IA.»
6. «La estructura de reel segundo a segundo + 20 ganchos y CTAs.»
7. **CTA** — «10 €. Enlace en la bio.» + logo

**Pie de foto**
```
Si llevas tú las redes de tu negocio, esto te ahorra el peor momento de la semana:
el de mirar la pantalla en blanco sin saber qué poner.

30 días planificados. 12 prompts de IA listos para copiar. La estructura de reel
que usamos con nuestros clientes. Y un caso real explicado de principio a fin.

12 páginas. 10 €. Pago único.
Enlace en la bio 👆

#negociolocal #valencia #marketingdigital #instagramparanegocios #contenidoconia
```

---

## 6. MENSAJE PARA GRUPOS DE COMERCIANTES / WHATSAPP

```
Buenas 👋 Somos Blastudios, agencia de marketing digital aquí en Valencia.

Hemos sacado un kit práctico para negocios que llevan ellos mismos las redes:
un calendario de 30 días con qué publicar cada día, 12 prompts de IA listos
y la estructura de reel que usamos con nuestros clientes.

Son 12 páginas en PDF por 10 €. Lo dejamos aquí por si a alguien le viene bien:
blastudios.vercel.app/kit

(Y si alguien lo compra y no le sirve, le devolvemos los 10 € sin preguntar.)
```

---

## 7. QUÉ MIRAR DESPUÉS DE LANZAR

| Señal | Qué significa | Qué hacer |
|-------|---------------|-----------|
| Visitas a `/kit/` pero cero compras | La página no cierra | Baja el precio de prueba o añade una muestra gratuita de 3 páginas |
| Cero visitas | No estás distribuyendo | Vuelve al punto 2: los DMs son el canal, no el post |
| Compras sin fricción | Funciona | Sube a 15–19 € y prepara el kit nº02 |
| Preguntan por servicios tras comprar | El kit está haciendo su trabajo real | Es la venta grande: pasa a llamada |

**Lo importante:** el kit no está aquí para facturar 10 €. Está para que un dueño de negocio
pruebe cómo trabaja Blastudios por el precio de dos cafés y luego pregunte por la web,
la campaña o la automatización. Ese es el retorno de verdad.
