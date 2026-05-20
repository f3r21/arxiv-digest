# arxiv-digest

Sistema multi-usuario que envía un digest diario de papers nuevos
de [arXiv](https://arxiv.org) a cada suscriptor con **sus propias categorías**
y keywords. Respondes el email con los números de los papers que te interesan
y el sistema te devuelve esos PDFs como adjuntos. Todo corre en contenedores
con `docker compose`.

Cualquiera se suscribe desde un formulario web (con double opt-in) y elige
entre todas las categorías oficiales de arXiv (cs.\*, math.\*, stat.\*, etc.).

Proyecto del curso **CS3P2 Cloud Computing** — caso de uso de Docker.

## Arquitectura

Seis servicios orquestados por `docker-compose.yml`:

```
            internet                       LAN docker
   +-----+   :80/:443    +---------+   +---------------+
   | www | ------------> |  caddy  |-->| subscriptions |  (FastAPI form +
   +-----+   HTTPS auto  +---------+   |  + SQLite DB  |   double opt-in)
                                       +---------------+
                                              ^   subscribers.db
                                              |
   arXiv API ---HTTP--->  +-----------+    --|--->    +--------------+
   (export)               |  digest   |               |  translator  | --> MyMemory
                          | scheduler |-------------> +--------------+
                          +-----------+   SMTP
                                |
                                v
                         +-----------+
                         |  mailhog  |  (dev)   o   Resend/Brevo (prod)
                         |  (buzon)  |
                         +-----------+
                                ^
   arXiv PDFs <-----    +-----------+  <-- poll inbox API ---/
                        |  listener | --SMTP (reply + PDFs)--> sender real
                        +-----------+
```

- **subscriptions** — FastAPI con formulario de suscripción y endpoints
  `/subscribe`, `/confirm`, `/unsubscribe`. Es el único que escribe la tabla
  `subscribers` en `data/subscribers.db`. Manda email de confirmación firmado
  con token (válido 48 h).
- **caddy** — reverse proxy con HTTPS automático. En producción obtiene cert
  de Let's Encrypt; en dev (`SUBSCRIPTIONS_DOMAIN=localhost`) usa CA interno.
- **digest** — cada día lista los suscriptores activos, hace **una sola**
  consulta a arXiv con la unión de categorías, y aplica filtro + dedup +
  email por suscriptor. Cada email lleva un footer + `List-Unsubscribe`
  personalizado.
- **translator** — microservicio FastAPI interno; expone `POST /translate` y
  llama a la API pública de [MyMemory](https://mymemory.translated.net/doc/spec.php).
  Sin API key. Cachea por texto, así que repetir un paper para N suscriptores
  cuesta una sola llamada.
- **listener** — hace polling al inbox configurado; cuando ve un reply,
  resuelve el `From` contra la tabla de suscriptores, busca el snapshot
  per-usuario y le devuelve los PDFs al sender. Mensajes de senders
  desconocidos se descartan con log.
- **mailhog** — servidor SMTP de prueba con interfaz web; hace de buzón en
  dev. **No se expone a internet** (puertos sólo en `127.0.0.1`).

Todo el estado (suscriptores, papers vistos por suscriptor, snapshot del
último digest) vive en `./data/subscribers.db` (SQLite con WAL).

## Requisitos previos

- **Docker Desktop** instalado y corriendo.
  - Windows: Docker Desktop con backend WSL2 (recomendado).
  - macOS / Linux: Docker Desktop o Docker Engine + plugin compose.
- Verificar la instalación:

  ```bash
  docker version
  docker compose version
  ```

Los comandos `docker compose` de este README son **idénticos** en PowerShell
(Windows) y en bash/zsh (macOS/Linux).

## Configuración (`.env`)

Toda la config sensible (SMTP, inbox backend, categorías) vive en `.env`. La
primera vez:

```bash
cp .env.example .env
```

Los defaults apuntan a MailHog local: el stack funciona end-to-end sin tocar
nada más. Para enviar a tu correo real, ver [Modo live](#modo-live-brevo--mailsac).

## Levantar el stack

Antes de arrancar genera un `SUBSCRIPTIONS_SECRET` y ponlo en `.env`:

```bash
echo "SUBSCRIPTIONS_SECRET=$(openssl rand -hex 32)" >> .env
```

```bash
docker compose up -d --build
docker compose ps
```

Los seis servicios deben aparecer `healthy`/`running`. URLs útiles:

- Formulario de suscripción: `https://localhost` (cert autofirmado en dev;
  acepta el warning del navegador la primera vez).
- Buzón MailHog: `http://localhost:8025`.

## Suscribirse al digest

1. Abre `https://localhost/` en el navegador.
2. Pon tu email, busca/elige categorías arXiv (cs.\*, math.\*, etc.) y
   opcionalmente keywords.
3. En MailHog (`http://localhost:8025`) aparece el email de confirmación; haz
   click en el link.
4. Listo: ya estás en la tabla `subscribers`. El próximo digest lo recibes
   solo tú con tus categorías.

Para inspeccionar el estado:

```bash
sqlite3 data/subscribers.db 'select id,email,categories_json from subscribers'
```

## Disparar el digest manualmente

El digest está programado para las 07:00 (configurable con `DIGEST_HOUR`),
pero puedes dispararlo cuando quieras:

```bash
docker compose exec digest python -c "from main import run_digest; run_digest()"
```

Hace **una sola** consulta a arXiv con la unión de categorías de todos los
suscriptores activos y manda un email personalizado a cada uno.

## Probar el flujo de reply (digest -> PDFs)

Cuando respondes el digest con números de paper, el listener identifica al
suscriptor por tu `From`, lee tu snapshot personal del último digest y te
devuelve los PDFs.

### Opción A — desde la interfaz de MailHog

1. En `http://localhost:8025`, abre el digest dirigido a tu suscriptor (por
   ejemplo `a@local`).
2. Clic en **Reply**.
3. Asegúrate que `From: a@local` (el email con el que te suscribiste).
4. En el cuerpo escribe los números, por ejemplo: `quiero los papers 1, 3 y 5`.
5. **Send**. En ~30 s aparece un email `Re: ...` dirigido a `a@local` con los
   PDFs adjuntos. Replies de senders no suscritos se descartan (revisa los
   logs del listener: `docker compose logs listener`).

### Opción B — con el helper `tools/send_test_reply.py`

Si tienes Python en tu máquina (el puerto 1025 está publicado por compose):

```bash
# Windows (PowerShell)
python tools\send_test_reply.py "1 3 5"

# macOS / Linux
python3 tools/send_test_reply.py "1 3 5"
```

Si **no** tienes Python en el host, córrelo dentro del contenedor listener:

```bash
docker compose cp tools/send_test_reply.py listener:/tmp/send_test_reply.py
docker compose exec listener python /tmp/send_test_reply.py "1 3 5"
```

El listener hace polling cada 30 s; espera ese tiempo y revisa MailHog.

## Traducción al español

El servicio `translator` traduce título y abstract de cada paper a español antes
del envío. Configuración relevante en `docker-compose.yml`:

- **Subir cuota gratuita**: MyMemory da ~5000 chars/día por IP sin email, y
  ~50000 chars/día si pones tu correo. Edita `translator.environment`:

  ```yaml
  MYMEMORY_EMAIL: "tucorreo@example.com"
  ```

- **Desactivar el translator**: quita la variable `TRANSLATOR_URL` del bloque
  `digest.environment` (o ponla en `""`). El digest sale en inglés sin tocar
  ningún otro código. También puedes bajar solo ese contenedor:
  `docker compose stop translator`.

## Filtros legacy (`filters.yml`)

`filters.yml` ya no es la fuente de verdad. Cada suscriptor elige sus
categorías y keywords desde el formulario web; el digest combina las de todos
los suscriptores activos en una sola query a arXiv.

El archivo queda como referencia y para el script `tools/send_test_reply.py`.

## Modo live: Brevo + Mailsac

Para recibir el digest en un correo real **sin Gmail + app password**:

1. **Brevo** (SMTP saliente, 300 emails/día gratis):
   - Crea cuenta en [brevo.com](https://www.brevo.com).
   - Verifica tu Gmail como *sender identity*.
   - Genera una *SMTP key* en **SMTP & API**.

2. **Mailsac** (inbox entrante, 1500 calls/mes gratis):
   - Crea cuenta en [mailsac.com](https://mailsac.com).
   - Reserva una inbox: `<lo-que-sea>@mailsac.com`.
   - Genera una *API key*.

3. Edita `.env` (descomenta el bloque de modo live y rellena):

   ```env
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USER=tu-login@smtp-brevo.com
   SMTP_PASS=xxxxxxxxxxxxxxxx
   SMTP_USE_TLS=1
   FROM_ADDR=tucorreo@gmail.com
   REPLY_TO=tu-inbox@mailsac.com
   RECIPIENT=tucorreo@gmail.com

   INBOX_BACKEND=mailsac
   MAILSAC_API_KEY=k_xxxxxxxxxxxxxxxx
   MAILSAC_INBOX=tu-inbox@mailsac.com

   POLL_INTERVAL_S=600
   ```

4. Reinicia el stack:

   ```bash
   docker compose down
   docker compose up -d --build
   ```

5. Disparar manualmente y verificar:

   ```bash
   docker compose exec digest python -c "from main import run_digest; run_digest()"
   ```

El digest llegará a tu Gmail (`From: tucorreo@gmail.com`,
`Reply-To: tu-inbox@mailsac.com`). Cuando respondas, la reply va a Mailsac; el
listener la lee por API y te manda los PDFs.

**Rate-limit Mailsac**: el plan gratis da 1500 calls/mes; con `POLL_INTERVAL_S=600`
(10 min) gastas ~4320 calls/mes. Si esperás muchos suscriptores activos,
considerá subir el plan.

## Deploy en VPS (Hetzner / DO / Oracle Free)

1. En tu DNS, crea un A record que apunte tu subdominio al VPS:
   `digest.tu-dominio.com -> <IP del VPS>`.
2. Abre puertos `80` y `443` en el firewall.
3. Clona el repo en el VPS y crea `.env` así:
   ```env
   SUBSCRIPTIONS_DOMAIN=digest.tu-dominio.com
   PUBLIC_BASE_URL=https://digest.tu-dominio.com
   ADMIN_EMAIL=tu@correo.com
   SUBSCRIPTIONS_SECRET=$(openssl rand -hex 32)
   # + el bloque de Resend/Brevo + Mailsac de arriba
   ```
4. `docker compose up -d --build`. Caddy obtiene el certificado de Let's
   Encrypt en la primera request.
5. Verifica: `curl -sv https://digest.tu-dominio.com/health`.

Para que Gmail no te marque como spam:

- En Resend/Brevo verifica el dominio del `FROM_ADDR` con DKIM + SPF.
- Publica un registro DMARC: `v=DMARC1; p=none; rua=mailto:tu@correo.com`.
- El digest ya manda `List-Unsubscribe` y `List-Unsubscribe-Post` para
  cumplir con [Gmail bulk sender requirements](https://support.google.com/a/answer/14229414).

## Apagar

```bash
docker compose down       # detiene los contenedores, conserva los volumenes
docker compose down -v    # ademas borra los volumenes (estado limpio)
```

## Notas para Windows

- **Fin de línea**: el repo incluye `.gitattributes` que fuerza LF. No cambies
  `core.autocrlf`; con clonar normal es suficiente. Esto evita que los
  Dockerfiles y el código se rompan dentro de los contenedores Linux.
- **Docker Desktop**: usa el backend WSL2. El bind mount de `./data`, `./pdfs` y
  `filters.yml` funciona sin configuración extra.
- Todos los comandos funcionan igual en PowerShell. La única diferencia es el
  intérprete de Python del helper: `python` en Windows, `python3` en macOS/Linux.

## Troubleshooting

- **El digest trae 0 papers / `429`**: `export.arxiv.org` aplica rate-limit por
  IP y puede bloquear varios minutos. Espera y reintenta, o amplía las keywords
  de `filters.yml`. Para una demostración, dispara el digest **con antelación**
  para que el email ya esté en MailHog.
- **Puertos ocupados**: si algo ya usa el `1025` o el `8025`, cámbialos en
  `docker-compose.yml` (por ejemplo a `11025:1025` y `18025:8025`).
- **Nota técnica**: el cliente usa `https://export.arxiv.org`; el endpoint
  `http://` hace redirect 301 que `feedparser` no sigue. No lo cambies a `http`.

## Estructura del repo

```
arxiv-digest/
├── docker-compose.yml      # orquesta los 6 servicios
├── .env.example            # plantilla de envs (copiar a .env)
├── filters.yml             # legacy (referencia)
├── .gitattributes          # normaliza fin de linea (LF)
├── caddy/
│   └── Caddyfile           # reverse proxy + HTTPS automatico
├── subscriptions/          # servicio de suscripciones (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # endpoints /, /subscribe, /confirm, /unsubscribe
│   ├── db.py               # owner de subscribers.db
│   ├── tokens.py           # firmas itsdangerous (confirm 48h, unsub)
│   ├── email_outbound.py   # SMTP de confirmacion
│   ├── categories_catalog.py
│   ├── arxiv_categories.json
│   ├── templates/          # form.html, confirm_*.html, email_confirm.*
│   └── static/             # app.css, app.js (buscador client-side)
├── digest/                 # servicio digest (per-subscriber)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # scheduler + run_digest()
│   ├── arxiv_client.py     # consulta la API de arXiv
│   ├── filter_engine.py    # aplica keywords/authors per-subscriber
│   ├── translator_client.py# llama al servicio translator
│   ├── email_sender.py     # send_digest_to(subscriber, papers, issue)
│   ├── subscriber_repo.py  # read subscribers, per-user state
│   ├── unsubscribe_tokens.py # firma URL de unsubscribe
│   └── templates/digest.txt|.html
├── translator/             # servicio translator (FastAPI + MyMemory)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # POST /translate, chunking, cache
├── listener/               # servicio listener multi-subscriber
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # poll + sender lookup
│   ├── subscriber_repo.py  # find_by_email, get_last_digest_for
│   ├── inbox/              # backends de inbox (mailhog | mailsac)
│   │   ├── base.py         # Protocol comun
│   │   ├── mailhog.py      # cliente HTTP de MailHog
│   │   └── mailsac.py      # cliente REST de Mailsac
│   ├── reply_parser.py     # extrae numeros del reply
│   ├── pdf_downloader.py   # baja los PDFs de arXiv
│   ├── email_sender.py     # responde con adjuntos
│   └── db.py               # SQLite de idempotencia
├── tools/
│   ├── send_test_reply.py    # helper para probar el flujo de reply
│   └── build_arxiv_categories.py  # refresca arxiv_categories.json
├── data/                   # estado en runtime (no versionado)
└── pdfs/                   # PDFs temporales (no versionado)
```
