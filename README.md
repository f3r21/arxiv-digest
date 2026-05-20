# arxiv-digest

Sistema que envía un digest diario de papers nuevos
de [arXiv](https://arxiv.org) a un buzón de correo. Respondes el email con los
números de los papers que te interesan y el sistema te devuelve esos PDFs como
adjuntos. Todo corre en contenedores con `docker compose`.

Proyecto del curso **CS3P2 Cloud Computing** — caso de uso de Docker.

## Arquitectura

Cuatro servicios orquestados por `docker-compose.yml`:

```
                   +-------------------+
   arXiv API ---->  |  digest           |  --HTTP--> +--------------+
   (export)         |  scheduler diario |            |  translator  | --HTTPS--> MyMemory
                    +-------------------+            +--------------+
                            | SMTP
                            v
                    +-----------+
                    |  mailhog  |
                    |  (buzon)  |
                    +-----------+
                            ^
   arXiv PDFs <----  +-------------------+  <--poll API---/
                     |  listener         |  --SMTP (reply + PDFs)--> mailhog
                     |  procesa replies  |
                     +-------------------+
```

- **digest** — cada día consulta arXiv, filtra por `filters.yml`, deduplica
  contra lo ya enviado, pide al `translator` traducir los papers que pasaron el
  filtro y manda el digest por email.
- **translator** — microservicio FastAPI interno; expone `POST /translate` y
  llama a la API pública de [MyMemory](https://mymemory.translated.net/doc/spec.php)
  (de la lista [public-apis](https://github.com/public-apis/public-apis)). Sin
  API key. Hace chunking por oración para respetar el límite de ~500 bytes por
  query y cachea en memoria. Si MyMemory falla, devuelve el texto original (el
  digest sigue saliendo en inglés).
- **listener** — hace polling a la API de MailHog; cuando ve un reply con
  números, descarga esos PDFs de arXiv y responde con los adjuntos.
- **mailhog** — servidor SMTP de prueba con interfaz web; hace de buzón. No sale
  correo real a internet.

El estado compartido (papers vistos, snapshot del último digest) vive en el
volumen `./data`.

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

```bash
docker compose up -d --build
docker compose ps
```

Los cuatro servicios deben aparecer en estado `running`. Luego abre la interfaz
de MailHog en el navegador:

```
http://localhost:8025
```

## Disparar el digest manualmente

El digest está programado para las 07:00, pero puedes dispararlo cuando quieras:

```bash
docker compose exec digest python -c "from main import run_digest; run_digest()"
```

Tras unos segundos aparece un email nuevo en MailHog con los papers filtrados.

## Probar el flujo de reply (digest -> PDFs)

Cuando respondes el digest con números de paper, el listener te devuelve esos
PDFs adjuntos. Hay dos formas de probarlo:

### Opción A — desde la interfaz de MailHog (igual en todos los SO)

1. En `http://localhost:8025`, abre el email del digest.
2. Clic en **Reply**.
3. Pon `From: fer@local` y `To: fer@local`.
4. En el cuerpo escribe los números, por ejemplo: `quiero los papers 1, 3 y 5`.
5. **Send**. En ~30 s aparece un email `Re: ...` con los PDFs adjuntos.

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

## Editar el filtro

Edita `filters.yml` (categorías de arXiv, máximo de papers, keywords y autores).
**No hace falta rebuild**: el digest lo lee en cada corrida porque está montado
como volumen.

### Categorías múltiples

`filters.yml` acepta una sola categoría (`category: cs.DC`) o una lista
(`categories: [cs.DC, cs.AI]`). Para sobrescribir sin tocar el YAML:

```bash
# en .env
ARXIV_CATEGORIES=cs.DC,cs.AI
```

La env tiene precedencia sobre `filters.yml`. arXiv combina las categorías con
`OR` en la query.

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
(10 min) gastas ~4320 calls/mes — sigue siendo bajo y deja margen para escalado.
Para una demo en vivo, baja temporalmente a `30` durante la presentación.

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
├── docker-compose.yml      # orquesta los 4 servicios
├── .env.example            # plantilla de envs (copiar a .env)
├── filters.yml             # configuracion editable del filtro
├── .gitattributes          # normaliza fin de linea (LF)
├── digest/                 # servicio digest
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # scheduler + run_digest()
│   ├── arxiv_client.py     # consulta la API de arXiv
│   ├── filter_engine.py    # aplica filters.yml
│   ├── translator_client.py# llama al servicio translator
│   ├── email_sender.py     # arma y envia el digest
│   ├── shared_state.py     # SQLite + snapshot del digest
│   └── templates/digest.txt
├── translator/             # servicio translator (FastAPI + MyMemory)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py             # POST /translate, chunking, cache
├── listener/               # servicio listener
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py             # poll al backend de inbox configurado
│   ├── inbox/              # backends de inbox (mailhog | mailsac)
│   │   ├── base.py         # Protocol comun
│   │   ├── mailhog.py      # cliente HTTP de MailHog
│   │   └── mailsac.py      # cliente REST de Mailsac
│   ├── reply_parser.py     # extrae numeros del reply
│   ├── pdf_downloader.py   # baja los PDFs de arXiv
│   ├── email_sender.py     # responde con adjuntos
│   └── db.py               # SQLite de idempotencia
├── tools/
│   └── send_test_reply.py  # helper para probar el flujo de reply
├── data/                   # estado en runtime (no versionado)
└── pdfs/                   # PDFs temporales (no versionado)
```
