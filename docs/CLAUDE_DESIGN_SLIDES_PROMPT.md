# Claude Design — Brief para slides de presentación

> Esto es el prompt completo para pegar en Claude Design.
> Generá HTML slides 16:9 para presentación de Cloud Computing (10 min).

---

## Tu rol

Diseñá un set de **10 slides HTML standalone (1920×1080, ratio 16:9)** para
una presentación de clase de Cloud Computing. El presentador es estudiante,
el público son profesores + compañeros. 10 minutos total.

El proyecto presentado es **The Daily Abstract** — un newsletter diario de
arXiv que ya tiene identidad visual editorial. Las slides deben **continuar
esa identidad** pero adaptada al formato presentación (texto más grande,
menos densidad, hierarchy más bold).

## Repo input (leé estos archivos primero)

| Archivo | Para qué |
|---|---|
| `docs/PRESENTATION.md` | **El contenido exacto de las 10 slides** (sigue su estructura — no inventes texto nuevo) |
| `docs/ARCHITECTURE.md` | Diagramas Mermaid para slide 3 |
| `docs/DESIGN_BRIEF.md` | Paleta Charcoal Ember, tipografía Georgia, anti-patterns |
| `docs/BRAND_VOICE.md` | Voz editorial, sin emoji, understated |
| `docker-compose.prod.yml` | Para snippet del slide 4 |
| `digest/Dockerfile` | Para snippet del slide 5 |
| `subscriptions/static/og-image.png` | Wordmark de referencia |

## Slides a generar (1920×1080 cada una)

### Slide 1 — Title

- Eyebrow caps amber: "CLOUD COMPUTING · 2026"
- H1 Georgia gigante: **The Daily Abstract**
- Sub italic Georgia: "Newsletter diario de arXiv con reply-to-PDF"
- Tres tags abajo separados por · : "Indie · Open source · $0/mes"
- En la esquina inferior: nombre del presentador (placeholder
  `{{ presenter_name }}`)
- En la otra esquina: URL `arxivdaily.ignorelist.com` en mono amber

### Slide 2 — Problema

Layout: izquierda texto, derecha visual numérico

**Izquierda (60%):**
- Eyebrow: "PROBLEMA"
- H2: "arXiv publica **~500 papers/día solo en cs.LG**"
- Lista de 4 pain points (de PRESENTATION.md):
  - Saturación
  - Fricción para guardar
  - Personalización pobre
  - Gap en herramientas abiertas + Spanish-aware

**Derecha (40%):**
- Visual grande estilo periódico: el número "500" enorme Georgia, con
  "papers/día" abajo. Tipografía editorial NYT-style.

### Slide 3 — Arquitectura

Slide más importante visualmente. **Centrar el diagrama Mermaid de
`docs/ARCHITECTURE.md` (el primer mermaid graph)** renderizado con
estética coherente — fondo charcoal, nodos cream con border amber.

- Header arriba: eyebrow "ARQUITECTURA" + h3 "5 containers, 1 VM, $0/mes"
- Diagrama centrado, ocupa 75% del espacio
- 3 callouts mínimos abajo: "5 servicios · 161 MB RAM · 17% del límite"

### Slide 4 — docker-compose.yml

Code-heavy slide pero legible:

- Eyebrow: "COMPOSICIÓN"
- H2: "5 servicios, total 570MB de RAM budget"
- **Snippet de código** (de PRESENTATION.md slide 3) — ~30 líneas YAML
  con syntax highlighting amber para keys, cream para values
- Callout abajo derecha: "Total memoria: **570MB / 956MB** = 60%"

### Slide 5 — Dockerfile

- Eyebrow: "DOCKERFILE"
- H2: "Patrón típico (digest service)"
- Snippet de código a la izquierda (10 líneas Dockerfile)
- Derecha: 4 decisiones clave en cards pequeñas:
  1. `python:3.11-slim` → 45MB base
  2. Requirements first → cache deps
  3. HEALTHCHECK declarativo
  4. Final image: 263MB

### Slide 6 — Demo

- Eyebrow: "DEMO"
- H2: "Subscribe → Confirm → Digest → Reply → PDFs"
- 5 mockups pequeños tipo wireframe en grid 2x3:
  1. Landing page
  2. Confirm email (inbox)
  3. Digest email
  4. Reply send
  5. PDFs received
- QR code grande en esquina inferior derecha — placeholder
  `{{ qr_code_url }}` con label "Subscribite ahora"

### Slide 7 — Resultado (métricas técnicas)

Tabla grande, hierarchy clara:

- Eyebrow: "RESULTADO · MÉTRICAS"
- 6 stats en grid 3x2, números enormes Georgia:
  - **$0** / mes
  - **161 MB** RAM (17%)
  - **5** containers
  - **2.4k** líneas Python
  - **28** ediciones archive
  - **~3 min** deploy

### Slide 8 — Lo que Docker resolvió

8 puntos en grid 4x2, cada uno con número grande Georgia + texto corto:

01. Aislamiento
02. Reproducibilidad
03. Memory limits declarativos
04. Restart automático
05. Volumes (code vs data)
06. Healthchecks integrados
07. Push to registry + atomic deploy
08. Dev = prod (mismo YAML)

### Slide 9 — Backup (Q&A anticipado, 1 sola slide)

Dense pero legible. 4 preguntas anticipadas en columnas:

- "¿Por qué no Kubernetes?"
- "¿Y si Oracle revoca free tier?"
- "¿Por qué SQLite y no Postgres?"
- "¿Cómo manejas secrets?"

Respuestas cortas (2-3 líneas cada una) de PRESENTATION.md.

### Slide 10 — Cierre

Espejo del Slide 1:
- H1: "Gracias"
- Sub: "Preguntas?"
- 3 links centered amber:
  - `arxivdaily.ignorelist.com` (live)
  - `github.com/f3r21/arxiv-digest` (repo)
  - QR code grande
- Footer: name del presentador

## Identidad visual

### Paleta (Charcoal Ember — el dark del proyecto)

| Token | Hex | Uso |
|---|---|---|
| `--bg` | `#13161a` | Background de cada slide |
| `--surface` | `#1a1e23` | Cards, código blocks |
| `--surface-elevated` | `#20252b` | Hover/focus, callouts |
| `--text` | `#ede9e0` | Body text (warm white) |
| `--text-muted` | `#86898e` | Secondary |
| `--text-faint` | `#5d6066` | Tertiary, hairlines |
| `--accent` | `#d99c5e` | Amber: SOLO en eyebrows, links, hairlines clave |
| `--border` | `#2d3137` | Hairlines |

**Restraint del amber**: máx 2-3 elementos por slide. Per `BRAND_VOICE.md`.

### Tipografía

- **Headers**: Georgia (serif), bold, letter-spacing tight
- **Body**: system sans (`-apple-system, BlinkMacSystemFont, ...`)
- **Code**: ui-monospace (Menlo, SF Mono)
- **Eyebrows**: small caps, letter-spacing 0.22em, amber, bold

### Escala (16:9 a 1920×1080)

- H1 hero: `clamp(80px, 8vw, 140px)`
- H2 section: `clamp(48px, 5vw, 80px)`
- H3 sub: 36px
- Body: 24px
- Eyebrow: 16px (small caps)
- Code: 18px

### Layout

- Padding generoso (96px de los bordes)
- Cada slide es un `<div class="slide">` con `width: 1920px; height: 1080px`
- Centrado horizontal y vertical donde aplique
- Hairlines `1px solid var(--border)` para separar secciones

## Anti-patterns (NO hacer)

Del `DESIGN_BRIEF.md` + adaptados a slides:

- ❌ Emoji decorativo (excepto en mockups del email donde sea contenido)
- ❌ Gradientes blob, glass effects, shadows pesadas
- ❌ Exclamation marks
- ❌ Stock-photo style
- ❌ "Revolutionary", "Game-changer", "Excited to share"
- ❌ Múltiples colores accent (solo amber)
- ❌ Sans-serif en headers (deben ser Georgia)
- ❌ Text dump — máx 7 lineas de body por slide

## Formato del output

Mismo pattern que el handoff anterior:

```
slides_handoff/
├── README.md                    ← integration notes para mí
├── slides/
│   ├── slide-01-title.html      ← cada slide standalone 1920×1080
│   ├── slide-02-problema.html
│   ├── slide-03-arquitectura.html
│   ├── slide-04-compose.html
│   ├── slide-05-dockerfile.html
│   ├── slide-06-demo.html
│   ├── slide-07-resultado.html
│   ├── slide-08-docker-resolvio.html
│   ├── slide-09-qa.html
│   └── slide-10-cierre.html
├── slides-combined.html         ← TODOS los slides en un solo HTML
│                                  con navegación (← → keys o click)
│                                  presentable directo desde browser
└── screenshots/                 ← PNG de cada slide para preview
    └── slide-NN.png
```

`slides-combined.html` debe permitir:
- Presentar en pantalla completa con F11
- Navegar con flechas izquierda/derecha y space
- ESC para salir / overview
- Quizá un indicador discreto "3 / 10" en la esquina

## Variables placeholder (te las paso después)

- `{{ presenter_name }}` → mi nombre
- `{{ qr_code_url }}` → `/static/demo-qr.png` (el QR ya está en `tools/demo-qr.png`)
- `{{ presentation_date }}` → fecha de la clase

## Decisiones que vos tomás (no tengo preferencia)

- ¿Transiciones entre slides? Si las hacés, sutiles (fade, no spin/3D)
- ¿Animaciones on-enter? Mínimas. Quizá fade del eyebrow + headline solo.
- ¿Cursor/pointer custom? No, default
- ¿Página de overview con grid de las 10 slides? Bonus si querés agregar

## Trust signal

Todo lo que digo en cada slide tiene evidencia. Métricas vienen del run
real en prod (verificable en el repo o vía SSH). Sin proyecciones, sin
"users targeted", sin features que no existen.

## Por qué este formato

Per market research (`docs/MARKET_RESEARCH.md`) y brand voice
(`docs/BRAND_VOICE.md`), el approach es "editorial restraint" — todo
debe sentirse hecho a mano, opinionado, sin la inflación visual de
slides corporativas típicas. La inspiración mental: cómo presentaría
Stratechery o The Browser un deck técnico — tipografía gigante,
hairlines, paleta limitada, sin chrome decorativo.

## Fidelidad esperada

Pixel-perfect. Esto va a la pantalla del proyector mañana en clase.
Texto debe ser legible desde la última fila. Contraste alto.
