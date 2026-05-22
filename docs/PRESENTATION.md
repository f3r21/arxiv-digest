# Presentación de clase — The Daily Abstract

**Caso de uso Docker · 10 minutos · Cloud Computing**

> Live: https://arxivdaily.ignorelist.com
> Repo: https://github.com/f3r21/arxiv-digest
> QR para suscribirse durante la clase: `tools/demo-qr.png`

---

## Slide 0 — Title (15 seg)

# The Daily Abstract
## Newsletter diario de arXiv con reply-to-PDF

Indie · open source · $0/mes · self-hosted en Oracle Free Tier

*Tu nombre · Cloud Computing · 2026-05-22*

> **Notas orador**: "Hola, hice un newsletter para investigadores que sufrimos
> arXiv. La gracia técnica es que está hostado en una VM gratuita corriendo
> 5 containers Docker que se comunican para hacer todo el trabajo."

---

## Slide 1 — Problema (1.5 min)

# Problema

arXiv publica **~500 papers/día solo en cs.LG**

Los investigadores enfrentamos:
- **Saturación**: skimear el listing diario tarda demasiado
- **Fricción para guardar**: cada PDF requiere 3-4 clicks (search → abs → PDF tab → download)
- **Personalización pobre**: las herramientas existentes son inglés-first y/o requieren plataforma cerrada
- **No hay tool open + free + Spanish-aware** que cierre el loop email → PDF

> **Notas orador**: "Un investigador típico abre arXiv todos los días y tiene
> que rebrowserlo desde 0. arxiv-sanity de Karpathy fue genial pero está
> abandonado desde marzo 2025. Scholar Inbox está en inglés. Mi tesis: hay
> espacio para una tool más opinionada, más editorial, con un workflow más
> rápido — específicamente el 'reply al email con números, recibí los PDFs'."

---

## Slide 2 — Arquitectura (2.5 min)

# Arquitectura: 5 containers, 1 VM, $0/mes

```
┌─────────────────── Oracle Cloud E2.1.Micro (1GB RAM) ────────────────────┐
│                                                                          │
│  ┌────────┐         ┌──────────────────┐         ┌────────────────────┐  │
│  │ caddy  │ <─────> │  subscriptions   │ <─────> │   SQLite (vol)     │  │
│  │ :443   │         │  FastAPI:8000    │         │  subscribers.db    │  │
│  │ TLS    │         │  /, /subscribe,  │         │  + archive/*.json  │  │
│  │        │         │  /archive, ...   │         └────────────────────┘  │
│  └────────┘         └──────────────────┘                ▲                │
│      ▲                       ▲                          │                │
│      │                       │ shares DB                │ writes/reads   │
│      │ HTTPS                 │                          │                │
│      │                       ▼                          │                │
│      │              ┌──────────────────┐                │                │
│      │              │     digest       │ ───────────────┘                │
│      │              │  cron 7am daily  │                                 │
│      │              │  fetch → filter  │ ──> SMTP ──> Gmail SMTP ──> 📬  │
│      │              │  → translate     │                                 │
│      │              └──────────────────┘                                 │
│      │                       │ uses                                      │
│      │                       ▼                                           │
│      │              ┌──────────────────┐                                 │
│      │              │   translator     │                                 │
│      │              │  FastAPI:8001    │                                 │
│      │              │  EN → ES         │ ──> MyMemory API (free)         │
│      │              └──────────────────┘                                 │
│      │                                                                   │
│      │              ┌──────────────────┐                                 │
│      └─────────────>│    listener      │ <─── polls Mailsac inbox        │
│                     │  poll every 10m  │                                 │
│                     │  reply parsing   │ ──> downloads PDFs from arXiv   │
│                     │  → SMTP attach   │ ──> Gmail SMTP ──> user 📎      │
│                     └──────────────────┘                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                                                            
   ─── External services (gratuitos) ──────────────────────────────────
   📤 Gmail SMTP (500/día)    📥 Mailsac inbox (1500 polls/mes)
   🌐 arXiv API               🌍 MyMemory translate (50k chars/día)
   📊 Healthchecks.io         💾 Google Drive (backup)
```

**Decisiones de diseño clave:**

1. **5 containers vs monolito** — cada servicio tiene un lifecycle distinto
   (subscriptions = web stateful, digest = cron, listener = poll loop, etc).
   Separar permite restart selectivo y memory limits por servicio.

2. **SQLite con volume compartido** — sin DB server propio. Para 1-1000 users
   es perfecto, WAL mode permite multi-process concurrent reads.

3. **Email como interfaz** — no requiere mobile app, no requiere login,
   funciona en cualquier cliente. Reply→PDF cierra el loop sin friction.

4. **Caddy adelante** — TLS automático vía Let's Encrypt, sin config manual.

> **Notas orador**: "Cada container es lo más chico posible. El digest se
> despierta una vez por día a las 7am, manda los emails, vuelve a dormir.
> El listener pollea Mailsac cada 10 minutos. La translator es un microservice
> wrapper sobre MyMemory para cachear traducciones entre subscribers (un
> mismo paper solo se traduce una vez). Caddy resuelve TLS sin tocarlo."

---

## Slide 3 — docker-compose.yml (2 min)

# Composición de servicios

```yaml
services:
  caddy:                          # TLS termination + reverse proxy
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data           # persiste certificados Let's Encrypt
    deploy:
      resources:
        limits: {memory: 50M}      # Caddy es eficiente

  subscriptions:                   # FastAPI web
    image: f999r/arxiv-digest-subscriptions:latest
    env_file: [.env.prod]
    volumes:
      - ./data:/app/data           # SQLite + archive JSONs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    deploy:
      resources:
        limits: {memory: 150M}

  digest:                          # Cron + arXiv fetch + SMTP send
    image: f999r/arxiv-digest-digest:latest
    env_file: [.env.prod]
    volumes:
      - ./data:/app/data           # mismo volume que subscriptions
    depends_on:
      subscriptions: {condition: service_healthy}
      translator: {condition: service_healthy}
    deploy:
      resources:
        limits: {memory: 100M}

  translator:                      # microservice EN→ES
    image: f999r/arxiv-digest-translator:latest
    deploy:
      resources:
        limits: {memory: 120M}

  listener:                        # Reply→PDF processor
    image: f999r/arxiv-digest-listener:latest
    env_file: [.env.prod]
    deploy:
      resources:
        limits: {memory: 150M}

volumes:
  caddy-data:
```

**Total memoria budget: 570MB / 956MB de VM = 60%** (vs límite Oracle 1GB).

> **Notas orador**: "5 servicios, total 570MB de RAM budget. Como ven, todos
> los containers son chicos. El detalle clave es que `digest` y `subscriptions`
> comparten el volume `./data` para que ambos puedan leer/escribir la misma
> SQLite. El digest tiene `depends_on: condition: service_healthy` para no
> arrancar hasta que la DB esté lista."

---

## Slide 4 — Dockerfile (1 min)

# Dockerfile típico (digest)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY templates ./templates
COPY tests ./tests

HEALTHCHECK --interval=30s --timeout=3s --retries=5 \
  CMD test -f /tmp/alive

CMD ["python", "-u", "main.py"]
```

**Decisiones:**
- **`python:3.11-slim`** — 45MB base vs 900MB de la full image
- **Copy requirements PRIMERO** → Docker cachea el layer de deps (rebuilds ~5s)
- **Sin user `root`** del slim por defecto — para prod real agregaria `USER nobody`
- **HEALTHCHECK** — `digest` toca `/tmp/alive` cada 30s en su loop principal,
  permite a Docker reportar el container como `(unhealthy)` si se cuelga

Final image size: **263MB** (incluye Python, dependencies, templates, código).

> **Notas orador**: "Slim base ahorra 850MB. El orden importa: requirements
> primero para cachear deps. El healthcheck es simple: el daemon toca
> /tmp/alive cada 30s; si Docker no ve cambios en 30s con 5 retries, marca
> el container unhealthy y restart: always lo recicla."

---

## Slide 5 — Demo en vivo (3 min — opcional)

# Demo (live o screenshots)

**Opción A — Live**:

1. Mostrar `https://arxivdaily.ignorelist.com` (landing editorial Stratechery)
2. Subscribe con email del profesor → "pending confirmation"
3. Mostrar email en su inbox
4. Click confirm → "You're in"
5. Trigger digest manual desde terminal:
   ```bash
   ssh ubuntu@... 'docker compose ... exec digest python -c "from main import run_digest; run_digest()"'
   ```
6. Mostrar email digest llegar (~30s) con 4 papers
7. Reply con "1 3" → 30s después llegan 2 PDFs adjuntos
8. Mostrar `/archive` público con todas las ediciones SEO-indexables

**Opción B — Screenshots si no hay wifi**:
- `docs/launch/demo.png` (landing)
- Screenshot del Gmail con el digest editorial
- Screenshot del Mailsac inbox capturing el reply
- Screenshot del reply email con PDFs attached

**QR code**: `tools/demo-qr.png` — proyectar para que clase se suscriba live.

> **Notas orador**: "Si tengo wifi hago el demo live. Sino, screenshots.
> El highlight es el flow completo: subscribe, recibo el email, contesto
> con números, me llegan los PDFs. Todo via 5 containers Docker conversando
> entre sí en una VM gratuita."

---

## Slide 6 — Resultado (1 min)

# Resultado

### Métricas técnicas
| Cosa | Valor |
|---|---|
| **Costo mensual** | $0 (Oracle Free Tier + Gmail SMTP + Mailsac + MyMemory) |
| **RAM total usada** | 161 MB / 956 MB disponibles (17%) |
| **Containers running** | 5 (caddy, subscriptions, digest, listener, translator) |
| **Líneas de código (services)** | ~2,400 Python |
| **Archive público generado** | 28 ediciones diarias indexables (1 día de operación real) |
| **Tiempo build + push + deploy** | ~3 min (incremental) |
| **Tests** | unit + integration en pytest |
| **Commits** | 34 (este sprint) |

### Métricas funcionales
- ✅ Cron diario autónomo verificado (cron 7am dispara → digest email)
- ✅ Reply→PDF flow funcional end-to-end (verificado con email real hoy)
- ✅ Backup off-VM a Google Drive (30d rotation)
- ✅ Monitoring vía Healthchecks.io (alerta email si falla 25h)
- ✅ HTTPS automático (Let's Encrypt vía Caddy)
- ✅ Security: HSTS, CSP, X-Frame-Options, COOP, CORP
- ✅ SEO: sitemap.xml dinámico, JSON-LD, OG meta

### Lo que Docker resolvió aquí
1. **Aislamiento** — cada servicio falla sin afectar a los otros
2. **Reproducibilidad** — `docker compose up` y el stack arranca igual
   en mi Mac, en CI, o en Oracle. Cero "funciona en mi máquina"
3. **Memory limits** — quita el riesgo de que un container se coma toda la VM
4. **Restart automático** — `restart: always` resuelve transient failures
5. **Volumes** — separación clara: el code es immutable (image),
   los datos persisten (volume)
6. **Healthchecks declarativos** — Docker sabe automáticamente cuándo un
   container está roto y reportarlo en `docker ps`
7. **Push to registry, pull en VM** — el deploy es atomic. Si la nueva
   imagen rompe, rollback es `docker compose pull --policy missing`
8. **Dev = prod** — el mismo `docker-compose.yml` que corro en mi laptop
   con MailHog para testing es el que corre en prod con Gmail SMTP, solo
   cambia el `.env`

> **Notas orador**: "Lo más importante de Docker en este proyecto no fue la
> portabilidad — fue la composición. Tengo 5 servicios con lifecycles muy
> distintos: uno es un cron diario, otro es web stateful, otro es un poll
> loop, otro es un microservice de translation. Sin Docker hubiera tenido
> que orquestar todo con systemd, supervisord, y crontab manualmente.
> Con docker-compose son 5 stanzas en un YAML y el stack entero arranca."

---

## Backup slides (preguntas anticipadas)

### "¿Por qué no Kubernetes?"
Para 1 VM con 5 containers, Kubernetes es overkill. Helm, etcd, kubelet,
network plugins — todo eso para coordinar lo que docker-compose hace
en 90 líneas YAML. K8s tiene sentido a partir de N pods replicados con
auto-scaling, lo que este proyecto no necesita por ahora.

### "¿Y si Oracle revoca tu free tier?"
Backup automático a Drive con 30 días de rotation. Restore es bajar el
tar.gz, untar en `./data/` y `docker compose up`. Migración a otra VM
(Hetzner $4/mes, GCP free tier) sería ~30 minutos.

### "¿Cómo manejas secrets?"
`.env.prod` en la VM (gitignored). Variables sensibles: SMTP password
(Gmail App Password), Mailsac API key, signing secret de tokens. No
están en el repo ni en la image.

### "¿Por qué SQLite y no Postgres?"
Para 1-1000 users, SQLite con WAL mode es más rápido y simple. Cero
configuración, backup es copiar un archivo. Si necesitamos a 10k+ users
o multi-region, migración a Postgres es un cambio de driver + alguna
adaptación de queries.

### "¿Tests?"
`pytest` para unit + integration. `docker-compose.yml` levanta MailHog
para tests de SMTP en dev. CI no está aún configurado.

### "Reply→PDF, ¿cómo funciona técnicamente?"
1. Cada digest se envía con `Reply-To: arxiv-replies@mailsac.com`
2. User responde "1 3" desde su Gmail
3. La respuesta llega a Mailsac inbox (gratis hasta 1500 polls/mes)
4. Listener container pollea cada 10 min vía API REST
5. Parsea los números del cuerpo del email (ignorando quoted text)
6. Mapea sender → subscriber → último digest snapshot (SQLite)
7. Descarga los PDFs de arXiv (parallel)
8. SMTP attach + send back via Gmail
9. Marca el msg como procesado + delete del inbox

---

## Cierre (15 seg)

# Gracias

- Live: https://arxivdaily.ignorelist.com
- Repo: https://github.com/f3r21/arxiv-digest
- QR para subscribirse acá [proyectar `tools/demo-qr.png`]

**Preguntas?**
