# Feedback para Claude Design — slides v2

> Copy-paste este documento entero en Claude Design para regenerar las slides
> con datos reales del proyecto. **Verifiqué cada afirmación contra el repo
> y prod.** Lista priorizada: CRITICAL (datos falsos), HIGH (mejoras de
> claridad), NICE (cosmetic).

---

## TL;DR

Las slides están **visualmente excelentes** — la composición, el tipo, el
restraint editorial, la grilla, todo bien. **Los datos están inventados** en
varios lugares porque no tuviste acceso al ARCHITECTURE.md / Dockerfiles
reales. Acá tenés los datos verídicos para reemplazar.

## Datos reales del proyecto (source of truth)

### Containers en producción (5)

| nombre | image | memory limit | uso real idle |
|---|---|---|---|
| **caddy** | `caddy:2-alpine` (oficial) | 50 MB | ~35 MB |
| **subscriptions** | `f999r/arxiv-digest-subscriptions` | 150 MB | ~46 MB |
| **digest** | `f999r/arxiv-digest-digest` | 100 MB | ~25 MB |
| **listener** | `f999r/arxiv-digest-listener` | 150 MB | ~23 MB |
| **translator** | `f999r/arxiv-digest-translator` | 120 MB | ~57 MB |

**Total budget**: 570 MB. **Uso real**: ~187 MB (~20% de la VM de 956 MB).

### Imágenes Docker (tamaño en disco)

- subscriptions: 264 MB
- listener: 210 MB
- digest: 218 MB
- translator: 256 MB
- caddy: 35 MB (oficial)

### Registry

- **Docker Hub** (`f999r/arxiv-digest-*`). **NO GHCR**.

### Dockerfile real (digest, 12 líneas — no 10)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY templates ./templates
COPY tests ./tests

CMD ["python", "-u", "main.py"]
```

NO tiene `HEALTHCHECK` en el Dockerfile. Los healthchecks están en
`docker-compose.prod.yml`:
- subscriptions: HTTP GET `/health` cada 15s
- digest: `test -f /tmp/alive` cada 30s
- listener: `test -f /tmp/alive`

### compose.prod.yml real

- `restart: always` (no `unless-stopped`)
- `env_file: [.env.prod]` para los services con secrets
- `depends_on: condition: service_healthy` chain
- 5 services, no 4

### Stack real

- Web: FastAPI + Jinja2 (no Flask)
- HTTP egress: arxiv API, MyMemory translator, Gmail SMTP, Mailsac inbox
- DB: SQLite WAL en volume `./data`
- HTTPS: Caddy auto Let's Encrypt
- Cron: Python `schedule` lib (no crontab del OS)
- SMTP: Gmail App Password (no Brevo ni Resend)
- Inbox: Mailsac (poll 10min)
- Monitor: healthchecks.io ping
- Backup: rclone a Google Drive + local /var/backups (NO S3, NO cifrado)

### Secrets reales (3 en .env.prod)

- `SMTP_PASS` (Gmail App Password)
- `SUBSCRIPTIONS_SECRET` (signing tokens manage/unsubscribe)
- `MAILSAC_API_KEY` (inbox poll)

**No hay arXiv token** (la API no requiere auth).
**No hay GitHub Secrets** (no hay CI, deploy es manual).

### Deploy real

- Build local en Mac (`./tools/build_and_push.sh`)
- Push a Docker Hub
- SSH a VM Oracle, `git pull` + `docker compose pull` + `up -d --force-recreate`
- Tiempo total: ~3 min incremental (correcto)
- **NO es `git push → producción`** — es manual

---

## Correcciones por slide

### Slide 1 — Title

✅ OK. Nada para cambiar.

### Slide 2 — Problema

**CRITICAL — dato falso**:
- "~500 papers/día solo en cs.LG" → real es **~150-250/día** (arxiv-sanity
  stats). 500 es exageración. **Cambiar a ~200**.

**HIGH — mentiras menores que ofenden al público técnico**:
- "Fricción para guardar... Tres clicks, login, captcha, archivo en Downloads/"
  → arXiv NO requiere login ni captcha. **Cambiar a**: "Tres clicks por
  paper: abstract → PDF tab → save. Diez veces al día = mucha fricción."
- "RSS muerto" → arXiv tiene RSS funcional. **Cambiar a**: "RSS sin
  personalización por categoría + keyword."

**Mantener correcto**:
- "Personalización pobre" ✓
- "Gap en herramientas abiertas" ✓ (validado en MARKET_RESEARCH.md)

### Slide 3 — Arquitectura

**CRITICAL — los 5 services están INVENTADOS**:

Reemplazar en el SVG:
- `nginx` → `caddy` (memoria 60→50 MB)
- `web` ("Flask · subscribe") → `subscriptions` ("FastAPI · web", memoria 120→150 MB)
- `ingest` ("Python · scheduler") → **REMOVER** (no existe servicio "ingest";
  el digest hace el fetch directo) **O reemplazar por `translator`**
  ("EN→ES microservice", 120 MB)
- `digest` ("Cron · 7am · ranker", 180 MB) → `digest` ("Cron · 7am · ranker", 100 MB)
- `mail` ("Reply · PDF handler", 110 MB) → `listener` ("Poll Mailsac · reply PDFs", 150 MB)

**HIGH — flow del diagrama**:
- "arXiv → ingest → digest" está mal: el digest hace fetch directo de arXiv,
  no via un servicio separado. **Cambiar a**: "arXiv → digest" (un solo arrow).
- Agregar arrow "digest → translator" (cuando traduce).
- Agregar arrow "listener → arXiv" (cuando descarga PDFs para reply).

**Data volume description**:
- Actual: "SQLite WAL · PDF cache · embeddings"
- Real: "SQLite WAL · archive JSONs"
- **No hay embeddings** (no usamos LLMs). **No hay PDF cache** (descargamos
  PDFs on-demand y los borramos post-send).

### Slide 4 — docker-compose

**CRITICAL — service names + memory wrong** (mismas correcciones que slide 3):

```yaml
services:
  caddy:
    image: caddy:2-alpine
    mem_limit: 50m

  subscriptions:
    build: ./subscriptions
    mem_limit: 150m

  digest:        # cron 7am, NO "ranker"
    build: ./digest
    mem_limit: 100m

  listener:      # poll Mailsac, reply con PDFs
    build: ./listener
    mem_limit: 150m

  translator:    # EN→ES microservice
    build: ./translator
    mem_limit: 120m
```

**Legend table**:
- caddy 50 MB
- subscriptions 150 MB
- digest 100 MB
- listener 150 MB
- translator 120 MB
- Total: **570 MB** (este número estaba correcto por coincidencia)

### Slide 5 — Dockerfile

**CRITICAL — código falso**:
- `HEALTHCHECK --interval=5m --timeout=10s CMD python -m digest.healthcheck`
  → **el Dockerfile real NO tiene HEALTHCHECK**. Los healthchecks viven en
  `compose.yml`. Remover la línea del Dockerfile o aclarar "del compose, no
  del Dockerfile".
- `CMD ["python", "-m", "digest.main"]` → real es `CMD ["python", "-u", "main.py"]`

**HIGH — números**:
- "Patrón típico, **10 líneas**" → real son **12 líneas**. Actualizar.
- "Imagen final: 263 MB" → real digest image es **218 MB**, subscriptions
  **264 MB**, listener **210 MB**, translator **256 MB**. Si querés un
  número solo, decir **"218-264 MB según servicio"** o cita
  subscriptions específicamente (que es la más grande con templates y CSS).
- "Push en ~14s a GHCR" → es **Docker Hub** (no GHCR). El push completo
  toma ~30-60s para 4 imágenes (~948 MB total layers).

**Dockerfile real para citar**:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
COPY templates ./templates
COPY tests ./tests
CMD ["python", "-u", "main.py"]
```

(El healthcheck lo agregamos en compose.yml para tener un patrón uniforme
across services en vez de duplicarlo por Dockerfile.)

### Slide 6 — Demo

✅ OK conceptualmente. Los wireframes son ilustrativos.

**NICE — detalle de timing**:
- "~90 segundos después" → real es ~**30 segundos** (Mailsac poll cada 10min
  pero cuando lo procesa, download + SMTP send es ~30s). Si querés mantener
  90s para acomodar el worst-case del poll, está OK.

### Slide 7 — Resultado

**CRITICAL — datos falsos**:
- "**161 MB RAM**" → real es **~187 MB** (idle). **Actualizar a "190 MB"** o
  decir "**~190 MB en idle**".
- "**17% del límite**" → real es **~20%**. Actualizar.
- "**nginx · web · ingest · digest · mail**" → **WRONG names**. Real:
  **caddy · subscriptions · digest · listener · translator**.
- "**28 días seguidos sin caídas**" → **MENTIRA**. El sistema arrancó en
  prod hace ~2 días. **Cambiar a**: "**~30 ediciones archivadas en 2 días
  de prod**" o quitar la métrica de "días sin caídas" entera.
- "**git push → producción**" → **MENTIRA**. No hay CI/CD. Es manual:
  build local + push Docker Hub + SSH deploy. **Cambiar a**: "**build →
  push → SSH deploy** (~3 min)".

### Slide 8 — Docker resolvió

**CRITICAL — datos falsos**:
- "`restart: unless-stopped`" → real usamos `restart: always`. **Cambiar a
  `always`** (más agresivo, lo querés en prod).
- "Push a GHCR · compose pull · up" → es **Docker Hub** (no GHCR). **Cambiar
  a**: "Push a Docker Hub · compose pull · up".

**HIGH — claim debatible**:
- "Healthchecks: Una línea en el Dockerfile reemplaza un script de
  monitoring" → en nuestro caso los healthchecks están en compose.yml, no
  Dockerfile (corregir similar a slide 5). **Cambiar a**: "Una línea en
  compose.yml reemplaza..."

### Slide 9 — Q&A

**CRITICAL — datos falsos**:
- "Backups diarios **cifrados a S3**" → real es **Google Drive con rclone**
  (no S3, no cifrados — Drive ya cifra at-rest, pero no usamos GPG en el
  tar.gz). **Cambiar a**: "Backups diarios a Google Drive (rclone, rotación
  30 días) + local /var/backups (7 días)".
- "En CI vienen de **GitHub Secrets**" → **NO HAY CI**. **Cambiar a**:
  "Solo en `.env.prod` en la VM (chmod 600). Sin CI por ahora — deploy
  manual via SSH."
- "3 secrets (SMTP, sign key, **arXiv token**)" → arXiv API NO requiere
  token. Real son: SMTP_PASS, SUBSCRIPTIONS_SECRET, MAILSAC_API_KEY.
  **Cambiar a**: "3 secrets: SMTP password, signing key, Mailsac API key".

**HIGH — claim adicional util**:
- Para "¿Por qué no Kubernetes?" agregar línea: "Cuando crezcamos más allá
  de 1 VM con 5 servicios, lo reconsideramos. Today: docker-compose hace
  el 90% del trabajo de k8s con 1% de la complejidad."

### Slide 10 — Cierre

**NICE**:
- "Open source · MIT" → **El repo no tiene archivo LICENSE todavía**. Antes
  de la presentación, agregar `LICENSE` con MIT estándar O cambiar el
  footer a "Open source" sin "MIT".

---

## Cambios cosmetic (sin urgencia)

1. **Slide 3 callouts**: actualizar "161 MB RAM en producción" → "~190 MB"
   y "17% del límite" → "~20%".

2. **Subject line del email mockup (slide 6)**: actualmente dice "Vol. I ·
   No. 28" — real es "**The Daily Abstract No. 6 - 2026-05-22 - 4 papers**"
   (subject completo del send_digest). Si querés realismo, actualizar.

3. **arxiv IDs en los mockups del slide 6** (2511.0142, 2511.0188, 2511.0203)
   → reemplazar con IDs reales del archive: **1706.03762** (Vaswani Attention),
   **2310.06825** (Mistral 7B), **2106.09685** (LoRA). Hace el demo más
   creíble.

---

## Lo que NO necesita cambio

- Toda la tipografía (Georgia + system sans + mono) ✓
- Paleta Charcoal Ember ✓
- Layout 1920x1080 ✓
- Navegación deck-stage ✓
- Restraint del amber ✓
- Estructura de 10 slides ✓
- Eyebrow/h2/code 24px (correcta decisión vs el brief original) ✓
- Tagline editorial "indie · open source · $0/mes" ✓
- Mensaje principal del problema (saturación + fricción + gap) ✓

---

## Para el regenerate

Cuando regenerés, **leé estos archivos del repo** que yo no te puse en el
prompt inicial pero ahora están actualizados:

- `docs/ARCHITECTURE.md` — diagrama Mermaid + tabla de decisiones reales
- `docker-compose.prod.yml` — services + memory real
- `digest/Dockerfile` — el Dockerfile más típico (12 líneas)
- `subscriptions/Dockerfile` — similar pero con `static/` extra
- `tools/backup_local.sh` y `tools/backup_drive.sh` — la real backup story
- `docs/RUNBOOK.md` — todos los detalles operacionales validados en prod
- `docs/MARKET_RESEARCH.md` — references para validar el "gap en
  herramientas abiertas" del slide 2

## Speaker notes (sí, dale)

Sí, agregá speaker notes en español. Para cada slide:
- 2-3 oraciones de qué decir
- 1 línea con la "killer line" (la frase que vale la pena que el público
  recuerde)
- Tiempo target (en segundos)

Total target: 10 min. Distribuir:
- Slide 1: 15 seg
- Slide 2: 90 seg (más tiempo, set the scene)
- Slide 3: 150 seg (la slide más densa, dejar absorber el diagrama)
- Slide 4: 90 seg
- Slide 5: 60 seg
- Slide 6: 120 seg (demo, dejarlo respirar)
- Slide 7: 60 seg
- Slide 8: 75 seg
- Slide 9: skip a menos que pregunten (backup)
- Slide 10: 15 seg + Q&A
