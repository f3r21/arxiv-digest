# Feedback inline (todo el contenido pegable)

> Pegale ESTO a Claude Design. Es self-contained: incluye todos los
> snippets reales del repo que necesita para regenerar las slides
> correctamente.

---

Gracias por el ACK. Acá va todo el contenido inline ya que no tenés
acceso al repo. Reemplazá los strings exactos donde te indique.

## 1. Dockerfile real (slide 5)

El Dockerfile actual de `digest` es **12 líneas** y NO tiene `HEALTHCHECK`
inline. Reemplazá el snippet del slide 5 con este:

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

En el slide explicar las 4 decisiones (estas son las reales):

1. `python:3.11-slim` — 45MB base. Sin Alpine (rompe con wheels de algunas
   libs Python). Sin Debian full (overkill).
2. Requirements first → Docker cachea el layer de deps. Si solo cambia código,
   no se reinstala nada.
3. `python -u` → unbuffered stdout para que `docker logs` muestre print en tiempo
   real.
4. **Healthchecks viven en compose.yml** (no en Dockerfile), uniformes across
   los 5 services.

Cambiar:
- "Patrón típico, **10 líneas**" → "**12 líneas**"
- "Imagen final: 263 MB" → "**218 MB** (digest) / **264 MB** (subscriptions, la más pesada)"
- "Push en ~14s a GHCR" → "Push a **Docker Hub**, ~30-60s para 4 imágenes"

## 2. docker-compose snippet (slide 4)

Reemplazá el YAML con este:

```yaml
services:
  caddy:
    image: caddy:2-alpine        # oficial, no build
    restart: always
    deploy:
      resources:
        limits: { memory: 50M }

  subscriptions:                  # FastAPI + Jinja
    image: f999r/arxiv-digest-subscriptions:latest
    env_file: [.env.prod]
    deploy:
      resources:
        limits: { memory: 150M }

  digest:                         # cron 7am
    image: f999r/arxiv-digest-digest:latest
    env_file: [.env.prod]
    depends_on:
      subscriptions: { condition: service_healthy }
    deploy:
      resources:
        limits: { memory: 100M }

  listener:                       # poll Mailsac, reply PDFs
    image: f999r/arxiv-digest-listener:latest
    env_file: [.env.prod]
    deploy:
      resources:
        limits: { memory: 150M }

  translator:                     # EN→ES microservice
    image: f999r/arxiv-digest-translator:latest
    deploy:
      resources:
        limits: { memory: 120M }
```

**Legend table** (slide 4 derecha):
- caddy 50 MB
- subscriptions 150 MB
- digest 100 MB
- listener 150 MB
- translator 120 MB
- **Total: 570 MB**

## 3. Arquitectura (slide 3 SVG)

5 containers reales con sus roles. Reemplazá los nodos del diagrama:

```
External:
  arXiv API   (export.arxiv.org)
  MyMemory    (translation API, 50k chars/day free)
  Gmail SMTP  (500/day free)
  Mailsac     (inbox poll, 1500/mo free)
  healthchecks.io  (monitoring)
  Google Drive   (backup off-VM via rclone)

Inside Oracle VM (956 MB total RAM, AMD E2.1.Micro):

  caddy           → TLS termination, Let's Encrypt auto, reverse proxy
                    (50 MB limit, ~35 MB actual)

  subscriptions   → FastAPI web (/subscribe, /confirm, /manage,
                    /unsubscribe, /archive, /privacy, /terms)
                    (150 MB limit, ~46 MB actual)

  digest          → Python schedule lib, cron 7am ART, fetch arxiv → filter
                    per subscriber → translate → SMTP send → write archive
                    (100 MB limit, ~25 MB actual)

  listener        → Poll Mailsac inbox every 10min, parse reply numbers,
                    download PDFs from arXiv, SMTP attach + send back
                    (150 MB limit, ~23 MB actual)

  translator      → FastAPI microservice wrapping MyMemory API with
                    cache (hash → translation) for paper sharing across subs
                    (120 MB limit, ~57 MB actual)

Shared volume ./data (mounted in subscriptions, digest, listener):
  subscribers.db        SQLite WAL — emails, categories, keywords, tokens
  replies_processed.db  SQLite — dedup of processed Mailsac messages
  archive/{cat}/{date}.json  — public archive JSONs (SEO)
  public_digest_preview.json — last seed digest snapshot for /preview

Connections:
  Internet → caddy → subscriptions (HTTPS)
  digest → arXiv (HTTP)
  digest → translator (internal HTTP)
  digest → Gmail SMTP (outbound)
  digest → healthchecks.io ping (outbound)
  listener → Mailsac (HTTPS poll)
  listener → arXiv (HTTP, PDF download)
  listener → Gmail SMTP (outbound, with PDFs)
  digest/subscriptions/listener → ./data volume
```

Actualizar el "data volume" sub text del SVG:
- Actual: "SQLite WAL · PDF cache · embeddings"
- Real: "**SQLite WAL · archive JSONs**" (sin "PDF cache", sin "embeddings")

## 4. Métricas reales (slide 7)

Reemplazar las 6 stats con estos datos verificados:

| Stat | Valor | Meta |
|---|---|---|
| Costo mensual | **$0** | Oracle Free Tier · Always Free |
| RAM en producción | **~190 MB** | 20% del límite VM (956 MB) |
| Containers | **5** | caddy · subscriptions · digest · listener · translator |
| Código | **2.4k LOC** | Python · FastAPI · Jinja2 |
| Ediciones archivadas | **~30** | en 2 días de prod (cron diario) |
| Deploy | **~3 min** | build local → Docker Hub push → SSH deploy |

NO usar "28 días sin caídas" (mentira, llevamos 2 días).
NO usar "git push → producción" (no hay CI, deploy es manual).

## 5. Docker resolvió (slide 8)

Cambios puntuales en los 8 items:

- Item 03 (Memory limits): cambiar `mem_limit: 120m` por `mem_limit: 150m`
  (más cercano a real)
- Item 04 (Restart): cambiar `restart: unless-stopped` por **`restart: always`**
- Item 06 (Healthchecks): cambiar "Una línea en el Dockerfile" por
  "**Una línea en `compose.yml`**" (porque ahí los tenemos uniformes)
- Item 07 (Atomic deploy): cambiar "Push a GHCR" por **"Push a Docker Hub"**

## 6. Q&A backup (slide 9)

Reemplazar las 4 respuestas con estas:

**¿Por qué no Kubernetes?**
> Una VM con 956 MB de RAM. El control plane de k8s ya pide ~2 GB.
> Para 5 servicios sin escalado horizontal, `docker-compose` es el sweet
> spot — k8s sería overengineering. Cuando crezcamos más allá de 1 VM
> lo reconsideramos.

**¿Y si Oracle revoca free tier?**
> Backups diarios a Google Drive vía `rclone` (rotación 30 días) + local
> `/var/backups/arxiv` (7 días). El `compose.yml` es portable: misma imagen,
> otro proveedor. Hetzner o Fly.io ~$5/mes, downtime estimado 10 minutos.

**¿SQLite y no Postgres?**
> Single-writer, <10k filas/día, sin replicación necesaria. SQLite en
> WAL mode sobra. Postgres añadiría 200 MB de RAM y operación — sin
> beneficio medible al volumen actual.

**¿Cómo manejás secrets?**
> `.env.prod` excluido del git, `chmod 600` en la VM. Tres secrets:
> `SMTP_PASS` (Gmail App Password), `SUBSCRIPTIONS_SECRET` (firma de
> tokens manage/unsubscribe), `MAILSAC_API_KEY` (inbox poll). No hay CI
> todavía — deploy manual via SSH.

## 7. Problema (slide 2)

Correcciones:
- "**~500 papers/día solo en cs.LG**" → "**~200 papers/día en cs.LG**"
- Pain "Fricción para guardar": cambiar "**Tres clicks, login, captcha,
  archivo en Downloads/**" por:
  > "Tres clicks por paper: abstract → PDF tab → save. Diez veces al día
  > = mucha fricción acumulada."
- Pain "Personalización pobre": mantener, está bien.
- Pain "Gap en herramientas abiertas": mantener, está validado.

## 8. Cierre (slide 10)

- Footer "Open source · MIT" → mantener (yo agrego el archivo LICENSE
  antes de la presentación).

## Speaker notes — en español, tiempo target

Por favor agregá speaker notes en español para cada slide siguiendo
este formato:

```html
<aside class="notes">
  [Qué decir — 2-3 oraciones]

  Killer line: [una frase que el público recuerde]

  Tiempo target: [N segundos]
</aside>
```

Distribución 10 min total:

| Slide | Tiempo |
|---|---|
| 01 Title | 15 seg |
| 02 Problema | 90 seg |
| 03 Arquitectura | 150 seg ← la más densa |
| 04 docker-compose | 90 seg |
| 05 Dockerfile | 60 seg |
| 06 Demo | 120 seg ← demo, dejá respirar |
| 07 Resultado | 60 seg |
| 08 Docker resolvió | 75 seg |
| 09 Q&A backup | skip (solo si pregunta) |
| 10 Cierre | 15 seg + Q&A |

Voz de las notes (per docs/BRAND_VOICE.md):
- editorial, understated, concreta
- sin emoji
- sin exclamation marks
- castellano rioplatense neutro
- ejemplos > abstracciones

## PDF export

Sí, mantené el deck-stage built-in print. Lo voy a usar para exportar PDF
con Cmd+P, una página por slide. No es necesario que generes PDF aparte.

## Si necesitás más contexto

Lo que sí podés asumir verídico de mi audit table inicial:
- Stack: FastAPI + Jinja2 (NO Flask)
- HTTPS via Caddy auto Let's Encrypt
- Cron via Python `schedule` lib (NO crontab del OS)
- SMTP: Gmail App Password
- Registry: Docker Hub (NO GHCR, NO ECR)
- Backup: Google Drive con rclone (NO S3)
- VM: Oracle Cloud E2.1.Micro AMD, 956 MB RAM, $0/mes Always Free
- Memory uso real idle: ~190 MB total / 5 containers

Cuando tengas el handoff v2 listo, mandame el link.
