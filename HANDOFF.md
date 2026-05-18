# HANDOFF — arxiv-digest demo CS3P2

**Para:** Claude en el chat nuevo
**Fecha de cierre:** 2026-05-17
**Owner humano:** Fernando Ramirez Arredondo (CS senior UCSP, MacBook Air M2 24 GB)
**Curso:** CS3P2 Cloud Computing, prof Chuctaya, 2026-I
**Entregable:** presentacion de 10 minutos sobre caso de uso de Docker con rubric de 5 puntos

## 0. Como leer este documento

Las secciones 1-3 son contexto y arquitectura. La 4 es la estructura de archivos a crear. La 5 son los esqueletos de codigo. La 6 es el template del email. La 7 es el plan de slides. La 8 es el cheat sheet del demo. La 9 son riesgos. La 10 es el prompt para arrancar el chat nuevo.

Regla critica heredada: **cero alucinaciones**. Si un claim factual no se puede verificar contra un archivo o una API publica, marcalo como juicio. Si el usuario pregunta por un valor numerico, verificalo, no lo cites de memoria.

## 1. Contexto y decision

El usuario tenia que entregar una presentacion de 10 minutos sobre un caso de uso de Docker para CS3P2. Exploro varias opciones en sesiones previas (cold-start-profiler relacionado con su tesis, Paperless-ngx, Immich, etc.) y descarto todas por distintas razones. La conversacion final convergio en construir un **arxiv-digest deterministico con flow bidireccional via email**.

**Por que esta opcion gano:**
- Es gratis (sin APIs pagas, sin claves)
- Es deterministica al 100% (sin LLMs)
- Cumple los 5 puntos del rubric
- Tiene demo visualmente fuerte (email-as-API con respuesta interactiva)
- Build en ~10 horas
- El usuario escribe ~200 LOC propias, no es solo desplegar el compose de otro

**Por que NO otras opciones:**
- Cold-start-profiler: doble proposito no se cumplio, datos no entran a tesis
- Paperless-ngx: era solo desplegar compose upstream, sin codigo propio
- Immich/Locust/Pokemon/etc: vetadas por el usuario por distintas razones

**Caveat honesto declarado al usuario y aceptado:**
Bajo lectura estricta del rubric ("Docker resuelve el problema"), el arxiv-digest es borderline — el problema se podria resolver con un script Python + cron + sendmail. La defensa fuerte de Docker aqui es: (1) polyglot stack (Python + Go de MailHog) sin conflictos de dependencias, (2) patron email-as-API multi-servicio, (3) portabilidad mac → cloud free tier sin cambios. El usuario eligio aceptar esa lectura permisiva y avanzar.

## 2. Que es el arxiv-digest

Un sistema que:

1. Cada dia (o cuando se trigger manualmente) consulta arxiv API por papers nuevos en una categoria configurada.
2. Filtra contra reglas en `filters.yml`: papers que matchean keywords O autores en la lista.
3. Genera un email de texto plano con los papers numerados, mostrando titulo, autores, link y abstract verbatim.
4. Envia el email via SMTP a MailHog (catcher local con UI web).
5. Cada 30 segundos, un servicio listener consulta la API de MailHog. Si encuentra un reply con numeros (ej "1 3 7"), descarga los PDFs correspondientes y envia un email de respuesta con los PDFs adjuntos.

**Flow visual:**
```
arxiv API → digest → SMTP → MailHog inbox  →  usuario lee, responde "1 3 7"
                                                       ↓
                                                  MailHog API
                                                       ↑
                                              listener (poll 30s)
                                                       ↓
                                        descarga PDFs de arxiv
                                                       ↓
                                              SMTP → MailHog (reply con attachments)
                                                       ↓
                                              usuario recibe los PDFs
```

## 3. Arquitectura

Tres servicios en `docker-compose.yml`:

| Servicio | Tipo | Responsabilidad | Imagen |
|---|---|---|---|
| `digest` | Build local | Cron interno (schedule lib) que diario consulta arxiv, filtra, arma email, envia | Dockerfile Python 3.11 |
| `listener` | Build local | Poll cada 30s a MailHog API, parsea replies, descarga PDFs, envia respuestas | Dockerfile Python 3.11 |
| `mailhog` | Imagen oficial | SMTP catcher + web UI en :8025 + API para que listener lea replies | `mailhog/mailhog:latest` |

**Volumenes:**
- `./data` → SQLite con histórico de papers vistos y replies procesados
- `./pdfs` → cache temporal de PDFs descargados (limpiar despues de adjuntarlos al email de reply)
- `./filters.yml` → mounted readonly en `digest`

**Network:** una sola network bridge para que los 3 servicios se comuniquen por nombre DNS interno.

**Diseño 24/7-ready:** todos los servicios con `restart: unless-stopped`. El `digest` corre como proceso largo con `schedule` library en loop, no un script one-shot.

## 4. Estructura de archivos

```
arxiv-digest/
├── HANDOFF.md                  ← este documento
├── README.md                   ← user-facing, como correr
├── docker-compose.yml          ← 3 servicios + volumenes + network
├── .env                        ← config sensible (vacio para demo)
├── filters.yml                 ← configuracion de filtros (editable)
├── data/                       ← volumen compartido SQLite (gitignored)
│   └── .gitkeep
├── pdfs/                       ← cache temporal PDFs (gitignored)
│   └── .gitkeep
├── digest/
│   ├── Dockerfile              ← Python 3.11-slim + schedule + requests
│   ├── requirements.txt        ← feedparser, requests, jinja2, schedule, pyyaml
│   ├── main.py                 ← scheduler loop con schedule.every().day.at("07:00")
│   ├── arxiv_client.py         ← query arxiv API, parseo Atom
│   ├── filter_engine.py        ← matching contra filters.yml
│   ├── email_sender.py         ← smtplib a mailhog:1025
│   ├── db.py                   ← SQLite wrapper (papers_seen tabla)
│   └── templates/
│       └── digest.txt          ← Jinja2 template texto plano
├── listener/
│   ├── Dockerfile              ← Python 3.11-slim + requests
│   ├── requirements.txt        ← requests
│   ├── main.py                 ← loop polling MailHog API
│   ├── reply_parser.py         ← regex para extraer numeros del body
│   ├── pdf_downloader.py       ← descarga PDFs de arxiv
│   ├── email_sender.py         ← smtplib con attachments
│   └── db.py                   ← SQLite wrapper (replies_processed tabla)
└── slides/
    └── outline.md              ← plan de 10-12 slides
```

Total: ~200 LOC entre los 8 archivos Python.

## 5. Esqueletos de codigo

### 5.1 `digest/main.py`

```python
"""Daemon principal del digest. Corre 24/7 con schedule library."""

import logging
import os
import time

import schedule

from arxiv_client import fetch_papers
from filter_engine import apply_filters, load_filters
from email_sender import send_digest
from db import init_db, mark_seen, get_unseen

logger = logging.getLogger("digest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s INIT: %(message)s")

DIGEST_HOUR = os.environ.get("DIGEST_HOUR", "07:00")
FILTERS_PATH = "/app/filters.yml"
MAX_PAPERS = int(os.environ.get("MAX_PAPERS", "15"))


def run_digest() -> None:
    """Ejecuta el ciclo completo: arxiv → filter → email."""
    filters = load_filters(FILTERS_PATH)
    raw_papers = fetch_papers(filters["category"], max_results=50)
    new_papers = get_unseen(raw_papers)
    matched = apply_filters(new_papers, filters)
    if not matched:
        logger.info("PROFILE: digest skipped, 0 papers tras filtro")
        return
    capped = matched[:MAX_PAPERS]
    omitted = len(matched) - len(capped)
    send_digest(capped, omitted, filters)
    for p in capped:
        mark_seen(p["arxiv_id"])
    logger.info("RESULT: digest enviado, %d papers, %d omitidos", len(capped), omitted)


def main() -> None:
    init_db()
    # En el demo: triggerear inmediatamente al arrancar para no esperar 7am
    if os.environ.get("RUN_NOW", "0") == "1":
        run_digest()
    schedule.every().day.at(DIGEST_HOUR).do(run_digest)
    logger.info("INIT: scheduler arrancado, proximo digest %s", DIGEST_HOUR)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
```

### 5.2 `digest/arxiv_client.py`

```python
"""Cliente de arxiv API. Free, sin auth, devuelve Atom XML."""

import feedparser

ARXIV_API = "http://export.arxiv.org/api/query"


def fetch_papers(category: str, max_results: int = 50) -> list[dict]:
    """Consulta arxiv API por papers recientes en la categoria dada.

    Retorna lista de dicts con: arxiv_id, title, authors (list), abstract,
    published, pdf_url, categories (list).
    """
    url = (f"{ARXIV_API}?search_query=cat:{category}"
           f"&sortBy=submittedDate&sortOrder=descending"
           f"&max_results={max_results}")
    feed = feedparser.parse(url)
    papers = []
    for entry in feed.entries:
        arxiv_id = entry.id.rsplit("/", 1)[-1]  # ej "2405.10234v1"
        arxiv_id = arxiv_id.split("v")[0]       # remove version suffix
        pdf_url = next(
            (l.href for l in entry.links if l.type == "application/pdf"),
            f"http://arxiv.org/pdf/{arxiv_id}.pdf",
        )
        papers.append({
            "arxiv_id": arxiv_id,
            "title": entry.title.replace("\n", " ").strip(),
            "authors": [a.name for a in entry.authors],
            "abstract": entry.summary.replace("\n", " ").strip(),
            "published": entry.published,
            "pdf_url": pdf_url,
            "categories": [t.term for t in entry.tags],
        })
    return papers
```

### 5.3 `digest/filter_engine.py`

```python
"""Aplica filtros declarados en filters.yml a una lista de papers."""

import yaml


def load_filters(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def apply_filters(papers: list[dict], filters: dict) -> list[dict]:
    """Retorna papers que matchean keywords O autores. Anota match_reason."""
    keywords = [k.lower() for k in filters.get("keywords", [])]
    authors = filters.get("authors", [])
    out = []
    for p in papers:
        haystack = (p["title"] + " " + p["abstract"]).lower()
        matched_kw = [k for k in keywords if k in haystack]
        matched_au = [a for a in authors if any(a.lower() in au.lower() for au in p["authors"])]
        if matched_kw or matched_au:
            p["match_reason"] = (
                ", ".join(matched_kw + [f"autor: {a}" for a in matched_au])
            )
            out.append(p)
    return out
```

### 5.4 `digest/email_sender.py`

```python
"""Envia el email del digest a MailHog via SMTP."""

import os
import smtplib
import textwrap
from datetime import date
from email.message import EmailMessage

from jinja2 import Environment, FileSystemLoader

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
FROM_ADDR = "arxiv-digest@local"
TO_ADDR = os.environ.get("RECIPIENT", "fer@local")


def wrap_abstract(abstract: str, width: int = 68) -> str:
    """Wrap a 68 chars indentado a 4 espacios."""
    wrapped = textwrap.fill(abstract, width=width)
    return textwrap.indent(wrapped, "    ")


def send_digest(papers: list[dict], omitted: int, filters: dict) -> None:
    env = Environment(loader=FileSystemLoader("/app/templates"))
    env.filters["wrap_abstract"] = wrap_abstract
    template = env.get_template("digest.txt")
    body = template.render(
        date=date.today().strftime("%d %b %Y"),
        papers=papers,
        omitted=omitted,
        category=filters["category"],
    )
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    msg["Subject"] = f"arxiv digest {date.today().isoformat()} — {len(papers)} papers"
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
```

### 5.5 `digest/db.py`

```python
"""SQLite wrapper. Tabla papers_seen para dedup."""

import sqlite3
from contextlib import contextmanager

DB_PATH = "/app/data/digest.db"


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS papers_seen (
                arxiv_id TEXT PRIMARY KEY,
                seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS last_digest (
                id INTEGER PRIMARY KEY,
                sent_at TEXT,
                papers_json TEXT
            )
        """)


def get_unseen(papers: list[dict]) -> list[dict]:
    with conn() as c:
        seen = {row[0] for row in c.execute("SELECT arxiv_id FROM papers_seen")}
    return [p for p in papers if p["arxiv_id"] not in seen]


def mark_seen(arxiv_id: str) -> None:
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO papers_seen (arxiv_id) VALUES (?)", (arxiv_id,))


def save_last_digest(papers: list[dict]) -> None:
    """Guarda el digest enviado para que el listener pueda mappear numeros → papers."""
    import json
    with conn() as c:
        c.execute("DELETE FROM last_digest")
        c.execute("INSERT INTO last_digest (sent_at, papers_json) VALUES (CURRENT_TIMESTAMP, ?)",
                  (json.dumps(papers),))


def get_last_digest() -> list[dict]:
    import json
    with conn() as c:
        row = c.execute("SELECT papers_json FROM last_digest ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row[0]) if row else []
```

### 5.6 `listener/main.py`

```python
"""Daemon listener. Polls MailHog API cada 30s buscando replies."""

import logging
import os
import time

import requests

from reply_parser import parse_reply
from pdf_downloader import download_pdfs
from email_sender import send_reply
from db import init_db, is_processed, mark_processed

logger = logging.getLogger("listener")
logging.basicConfig(level=logging.INFO, format="%(asctime)s INIT: %(message)s")

MAILHOG_API = os.environ.get("MAILHOG_API", "http://mailhog:8025/api/v2/messages")
POLL_INTERVAL_S = 30
RECIPIENT = "fer@local"


def fetch_replies() -> list[dict]:
    """Lista los mensajes en MailHog dirigidos al usuario."""
    r = requests.get(MAILHOG_API, timeout=5)
    r.raise_for_status()
    out = []
    for m in r.json().get("items", []):
        msg_id = m["ID"]
        to_addrs = [t["Mailbox"] + "@" + t["Domain"] for t in m["To"]]
        if RECIPIENT not in to_addrs:
            continue
        subject = m["Content"]["Headers"].get("Subject", [""])[0]
        body = m["Content"]["Body"]
        out.append({"id": msg_id, "subject": subject, "body": body})
    return out


def main() -> None:
    init_db()
    logger.info("INIT: listener arrancado, polling %s cada %ss", MAILHOG_API, POLL_INTERVAL_S)
    while True:
        try:
            for msg in fetch_replies():
                if is_processed(msg["id"]):
                    continue
                numbers = parse_reply(msg["body"])
                if not numbers:
                    mark_processed(msg["id"])  # no actionable, skip
                    continue
                pdfs = download_pdfs(numbers)
                send_reply(msg["subject"], numbers, pdfs)
                mark_processed(msg["id"])
                logger.info("RESULT: respondido a reply %s con %d PDFs",
                            msg["id"], len(pdfs))
        except Exception as e:
            logger.error("ERROR: %s", e)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
```

### 5.7 `listener/reply_parser.py`

```python
"""Extrae numeros de un reply. Acepta '1 3 7', '1,3,7', '#1 #3 #7'."""

import re


def parse_reply(body: str) -> list[int]:
    """Retorna lista ordenada, deduplicada, capped a 10 numeros."""
    tokens = re.findall(r"\b\d{1,2}\b", body)
    seen = set()
    out = []
    for t in tokens:
        n = int(t)
        if 1 <= n <= 99 and n not in seen:
            seen.add(n)
            out.append(n)
        if len(out) >= 10:
            break
    return out
```

### 5.8 `listener/pdf_downloader.py`

```python
"""Descarga PDFs de arxiv.org para los papers solicitados."""

import os
from pathlib import Path

import requests

from db import get_papers_from_last_digest

PDFS_DIR = Path("/app/pdfs")
PDFS_DIR.mkdir(exist_ok=True)


def download_pdfs(numbers: list[int]) -> list[dict]:
    """Para cada numero del reply, busca el paper correspondiente al ultimo
    digest, descarga el PDF y retorna info para el email de respuesta."""
    papers = get_papers_from_last_digest()
    out = []
    for n in numbers:
        if not (1 <= n <= len(papers)):
            continue
        p = papers[n - 1]
        first_author = p["authors"][0].split()[-1] if p["authors"] else "unknown"
        year = p["published"][:4]
        slug = "".join(c if c.isalnum() else "_" for c in p["title"][:30])
        filename = f"{first_author}_{year}_{slug}.pdf"
        path = PDFS_DIR / filename
        r = requests.get(p["pdf_url"], timeout=30)
        r.raise_for_status()
        path.write_bytes(r.content)
        out.append({"number": n, "path": str(path), "title": p["title"]})
    return out
```

### 5.9 `listener/email_sender.py`

```python
"""Envia email de respuesta con PDFs adjuntos."""

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))


def send_reply(original_subject: str, numbers: list[int], pdfs: list[dict]) -> None:
    msg = EmailMessage()
    msg["From"] = "arxiv-digest@local"
    msg["To"] = "fer@local"
    msg["Subject"] = f"Re: {original_subject} — {len(pdfs)} PDFs"
    body_lines = [f"PDFs solicitados: {numbers}", "", "Aqui los adjuntos:", ""]
    for p in pdfs:
        body_lines.append(f"  [{p['number']:>2}] {p['title']}")
    body_lines.append("")
    msg.set_content("\n".join(body_lines))
    for p in pdfs:
        path = Path(p["path"])
        msg.add_attachment(path.read_bytes(), maintype="application",
                           subtype="pdf", filename=path.name)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    # Limpiar PDFs descargados
    for p in pdfs:
        Path(p["path"]).unlink(missing_ok=True)
```

## 6. Template del email (`digest/templates/digest.txt`)

Plain text, Jinja2:

```jinja
=== arXiv Digest — {{ date }} ===

{{ papers|length }} papers nuevos. Filtro: {{ category }} + keywords/autores
configurados en filters.yml.

Para descargar PDFs, responde con los numeros (ej: 1 3 7).
{% for p in papers %}

{{ "%2d"|format(loop.index) }}. {{ p.title }}
    {{ p.authors|join(', ')|truncate(60) }} (matched: {{ p.match_reason }})
    arxiv.org/abs/{{ p.arxiv_id }}

{{ p.abstract|wrap_abstract }}
{% endfor %}
{% if omitted %}

(+ {{ omitted }} papers omitidos. Edita filters.yml para refinar.)
{% endif %}

—  fin del digest, responde con los numeros  —
```

## 7. Plan de slides (10-12 slides para 10 minutos)

**Slide 1 — Titulo**
- "arxiv-digest: tu firehose de papers, filtrado, en tu inbox"
- Subtitulo: "CS3P2 Cloud Computing — caso de uso Docker (10 min)"
- Autor, fecha

**Slide 2 — Hook (un solo numero)**
- "50+" en grande
- "papers nuevos cada dia en cs.DC. Nadie los lee todos."

**Slide 3 — Problema**
- 3 bullets cortos: volumen ingobernable, soluciones SaaS pagas ($14-50/mes), AI no-determinista
- Foto/screenshot pequeno del listing de arxiv abrumador

**Slide 4 — La solucion en una frase**
- "Un digest deterministico que llega a tu correo. Respondes con numeros, recibes PDFs."
- Diagrama minimalista del flow

**Slide 5 — Arquitectura**
- 3 cajas: digest, listener, mailhog
- Flecha bidireccional usuario ↔ mailhog
- Anotacion: "Patron email-as-API (ChatOps adaptado a SMTP)"

**Slide 6 — Polyglot stack via Docker**
- "digest" (Python 3.11) + "listener" (Python 3.11) + "mailhog" (Go)
- "3 runtimes, 1 compose.yml, 0 conflictos de dependencias"
- Codigo: docker-compose.yml en monospace, 30 lineas

**Slide 7 — El email (texto plano)**
- Captura del template renderizado
- Subraya: numerado, autores, link, abstract verbatim, instruccion clara

**Slide 8 — filters.yml**
- Snippet del yaml en 5 lineas
- "Configuracion declarativa, no codigo"

**Slide 9 — Codigo (~200 LOC tuyo)**
- Captura del filter_engine.py o reply_parser.py
- "<200 lineas Python entre los 2 servicios. Sin LLMs. Sin magia."

**Slide 10 — Demo (slide vacia, cambias a la app)**

**Slide 11 — Resultados medidos**
- Tabla:
  - Trigger → digest enviado: ~5s
  - Reply → PDFs recibidos: ~25s
  - Papers procesados en 1 corrida: 50
  - Costo: $0
  - vs Scholarcy Pro: $168/año, vs Elicit: $120/año

**Slide 12 — Deployment options + cierre**
- Tabla con 3 modos: local on-demand, local 24/7, cloud free tier (Oracle/Fly.io)
- "Mismo docker-compose, 3 entornos. Eso es lo que aporta Docker aqui."
- Q&A

## 8. Cheat sheet del demo

**Antes de entrar al aula:**

```bash
cd ~/2026-1/Cloud\ Computing/arxiv-digest
# Aregurarse de que no haya estado previo
docker compose down -v
# Limpiar MailHog inbox curl
# Levantar todo en background
docker compose up -d
# Pre-flight: confirmar que los 3 servicios estan healthy
docker compose ps
# Abrir MailHog UI en una pestana del browser
open http://localhost:8025
```

**Durante el demo (5 min de demo en vivo):**

1. **Trigger del digest manualmente** (no esperar 7am):
   ```bash
   docker compose exec digest python -c "from main import run_digest; run_digest()"
   ```
   Ves logs en pantalla "fetching 50 papers, filtering, sending..."

2. **Cambiar al browser con MailHog UI**. Email recien llegado. Lo abres. Audiencia ve el formato limpio.

3. **Identificar 3 papers de interes en el email**. Ejemplo verbal: "me interesa el 2, el 5 y el 9".

4. **Click "Reply" en MailHog UI**. Escribir simplemente `2 5 9` en el body. Send.

5. **Esperar ~30 segundos** (mientras hablas del listener). Aparece email nuevo en MailHog con prefijo "Re:" y 3 attachments.

6. **Abrir el email nuevo**. Mostrar la lista de papers solicitados. Mostrar attachments en la parte inferior.

7. **Click en un PDF**. Se descarga/abre. Mostrar que es el paper real de arxiv.

**Plan B si falla algo en vivo:**

Tener grabado un screencast de 90 segundos de TODO el flow funcionando, listo para reproducir si algo se cuelga en vivo. Se graba con QuickTime mostrando los pasos 1-7 anteriores. Backup mental: "tengo un screencast del flujo si esto se cuelga".

**Despues del demo:**

```bash
docker compose down
```

## 9. Riesgos identificados

**R1 — arxiv API timeout o down durante el demo.**
Mitigacion: tener un fixture JSON con 15 papers pre-fetchados en `digest/fixtures/papers_2026-05-17.json`. Si arxiv falla, cambiar a `RUN_NOW=1 USE_FIXTURE=1` para usar el fixture. El demo no se nota la diferencia.

**R2 — MailHog API tarda mas de 30s en reflejar el reply.**
Mitigacion: ensayar 3 veces antes del demo. En el peor caso, hablar 30-45s extra sobre la arquitectura mientras el listener procesa.

**R3 — Conflict de puerto si algo ya corre en 8025 o 1025.**
Mitigacion: hacer `lsof -i :8025` antes del demo. En el compose, exponer en :18025 si hay conflicto.

**R4 — Si el filtro no matchea ningun paper en los 50 fetched, el demo queda vacio.**
Mitigacion: configurar `filters.yml` con keywords MUY anchas (ej: "learning", "system", "scaling") para garantizar matches. Esto es trampa benigna; el real-world filtro seria mas restrictivo.

**R5 — El usuario tipea numeros fuera de rango (ej: 99 cuando solo hay 12 papers).**
Mitigacion: el `pdf_downloader.py` ya filtra con `if 1 <= n <= len(papers)`. Salida graceful, no crash.

**R6 — Email con muchos PDFs supera el size limit.**
Mitigacion: limite de 10 numeros en `reply_parser.py`, y PDFs >5 MB skipped. Para el demo, no es problema.

## 10. Prompt para arrancar el chat nuevo

Pegale esto al chat nuevo:

```
Soy Fernando, CS senior en UCSP. Tengo el handoff completo del proyecto en
/Users/99/2026-1/Cloud Computing/arxiv-digest/HANDOFF.md

Lee ese documento entero antes de hacer nada. Contiene:
- Arquitectura final decidida
- Estructura de archivos a crear
- Esqueletos de codigo para los 8 archivos Python
- Template del email
- Plan de 10-12 slides
- Cheat sheet del demo en vivo
- Riesgos identificados con mitigaciones

Mi objetivo en este chat: construir el proyecto siguiendo el handoff, ensayar
el demo 3 veces, y armar las slides. Total estimado ~10 horas. Trabajemos
seccion por seccion siguiendo la estructura del HANDOFF.

Reglas heredadas:
- Cero alucinaciones. Cualquier numero que cites debe venir de un archivo o
  una API publica, no de tu memoria.
- No emojis en codigo.
- Prints minimos en codigo, solo los logs estructurados que el HANDOFF
  ya especifica (prefijos INIT:, PROFILE:, RESULT:, ERROR:).
- Mac M2 24GB, Docker Desktop ya instalado.

Empezamos por la estructura de carpetas y docker-compose.yml. Cuando
verifiques que todo levanta, pasamos al codigo de digest/. Cuando el digest
envia un email correctamente a MailHog, pasamos al listener.
```

## Anexo: comandos de verificacion paso a paso

```bash
# 1. Verificar que la estructura de archivos esta completa
cd ~/2026-1/Cloud\ Computing/arxiv-digest
ls -la digest/ listener/ slides/

# 2. Levantar el stack
docker compose up -d --build

# 3. Verificar que los 3 servicios estan corriendo
docker compose ps

# 4. Mirar logs del digest (deberia estar en idle esperando 7am)
docker compose logs digest

# 5. Triggerar digest manualmente
docker compose exec digest python -c "from main import run_digest; run_digest()"

# 6. Verificar el email en MailHog
curl -s http://localhost:8025/api/v2/messages | python3 -m json.tool | head -50

# 7. Probar reply parser localmente
docker compose exec listener python -c "from reply_parser import parse_reply; print(parse_reply('quiero los papers 2, 5 y 9 por favor'))"
# Esperado: [2, 5, 9]

# 8. Si MailHog acumula mucha basura
curl -X DELETE http://localhost:8025/api/v1/messages

# 9. Reset completo
docker compose down -v && docker compose up -d --build
```

Fin del documento.
