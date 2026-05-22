# Runbook — The Daily Abstract

> Troubleshooting de los problemas más probables en prod.
> Lee de arriba a abajo cuando algo se rompa.

## Telemetria minima

| Donde | Que muestra |
|---|---|
| https://healthchecks.io | Si el digest cron de las 7am (UTC-3) corrio. Alerta si no llega ping en 25h. |
| `ssh ubuntu@144.22.43.121 'docker ps'` | Cuales containers estan up + healthy. |
| `ssh ubuntu@144.22.43.121 'docker stats --no-stream'` | RAM y CPU live por container. |
| `ssh ubuntu@144.22.43.121 'free -h'` | RAM total libre de la VM. |
| `tail -100 /var/log/arxiv-backup.log` | Si el backup local diario corrio. |
| Logs por container | `docker compose -f docker-compose.prod.yml --env-file .env.prod logs <service> --tail 50` |

## Comandos `ssh` rapidos

```bash
SSH() { ssh ubuntu@144.22.43.121 "$@"; }
COMPOSE() { SSH "cd ~/arxiv-digest && docker compose -f docker-compose.prod.yml --env-file .env.prod $*"; }

# Status de todos los containers
SSH 'docker ps'

# Logs ultimos 50 lines per servicio
COMPOSE 'logs digest --tail 50'
COMPOSE 'logs subscriptions --tail 50'
COMPOSE 'logs listener --tail 50'
COMPOSE 'logs caddy --tail 50'

# Restart un service
COMPOSE 'restart digest'

# Pull nueva imagen + restart
COMPOSE 'pull digest && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate digest'

# Trigger digest manualmente
COMPOSE 'exec digest python -c "from main import run_digest; run_digest()"'

# Inspeccionar DB
COMPOSE 'exec subscriptions python -c "import sqlite3; c = sqlite3.connect(\"/app/data/subscribers.db\"); [print(r) for r in c.execute(\"SELECT id,email,confirmed_at,unsubscribed_at FROM subscribers\")]"'
```

---

## Problemas comunes y como arreglarlos

### 1. "Healthchecks alert: digest no corrio en 25h"

Causas posibles, en orden de probabilidad:

1. **arXiv multi-cat query con parens** → 0 papers → digest skip. **Ya fixeado en commit `80b4967`** pero verificar:
   ```bash
   COMPOSE 'exec digest python -c "from arxiv_client import _build_search_query; print(_build_search_query([\"cs.LG\",\"cs.AI\"]))"'
   # Debe imprimir: cat:cs.LG+OR+cat:cs.AI (SIN parens)
   ```

2. **arXiv rate-limited el IP de Oracle**. Test directo:
   ```bash
   SSH 'curl -s "https://export.arxiv.org/api/query?search_query=cat:cs.LG&max_results=5" | grep -c "<entry>"'
   # Debe imprimir: 5
   ```
   Si imprime 0: arXiv block. Mitigacion: esperar 1-2h o cambiar IP/proxy.

3. **Container digest down**. Check status, restart si hace falta:
   ```bash
   SSH 'docker ps -a | grep digest'
   COMPOSE 'restart digest'
   ```

4. **Cron disabled o `schedule` corrupto**. El daemon usa `schedule` lib en loop:
   ```bash
   COMPOSE 'logs digest --tail 20 | grep -i "scheduler\|next"'
   ```

5. **SMTP fallo todos los retries**. Gmail tira `5.7.0 cuenta no activada` → migrate provider:
   ```bash
   COMPOSE 'logs digest --tail 50 | grep -iE "error|smtp"'
   ```

### 2. "Email no llega aunque digest haya enviado"

1. **Gmail rate-limit (500/dia free)**: si N suscriptores > 500/dia, Gmail rebota. Migration a Postmark / SES.

2. **App Password rotado/revocado**: en Google Account → Security → 2FA → App Passwords. Crear nuevo, actualizar `.env.prod`:
   ```bash
   SSH 'cd ~/arxiv-digest && sed -i "s|^SMTP_PASS=.*|SMTP_PASS=NEW_APP_PASSWORD|" .env.prod'
   COMPOSE 'restart digest subscriptions listener'
   ```

3. **Receiver lo marco como spam**. Check Gmail "Spam" folder o el `Junk` del proveedor.

### 3. "Reply para PDFs no llega"

Flow: Reply → Mailsac inbox → listener polls cada 10min → match sender → download PDFs → SMTP reply.

1. **Reply no esta en Mailsac** (no llego del proveedor del usuario):
   ```bash
   SSH 'docker exec arxiv-listener python -c "
   import os, requests
   k = os.environ[\"MAILSAC_API_KEY\"]
   i = os.environ[\"MAILSAC_INBOX\"]
   r = requests.get(f\"https://mailsac.com/api/addresses/{i}/messages\", headers={\"Mailsac-Key\":k})
   print(len(r.json()) if r.ok else r.text)
   "'
   ```

2. **Listener no procesa** (poll de 10min aun no llego). Forzar:
   ```bash
   COMPOSE 'exec listener python -c "
   from db import init_db; init_db()
   from inbox import create_backend
   from main import _process_message
   b = create_backend()
   for m in b.fetch_messages(): _process_message(m, b)
   "'
   ```

3. **Parser interpretacion mal**. Verificar con el reply body:
   ```bash
   COMPOSE 'exec listener python -c "from reply_parser import parse_reply; print(parse_reply(open(\"/tmp/test_body.txt\").read()))"'
   ```
   Mas info: `docs/EMAIL_AUDIT.md` y `listener/reply_parser.py`.

4. **Listener OOM kill** (mas de 150MB usados). Verificar:
   ```bash
   SSH 'docker stats --no-stream | grep listener'
   ```
   Bump el limit en `docker-compose.prod.yml`.

5. **PDFs > limit de Gmail attachment (25MB)**. Cada PDF de arxiv suele ser <5MB, pero si suma de 5 PDFs > 25MB rebota. Cap a 3 PDFs por reply o split.

### 4. "Caddy: 502 Bad Gateway"

Subscriptions container down. Caddy proxies bien pero el upstream falla:
```bash
COMPOSE 'logs subscriptions --tail 30'
COMPOSE 'restart subscriptions'
```

### 5. "VM se quedo sin memoria (OOM kill)"

```bash
SSH 'free -h'
SSH 'docker stats --no-stream'
```

Budget total: 956MB total, deberia haber ~330MB libres. Si esta tight:
- Reducir `ARXIV_MAX_RESULTS` (default 200, baja a 100)
- Reducir `POLL_INTERVAL_S` del listener (mas seguido = menos backlog en memoria)
- Restart todo: `COMPOSE 'restart'`

Hard fix: bump VM o limpiar logs viejos:
```bash
SSH 'docker system prune -af'  # cuidado, borra TODAS las imagenes no usadas
```

### 6. "Certificado HTTPS expiro"

Caddy auto-renueva via Let's Encrypt. Si fallo:
```bash
COMPOSE 'logs caddy --tail 50 | grep -iE "cert|acme"'
```

Mitigacion: restart Caddy, dispara nuevo ACME challenge.

### 7. "Suscriptor no recibe digest aunque este confirmado"

Posibles causas:
- `unsubscribed_at` no es NULL → no se le envia. Reactivar manual.
- Sus categorias no tienen papers nuevos hoy (filter devuelve []).
- Marcado como "seen" todos los papers (subscriber_seen_papers). Para retest:
  ```bash
  COMPOSE 'exec subscriptions python -c "
  import sqlite3
  c = sqlite3.connect(\"/app/data/subscribers.db\")
  c.execute(\"DELETE FROM subscriber_seen_papers WHERE subscriber_id=<ID>\").rowcount; c.commit()
  "'
  ```

### 8. "Subscribe form da 500 / 422 / etc"

```bash
COMPOSE 'logs subscriptions --tail 50 | grep -iE "error|exception"'
```

Casos comunes:
- Categoria invalida que el catalog no conoce
- Email vacio o malformado (deberia rebotar con 422)
- Rate limit hit (slowapi)

### 9. "Archive pagina muestra papers de mock"

Significa que NUNCA corrio el cron real (todos los archives son inyectados). Trigger cron real:
```bash
COMPOSE 'exec digest python -c "from main import run_digest; run_digest()"'
```

### 10. "Quiero restaurar un backup"

Backups locales: `/var/backups/arxiv/arxiv-<timestamp>.tar.gz` (ultimos 7 dias).

```bash
SSH 'ls -la /var/backups/arxiv/'

# Restaurar (CUIDADO: sobre-escribe data actual)
SSH 'cd ~/arxiv-digest && \
  docker compose -f docker-compose.prod.yml --env-file .env.prod down && \
  tar xzf /var/backups/arxiv/arxiv-YYYYMMDD-HHMM.tar.gz -C data/ && \
  docker compose -f docker-compose.prod.yml --env-file .env.prod up -d'
```

---

## Emergencias

### "Oracle revoco mi free tier VM"

1. Backup local NO te salva. Necesitas backup off-VM (Drive — pendiente OAuth).
2. Plan B: spin up VM en GCP free tier o Hetzner ($4/mes).
3. Restore desde el ultimo backup Drive que tengas.

### "Brevo/Gmail SMTP suspendido"

1. Test SMTP credentials externo (otro provider).
2. Migrate a Postmark / SES / Resend (requiere DKIM → dominio propio).
3. Stop-gap: pause el cron 1-2 dias hasta resolver, suscriptores no se enteran si quiero.

### "Spam complaints altos"

1. Verificar bounce rate en provider dashboard.
2. Pause cron + revisar lista de subs (¿alguien se reporto spam?).
3. Remove email del bouncer / complainer.

---

## Que NO esta documentado aca (Fase 3+)

- LLM relevance scoring fallbacks
- Multi-source ingestion fallbacks
- Pro tier / billing problemas
- Migration de domain owner (FreeDNS → propia)
