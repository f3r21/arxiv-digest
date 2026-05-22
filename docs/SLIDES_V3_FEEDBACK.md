# Feedback v3 para Claude Design — focus slide 6 (Demo)

> Pegale ESTO. Las correcciones del audit v2 quedaron perfectas. El
> único problema serio que queda es el slide 6 (Demo). Te explico
> qué no funciona y propongo 2 opciones de redesign.

---

## Lo que ya está OK (no tocar)

Verifiqué todas las correcciones del audit anterior — aplicadas
correctamente:
- Service names + RAM en SVG arquitectura
- YAML real en slide 4
- Dockerfile real en slide 5 (12 líneas, sin HEALTHCHECK inline)
- Métricas slide 7 (~190 MB, ~20%, ~30 ediciones, manual deploy)
- Backup story slide 9 (Google Drive + rclone)
- Secrets slide 9 (3 reales con nombres correctos)
- Speaker notes en español neutro (sin voseo)
- restart: always, Docker Hub, todo correcto

Excelente trabajo en v2. Solo falta arreglar el slide 6.

---

## Slide 6 actual — por qué no funciona

5 wireframes esquemáticos en fila (Landing → Confirm → Digest →
Reply → PDFs) + QR en la 6ta columna. Problemas:

### 1. Visualmente stale

Wireframes con rect dummy + buttons placeholder se ven "demo deck
de 2014". En 2026, mockups así se leen como **placeholders, no
como producto**. El público técnico los descarta visualmente.

### 2. Sin jerarquía

Los 5 wireframes son del mismo tamaño y forma. No hay focal point.
El elemento más interesante de la demo (**reply → PDFs**, lo único
realmente único del producto) está enterrado como la 5ta tarjeta
chiquita.

### 3. Texto redundante

El header `"Subscribe → Confirm → Digest → Reply → PDFs"` repite
exactamente los 5 labels (`01·Landing`, `02·Confirm`, etc.) que
están abajo. Decir lo mismo dos veces.

### 4. Datos inventados que distraen

- "Vol. I · **No. 28**" → real estamos en No. 6
- "A scaling law for chain-of-thought…" → paper inventado
- "2511.0142.pdf, 2511.0188.pdf, 2511.0203.pdf" → IDs falsos
- "~**90** segundos después" → real es ~30s
- "From: **hola@arxivdaily.com**" → no existe ese email

Cuando un orador técnico ve "No. 28" pero el speaker dice "estamos
en No. 6", el público nota la inconsistencia.

### 5. QR comprimido

El QR está spueezed en la 6ta columna a la misma altura que los
wireframes. Es chico, casi escondido. **Debería ser el CTA visual
del slide** porque permite que el público escanee y se suscriba
en el mismo momento.

---

## Propuesta A — Hero + secuencia simplificada (Recommended)

**Concepto**: foco grande en la captura real del email reply con
PDFs (la cosa única). El flow se simplifica a 3 pasos en vez de 5.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  05 — Demo                                  arxivdaily · 06/10│
├──────────────────────────────────────────────────────────────┤
│  EL FLUJO EN VIVO        Tres pasos. Treinta segundos.        │
│                                                                │
│  ┌─────────────────────────────────┬──────────────────────┐   │
│  │                                 │                      │   │
│  │  [SCREENSHOT GRANDE             │   01  Suscríbete     │   │
│  │   del email digest con          │       arxivdaily.    │   │
│  │   "Editor's Pick" + 3 papers    │       ignorelist.com │   │
│  │   en cream Georgia editorial]   │                      │   │
│  │                                 │   02  Recibes la     │   │
│  │  ─────────────────              │       edición 7 am   │   │
│  │                                 │                      │   │
│  │  [SCREENSHOT REPLY con PDFs     │   03  Respondes con  │   │
│  │   adjuntos: "1 3 5" → 3 PDFs    │       los números    │   │
│  │   en ~30s]                      │       — recibes los  │   │
│  │                                 │       PDFs en ~30s   │   │
│  │                                 │                      │   │
│  │                                 │   ┌──────────────┐   │   │
│  │                                 │   │   [QR GRANDE]│   │   │
│  │                                 │   │              │   │   │
│  │                                 │   │  arxivdaily. │   │   │
│  │                                 │   │  ignorelist  │   │   │
│  │                                 │   └──────────────┘   │   │
│  └─────────────────────────────────┴──────────────────────┘   │
│                                                                │
│  The Daily Abstract                                  Fer       │
└──────────────────────────────────────────────────────────────┘
```

### Cambios específicos

1. **Eliminar** los 5 wireframes chicos (Landing, Confirm, Digest,
   Reply, PDFs separados).
2. **Reemplazar** con 2 "mockups" más grandes apilados verticalmente
   a la izquierda (60% del ancho):
   - **Mockup 1**: render fiel del email digest. Cream `#f4f1ea`,
     Georgia serif "The Daily Abstract" header en amber caps,
     "Hoy 4 papers nuevos" intro, "Editor's Pick" con número 01
     gigante (no SVG genérico — replicar la estética del email real
     del proyecto).
   - **Mockup 2**: render del reply email. Mismo cream. Header
     "Your papers, attached." en Georgia. "You asked for papers 1
     and 3" + listing de 2 PDFs con `arxiv.org/abs/1706.03762` y
     `arxiv.org/abs/2310.06825`.
3. **A la derecha (35%)**: 3 pasos vertical, tipografía grande:
   ```
   01  Suscríbete
       arxivdaily.ignorelist.com
   02  Recibes la edición a las 7 am
       4 papers nuevos · ~6 min de lectura
   03  Respondes con los números → PDFs en ~30 s
   ```
4. **QR**: agrandar al doble del tamaño actual. Posicionarlo abajo
   a la derecha bajo el paso 03. Etiqueta "Suscríbete" en amber
   caps encima.
5. **Header del slide**: eyebrow "EL FLUJO EN VIVO" + h3 italic
   "Tres pasos. Treinta segundos." (en vez de la cadena de 5 con
   flechas).
6. **Datos reales** en los mockups:
   - Mockup 1 (digest): "Vol. I · No. 6 · Thursday, 22 May 2026 ·
     cs.CL · cs.LG"
   - Editor's Pick: "Attention Is All You Need" con autores
     "Vaswani, Shazeer, Parmar et al." y abstract real (4 líneas).
   - Mockup 2 (reply): "Re: The Daily Abstract No. 6 — 2 PDFs",
     "Vaswani_2017_Attention_Is_All_You_Need.pdf" y
     "Jiang_2023_Mistral_7B.pdf"

### Ventajas

- Foco claro: el reply→PDF es lo único, ahora se VE
- Reemplaza wireframes esquemáticos por mockups del email REAL
  (Charcoal Ember + Georgia + amber accent — coherente con el
  resto del deck)
- QR grande = el público escanea en el momento del demo (auténtico
  CTA, no decoración)
- 3 pasos vs 5 = menos texto, más espacio para respirar

---

## Propuesta B — Live demo screenshot puro

**Concepto**: nada de mockups. Una sola screenshot del Gmail del
presentador mostrando el email digest + reply lado a lado.

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  05 — Demo                                  arxivdaily · 06/10│
├──────────────────────────────────────────────────────────────┤
│  ENVIÉ "1 3" — RECIBÍ 2 PDFs       ~30 segundos               │
│                                                                │
│  ┌─────────────────────────┬─────────────────────────────┐   │
│  │                         │                              │   │
│  │  [SCREENSHOT REAL Gmail │  [SCREENSHOT Gmail reply    │   │
│  │   inbox con el digest   │   con 2 PDFs adjuntos]      │   │
│  │   open, Editor's Pick   │                              │   │
│  │   visible]              │   Click se ve el archivo:   │   │
│  │                         │   Vaswani_2017.pdf         │   │
│  │                         │   Jiang_2023.pdf           │   │
│  └─────────────────────────┴─────────────────────────────┘   │
│                                                                │
│  ┌────────────┐                                                │
│  │  [QR]      │   Probalo ahora: arxivdaily.ignorelist.com    │
│  └────────────┘                                                │
│                                                                │
│  The Daily Abstract                                  Fer       │
└──────────────────────────────────────────────────────────────┘
```

### Cambios específicos

1. **Reemplazar todos los wireframes** por 2 screenshots reales
   side-by-side (presupone que el orador exporta screenshots del
   email digest + reply de su Gmail antes del demo)
2. **Header**: "ENVIÉ '1 3' — RECIBÍ 2 PDFs" con timing "~30 segundos"
   subtitle
3. **QR + URL** abajo, prominentes pero no centrales

### Ventajas

- Maximum authenticity: el producto se ve como ES, no como podría ser
- Trust signal fuerte (especialmente para público técnico que
  detecta mockups falsos)
- Menos texto, más visual

### Desventajas

- Requiere que el orador exporte 2 screenshots y los pase al deck
  (tú no lo puedes hacer sin esos PNGs)
- Los screenshots quizá tengan info personal a tachar

---

## Mi recomendación

**Propuesta A** porque:

1. No requiere exportar nada externamente — vos lo armás todo
   con HTML/CSS replicando la estética del email digest real
2. Mantiene la identidad editorial del deck (Charcoal Ember + Georgia)
3. Los "mockups" en HTML/CSS se ven más curated que screenshots
   crudos de Gmail (Gmail tiene chrome feo)
4. Permite controlar exactamente qué datos mostrar (paper IDs reales)

Pero si el usuario prefiere B, también funciona — el orador
agrega los PNGs después.

---

## Cambios menores en otras slides (mientras estamos)

Mientras regenerás el deck:

### Slide 2 (Problema) — pain "Personalización pobre"

El texto actual: "Newsletters genéricos por categoría amplia. No
hay un cs.CL + es-ES nativo."

Está bien pero "cs.CL + es-ES nativo" suena críptico al público
no técnico. Suavizar a: "No hay newsletter específico por
categoría arXiv con traducción a español nativa."

### Slide 4 (compose) — verificar memoria total

El callout dice "Memoria: 570 MB · 60% de la VM". El 60% es del
budget asignado, no del uso real (que es ~20%). Aclarar para
evitar confusión:

```
Memoria reservada: 570 MB    (60% del límite VM 956 MB)
Memoria en uso:    ~190 MB   (20% real en idle)
```

### Slide 5 (Dockerfile) — heading

"Patrón típico, 12 líneas" → más fuerte: "**Doce líneas, sin
trucos**." (más editorial, más memorable)

---

## Speaker notes — solo slide 6

Reescribir el speaker note de slide 6 si elegís Propuesta A:

```
Acá pueden ver el flujo en vivo. La izquierda: el email digest
que llega cada mañana a las siete. Cream paper, Georgia serif,
"Editor's Pick" arriba con el número 01 gigante — esto es lo
que ve el suscriptor.

Debajo: el reply email. Yo respondo con los números — en este
caso uno y tres — y treinta segundos después me llegan los dos
PDFs adjuntos. No abro arxiv, no clickeo en abstract, no busco
el botón de PDF. Solo respondo el email.

A la derecha tienen los tres pasos. Y ese QR es el deck en
producción ahora mismo — pueden escanear y suscribirse en este
momento. Si lo hacen ahora, mañana a las siete les llega el
primer digest.

Killer line: Tres pasos. Treinta segundos del reply al PDF.
Tiempo target: 120 seg
```

---

Cuando esté el handoff v3, mandame el link y verifico el slide 6
final + los cambios menores.
