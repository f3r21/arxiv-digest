# HANDOFF para Claude Code — arxiv-digest

**Audiencia:** Claude Code (CLI con bash + git + docker compose).
**Working dir:** `/Users/99/2026-1/Cloud Computing/arxiv-digest/`
**Owner humano:** Fernando Ramirez Arredondo (CS senior UCSP, MacBook Air M2 24 GB).
**Curso:** CS3P2 Cloud Computing, prof Chuctaya, presentacion de 10 min sobre caso de uso de Docker.

## 1. Mision

Construir un sistema de digest de arxiv con flow bidireccional via email (digest llega al inbox → usuario responde con numeros → PDFs llegan adjuntos al reply). Tres servicios en docker-compose (digest, listener, mailhog). Total ~250 LOC Python que tu escribes literalmente del codigo inline en este documento. Determinístico al 100% (sin LLMs).

**Salida esperada al cerrar este chat:**

```
arxiv-digest/
├── HANDOFF_CLAUDE_CODE.md       ← este documento
├── README.md                     ← user-facing
├── docker-compose.yml
├── filters.yml
├── .gitignore
├── data/.gitkeep
├── pdfs/.gitkeep
├── digest/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── arxiv_client.py
│   ├── filter_engine.py
│   ├── email_sender.py
│   ├── shared_state.py
│   └── templates/digest.txt
└── listener/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── reply_parser.py
    ├── pdf_downloader.py
    ├── email_sender.py
    └── db.py
```

Con `docker compose up -d --build`, los tres servicios sanos, un digest triggereado manualmente que envia email a MailHog, y un reply con numeros que provoca PDFs adjuntos en respuesta.

## 2. Reglas hereditarias

- **Cero alucinaciones.** Cualquier numero, comportamiento o resultado debe ser verificable contra un archivo o una respuesta de API real. Si no lo sabes, corre el comando que te lo confirma. No inventes.
- **No emojis en codigo ni en logs.** Anywhere.
- **Prints minimos.** Solo los logs estructurados con prefijos `INIT:`, `PROFILE:`, `RESULT:`, `ERROR:`.
- **Anotaciones de tipo completas** en todas las firmas de funciones publicas (PEP 8 + rule `python/coding-style.md`).
- **Una pieza a la vez.** No saltes pasos. Verifica cada step antes de avanzar.

## 3. Plan de ejecucion en 7 fases

Cada fase tiene: archivos a crear, codigo completo inline, y un check verificable. NO continues a la siguiente fase si el check de la actual falla.

### Fase 0 — Pre-flight

Verifica que Docker Desktop esta corriendo:

```bash
docker version
docker compose version
```

Verifica el working directory:

```bash
cd "/Users/99/2026-1/Cloud Computing/arxiv-digest"
pwd
ls -la
```

Si la carpeta no existe, creala:

```bash
mkdir -p "/Users/99/2026-1/Cloud Computing/arxiv-digest"
cd "/Users/99/2026-1/Cloud Computing/arxiv-digest"
```

**Check fase 0:** `docker info` retorna sin error, y estas posicionado en el directorio correcto.

### Fase 1 — Skeleton del repo

Crea la estructura de carpetas:

```bash
mkdir -p digest/templates listener data pdfs
touch data/.gitkeep pdfs/.gitkeep
```

Crea **`.gitignore`**:

```
__pycache__/
*.pyc
.venv/
.DS_Store
data/*
!data/.gitkeep
pdfs/*
!pdfs/.gitkeep
```

Crea **`filters.yml`** (configuracion editable por el usuario):

```yaml
# Categoria de arxiv a consultar. Catalogo: https://arxiv.org/category_taxonomy
category: cs.DC

# Maximo papers en el digest (cap aplicado tras filtrar).
max_papers: 15

# Para que un paper aparezca debe matchear al menos un keyword O un autor.
keywords:
  - kubernetes
  - autoscaling
  - cold start
  - cold-start
  - serverless
  - microservice
  - container

authors:
  - "Pavlou T"
  - "Liu Y"
```

Crea **`README.md`** (corto, user-facing):

````markdown
# arxiv-digest

Sistema deterministico que envia digests diarios de papers nuevos en arxiv a tu inbox. Respondes con numeros, te llegan los PDFs.

## Levantar

```bash
docker compose up -d --build
docker compose ps
```

MailHog UI: http://localhost:8025

## Trigger manual del digest

```bash
docker compose exec digest python -c "from main import run_digest; run_digest()"
```

## Editar el filtro

Edita `filters.yml`. Tras editar, no hace falta rebuild — el digest lo lee en cada corrida.

## Apagar

```bash
docker compose down       # mantiene volumenes
docker compose down -v    # borra todo
```
````

**Check fase 1:** `tree -L 3 -a -I '__pycache__|.git'` muestra la estructura completa con los 4 archivos creados (.gitignore, filters.yml, README.md, y los .gitkeep).

### Fase 2 — docker-compose.yml

Crea **`docker-compose.yml`**:

```yaml
services:
  digest:
    build: ./digest
    container_name: arxiv-digest
    restart: unless-stopped
    depends_on:
      - mailhog
    environment:
      SMTP_HOST: mailhog
      SMTP_PORT: "1025"
      RECIPIENT: fer@local
      DIGEST_HOUR: "07:00"
      RUN_NOW: "0"
      TZ: America/Lima
    volumes:
      - ./filters.yml:/app/filters.yml:ro
      - ./data:/app/data
    networks: [internal]
    logging:
      driver: json-file
      options: {max-size: "5m", max-file: "3"}

  listener:
    build: ./listener
    container_name: arxiv-listener
    restart: unless-stopped
    depends_on:
      - mailhog
    environment:
      MAILHOG_API: http://mailhog:8025/api/v2/messages
      MAILHOG_DELETE_API: http://mailhog:8025/api/v1/messages
      SMTP_HOST: mailhog
      SMTP_PORT: "1025"
      RECIPIENT: fer@local
      POLL_INTERVAL_S: "30"
      TZ: America/Lima
    volumes:
      - ./data:/app/data
      - ./pdfs:/app/pdfs
    networks: [internal]
    logging:
      driver: json-file
      options: {max-size: "5m", max-file: "3"}

  mailhog:
    image: mailhog/mailhog:latest
    container_name: arxiv-mailhog
    restart: unless-stopped
    ports:
      - "1025:1025"
      - "8025:8025"
    networks: [internal]

networks:
  internal:
    driver: bridge
```

**Check fase 2:** `docker compose config` parsea sin errores y muestra los 3 servicios. NO levantes nada todavia — los Dockerfiles aun no existen.

### Fase 3 — Servicio digest

Crea **`digest/Dockerfile`**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY templates ./templates

CMD ["python", "-u", "main.py"]
```

Crea **`digest/requirements.txt`**:

```
feedparser==6.0.11
requests==2.32.3
jinja2==3.1.4
schedule==1.2.2
pyyaml==6.0.2
```

Crea **`digest/arxiv_client.py`** (completo, sin TODOs):

```python
"""Cliente de arxiv API. Free, sin auth, devuelve Atom XML."""

import logging
from typing import Any

import feedparser

logger = logging.getLogger("digest")

ARXIV_API = "http://export.arxiv.org/api/query"


def fetch_papers(category: str, max_results: int = 50) -> list[dict[str, Any]]:
    """Consulta arxiv API por papers recientes en una categoria.

    :param category: codigo de categoria arxiv (ej "cs.DC").
    :param max_results: limite de papers a traer.
    :returns: lista de dicts con arxiv_id, title, authors, abstract,
        published, pdf_url, categories.
    """
    url = (
        f"{ARXIV_API}?search_query=cat:{category}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    logger.info("PROFILE: query arxiv category=%s max=%d", category, max_results)
    feed = feedparser.parse(url)
    papers: list[dict[str, Any]] = []
    for entry in feed.entries:
        raw_id = entry.id.rsplit("/", 1)[-1]  # ej "2405.10234v1"
        arxiv_id = raw_id.split("v")[0]
        pdf_url = next(
            (l.href for l in entry.links if l.get("type") == "application/pdf"),
            f"http://arxiv.org/pdf/{arxiv_id}.pdf",
        )
        papers.append({
            "arxiv_id": arxiv_id,
            "title": " ".join(entry.title.split()),
            "authors": [a.name for a in entry.authors],
            "abstract": " ".join(entry.summary.split()),
            "published": entry.published,
            "pdf_url": pdf_url,
            "categories": [t.term for t in entry.tags],
        })
    logger.info("PROFILE: fetched %d papers", len(papers))
    return papers
```

Crea **`digest/filter_engine.py`**:

```python
"""Aplica reglas de filters.yml a una lista de papers."""

from typing import Any

import yaml


def load_filters(path: str) -> dict[str, Any]:
    """Carga el yaml de configuracion."""
    with open(path) as f:
        return yaml.safe_load(f)


def apply_filters(
    papers: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Retorna papers que matchean keywords O autores configurados.

    Anota cada paper retornado con un campo `match_reason` describiendo
    por que paso el filtro.
    """
    keywords = [k.lower() for k in filters.get("keywords") or []]
    target_authors = filters.get("authors") or []
    matched: list[dict[str, Any]] = []
    for p in papers:
        haystack = (p["title"] + " " + p["abstract"]).lower()
        kw_hits = [k for k in keywords if k in haystack]
        au_hits = [
            a for a in target_authors
            if any(a.lower() in author.lower() for author in p["authors"])
        ]
        if kw_hits or au_hits:
            reasons: list[str] = list(kw_hits)
            reasons.extend(f"autor:{a}" for a in au_hits)
            p["match_reason"] = ", ".join(reasons)
            matched.append(p)
    return matched
```

Crea **`digest/shared_state.py`** (estado compartido con listener via JSON + SQLite separados):

```python
"""Estado persistente del digest.

Dos archivos en el volumen /app/data:
- papers_seen.db: SQLite con arxiv_ids ya enviados (solo digest escribe).
- last_digest.json: snapshot del ultimo digest (digest escribe, listener lee).
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "papers_seen.db"
LAST_DIGEST_JSON = DATA_DIR / "last_digest.json"


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    """Crea la tabla papers_seen si no existe."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS papers_seen (
                arxiv_id TEXT PRIMARY KEY,
                seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_unseen(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra papers que aun no estan en papers_seen."""
    with _conn() as c:
        seen = {row[0] for row in c.execute("SELECT arxiv_id FROM papers_seen")}
    return [p for p in papers if p["arxiv_id"] not in seen]


def mark_seen(arxiv_ids: list[str]) -> None:
    """Marca los arxiv_ids como vistos."""
    with _conn() as c:
        c.executemany(
            "INSERT OR IGNORE INTO papers_seen (arxiv_id) VALUES (?)",
            [(aid,) for aid in arxiv_ids],
        )


def save_last_digest(papers: list[dict[str, Any]]) -> None:
    """Guarda los papers del digest enviado para que el listener los mapee."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_DIGEST_JSON.write_text(json.dumps(papers, ensure_ascii=False, indent=2))
```

Crea **`digest/email_sender.py`**:

```python
"""Envia el digest a MailHog via SMTP."""

import logging
import os
import smtplib
import textwrap
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("digest")

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
FROM_ADDR = "arxiv-digest@local"
TO_ADDR = os.environ.get("RECIPIENT", "fer@local")
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _wrap_abstract(abstract: str, width: int = 68) -> str:
    wrapped = textwrap.fill(abstract, width=width)
    return textwrap.indent(wrapped, "    ")


def send_digest(
    papers: list[dict[str, Any]], omitted: int, filters: dict[str, Any]
) -> None:
    """Renderiza el template y envia el email."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["wrap_abstract"] = _wrap_abstract
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
    msg["Subject"] = (
        f"arxiv digest {date.today().isoformat()} - {len(papers)} papers"
    )
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    logger.info("RESULT: email enviado a %s con %d papers", TO_ADDR, len(papers))
```

Crea **`digest/templates/digest.txt`**:

```jinja
=== arXiv Digest - {{ date }} ===

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

---  fin del digest, responde con los numeros  ---
```

Crea **`digest/main.py`** (entrypoint con scheduler):

```python
"""Daemon principal del digest. Loop con schedule library, 24/7-ready."""

import logging
import os
import time

import schedule

from arxiv_client import fetch_papers
from email_sender import send_digest
from filter_engine import apply_filters, load_filters
from shared_state import get_unseen, init_db, mark_seen, save_last_digest

logger = logging.getLogger("digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

FILTERS_PATH = "/app/filters.yml"
DIGEST_HOUR = os.environ.get("DIGEST_HOUR", "07:00")


def run_digest() -> None:
    """Ciclo completo: arxiv -> filter -> dedup -> save -> email."""
    filters = load_filters(FILTERS_PATH)
    max_papers = int(filters.get("max_papers", 15))
    raw = fetch_papers(filters["category"], max_results=50)
    new = get_unseen(raw)
    matched = apply_filters(new, filters)
    if not matched:
        logger.info("PROFILE: 0 papers tras filtro, digest no enviado")
        return
    capped = matched[:max_papers]
    omitted = len(matched) - len(capped)
    save_last_digest(capped)
    send_digest(capped, omitted, filters)
    mark_seen([p["arxiv_id"] for p in capped])
    logger.info(
        "RESULT: digest %d enviados, %d omitidos, %d nuevos tras dedup",
        len(capped), omitted, len(new),
    )


def main() -> None:
    init_db()
    if os.environ.get("RUN_NOW", "0") == "1":
        logger.info("INIT: RUN_NOW=1, ejecutando digest inmediato")
        run_digest()
    schedule.every().day.at(DIGEST_HOUR).do(run_digest)
    logger.info("INIT: scheduler arrancado, proximo digest a las %s", DIGEST_HOUR)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
```

**Check fase 3:** Build solo el servicio digest sin levantar nada:

```bash
docker compose build digest
```

Esperado: build exitoso, sin warnings de pip about missing wheels. Si falla, revisa requirements.txt y el Dockerfile.

### Fase 4 — Servicio listener

Crea **`listener/Dockerfile`**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

CMD ["python", "-u", "main.py"]
```

Crea **`listener/requirements.txt`**:

```
requests==2.32.3
```

Crea **`listener/db.py`**:

```python
"""SQLite local del listener. Tabla replies_processed para idempotencia."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "replies_processed.db"
LAST_DIGEST_JSON = DATA_DIR / "last_digest.json"


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS replies_processed (
                msg_id TEXT PRIMARY KEY,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def is_processed(msg_id: str) -> bool:
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM replies_processed WHERE msg_id = ?", (msg_id,)
        ).fetchone()
    return row is not None


def mark_processed(msg_id: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO replies_processed (msg_id) VALUES (?)",
            (msg_id,),
        )


def get_last_digest_papers() -> list[dict[str, Any]]:
    """Lee el snapshot del ultimo digest. Vacio si nunca se envio uno."""
    if not LAST_DIGEST_JSON.exists():
        return []
    return json.loads(LAST_DIGEST_JSON.read_text())
```

Crea **`listener/reply_parser.py`**:

```python
"""Extrae numeros del cuerpo de un reply.

Acepta '1 3 7', '1, 3, 7', '#1 #3 #7', 'quiero los 2, 5 y 9'.
"""

import re


def parse_reply(body: str) -> list[int]:
    """Lista ordenada por orden de aparicion, deduplicada, cap a 10."""
    tokens = re.findall(r"\b(\d{1,2})\b", body)
    seen: set[int] = set()
    out: list[int] = []
    for t in tokens:
        n = int(t)
        if 1 <= n <= 99 and n not in seen:
            seen.add(n)
            out.append(n)
        if len(out) >= 10:
            break
    return out
```

Crea **`listener/pdf_downloader.py`**:

```python
"""Descarga PDFs de arxiv para los numeros del reply."""

import logging
import re
from pathlib import Path
from typing import Any

import requests

from db import get_last_digest_papers

logger = logging.getLogger("listener")

PDFS_DIR = Path("/app/pdfs")
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def _slugify(text: str, max_len: int = 30) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return cleaned.strip("_")[:max_len]


def download_pdfs(numbers: list[int]) -> list[dict[str, Any]]:
    """Descarga los PDFs y devuelve lista con paths locales y titulos."""
    papers = get_last_digest_papers()
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for n in numbers:
        if not (1 <= n <= len(papers)):
            logger.info("PROFILE: numero %d fuera de rango (1-%d)", n, len(papers))
            continue
        p = papers[n - 1]
        first_author = (
            p["authors"][0].split()[-1] if p["authors"] else "unknown"
        )
        year = p["published"][:4]
        slug = _slugify(p["title"])
        filename = f"{first_author}_{year}_{slug}.pdf"
        path = PDFS_DIR / filename
        try:
            resp = requests.get(p["pdf_url"], timeout=30, stream=True)
            resp.raise_for_status()
            total = 0
            with open(path, "wb") as fh:
                for chunk in resp.iter_content(8192):
                    total += len(chunk)
                    if total > MAX_PDF_BYTES:
                        raise ValueError(f"PDF excede {MAX_PDF_BYTES} bytes")
                    fh.write(chunk)
            out.append({
                "number": n,
                "path": str(path),
                "title": p["title"],
                "arxiv_id": p["arxiv_id"],
            })
            logger.info("PROFILE: descargado paper %d (%s) -> %s", n, p["arxiv_id"], filename)
        except Exception as exc:
            logger.error("ERROR: descarga del paper %d fallo: %s", n, exc)
            if path.exists():
                path.unlink()
    return out
```

Crea **`listener/email_sender.py`**:

```python
"""Envia el reply con PDFs adjuntos."""

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

logger = logging.getLogger("listener")

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
FROM_ADDR = "arxiv-digest@local"
TO_ADDR = os.environ.get("RECIPIENT", "fer@local")


def send_reply(
    original_subject: str, numbers: list[int], pdfs: list[dict[str, Any]]
) -> None:
    """Compone email con los PDFs como attachments y los limpia al final."""
    subject_clean = original_subject.replace("Re: ", "").replace("RE: ", "")
    subject = f"Re: {subject_clean} - {len(pdfs)} PDFs"
    body_lines = [f"PDFs solicitados: {numbers}", "", "Aqui los adjuntos:", ""]
    for p in pdfs:
        body_lines.append(f"  [{p['number']:>2}] {p['title']}")
    body_lines.append("")
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    msg["Subject"] = subject
    msg.set_content("\n".join(body_lines))
    for p in pdfs:
        path = Path(p["path"])
        msg.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=path.name,
        )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    logger.info("RESULT: reply enviado con %d PDFs", len(pdfs))
    for p in pdfs:
        Path(p["path"]).unlink(missing_ok=True)
```

Crea **`listener/main.py`**:

```python
"""Daemon listener. Polls MailHog API y procesa replies con numeros."""

import logging
import os
import time
from typing import Any

import requests

from db import init_db, is_processed, mark_processed
from email_sender import send_reply
from pdf_downloader import download_pdfs
from reply_parser import parse_reply

logger = logging.getLogger("listener")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

MAILHOG_API = os.environ.get("MAILHOG_API", "http://mailhog:8025/api/v2/messages")
POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "30"))
RECIPIENT = os.environ.get("RECIPIENT", "fer@local")
SELF_ADDR = "arxiv-digest@local"


def fetch_replies() -> list[dict[str, Any]]:
    """Mensajes dirigidos al RECIPIENT, excluyendo los que envio el mismo digest."""
    r = requests.get(MAILHOG_API, timeout=5)
    r.raise_for_status()
    out: list[dict[str, Any]] = []
    for m in r.json().get("items", []):
        to_addrs = [t["Mailbox"] + "@" + t["Domain"] for t in m["To"]]
        from_mb = m["From"]["Mailbox"] + "@" + m["From"]["Domain"]
        # solo procesar mensajes hacia el usuario y desde alguien que NO sea el digest
        if RECIPIENT not in to_addrs:
            continue
        if from_mb == SELF_ADDR:
            continue
        subject = m["Content"]["Headers"].get("Subject", [""])[0]
        body = m["Content"]["Body"]
        out.append({"id": m["ID"], "subject": subject, "body": body})
    return out


def main() -> None:
    init_db()
    logger.info(
        "INIT: listener arrancado, polling %s cada %ss",
        MAILHOG_API, POLL_INTERVAL_S,
    )
    while True:
        try:
            for msg in fetch_replies():
                if is_processed(msg["id"]):
                    continue
                numbers = parse_reply(msg["body"])
                if not numbers:
                    mark_processed(msg["id"])
                    continue
                logger.info(
                    "PROFILE: reply %s con numeros %s", msg["id"], numbers
                )
                pdfs = download_pdfs(numbers)
                if pdfs:
                    send_reply(msg["subject"], numbers, pdfs)
                mark_processed(msg["id"])
        except Exception as exc:
            logger.error("ERROR: loop: %s", exc)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
```

**Check fase 4:** Build el servicio listener:

```bash
docker compose build listener
```

Esperado: build exitoso.

### Fase 5 — Levantar el stack completo

```bash
docker compose up -d
docker compose ps
```

Esperado: los tres servicios en estado `running`. `arxiv-mailhog` healthy de inmediato; `arxiv-digest` y `arxiv-listener` quizas marcan unhealthy si el compose no tiene healthchecks definidos — eso es OK, lo importante es que `running` aparezca.

```bash
docker compose logs digest --tail 20
docker compose logs listener --tail 20
```

Esperado en digest:
```
INIT: scheduler arrancado, proximo digest a las 07:00
```

Esperado en listener:
```
INIT: listener arrancado, polling http://mailhog:8025/api/v2/messages cada 30s
```

### Fase 6 — Trigger end-to-end del flow

Trigger del digest manualmente:

```bash
docker compose exec digest python -c "from main import run_digest; run_digest()"
```

Esperado en stdout:
```
... PROFILE: query arxiv category=cs.DC max=50
... PROFILE: fetched 50 papers
... RESULT: email enviado a fer@local con N papers
... RESULT: digest N enviados, M omitidos, 50 nuevos tras dedup
```

Si `N == 0`, ajustar `filters.yml` ampliando keywords (ej. `["learning", "system", "scaling"]`) hasta que matchee.

Verifica el email en MailHog:

```bash
curl -s http://localhost:8025/api/v2/messages | python3 -c "import sys, json; d = json.load(sys.stdin); print('count:', d['count']); print('first subject:', d['items'][0]['Content']['Headers']['Subject'][0] if d['count'] else 'none')"
```

Esperado: `count: 1`, subject contiene `arxiv digest ...`.

Abre MailHog UI en el browser y confirma visualmente el formato del email:

```bash
open http://localhost:8025
```

Ahora simula un reply via la API de MailHog (no se puede hacer reply real desde la UI sin SMTP client, asi que mandamos un mensaje from `fer@local` que el listener interprete como reply):

```bash
docker compose exec listener python <<'EOF'
import smtplib
from email.message import EmailMessage
msg = EmailMessage()
msg["From"] = "fer@local"
msg["To"] = "arxiv-digest@local"
msg["Subject"] = "Re: arxiv digest"
msg.set_content("Por favor enviame 1, 3 y 5")
with smtplib.SMTP("mailhog", 1025) as s:
    s.send_message(msg)
print("reply mock enviado")
EOF
```

**Importante:** el listener filtra mensajes hacia `RECIPIENT=fer@local`. Acabamos de mandar un mensaje **FROM** fer@local **TO** arxiv-digest@local. Eso no caera en el filtro `RECIPIENT in to_addrs`.

**Fix:** en el demo real desde MailHog UI, el reply va de fer@local hacia fer@local (porque MailHog conserva el From original). Para el test automatizado:

```bash
docker compose exec listener python <<'EOF'
import smtplib
from email.message import EmailMessage
msg = EmailMessage()
msg["From"] = "fer@local"
msg["To"] = "fer@local"
msg["Subject"] = "Re: arxiv digest"
msg.set_content("Por favor enviame 1, 3 y 5")
with smtplib.SMTP("mailhog", 1025) as s:
    s.send_message(msg)
print("reply mock enviado")
EOF
```

Espera 30-45 segundos. Mira los logs del listener:

```bash
docker compose logs listener --tail 30
```

Esperado:
```
PROFILE: reply <msg_id> con numeros [1, 3, 5]
PROFILE: descargado paper 1 (...) -> X_2026_....pdf
PROFILE: descargado paper 3 (...) -> Y_2026_....pdf
PROFILE: descargado paper 5 (...) -> Z_2026_....pdf
RESULT: reply enviado con 3 PDFs
```

Verifica el nuevo email en MailHog UI: debe aparecer un email con subject `Re: ... - 3 PDFs` y 3 attachments PDF.

**Check fase 6:** todo el flow end-to-end funciona. Trigger digest → MailHog tiene el digest. Reply mock → 30s despues MailHog tiene el reply con PDFs.

### Fase 7 — Ensayo del demo (3 veces)

Antes de cada ensayo:

```bash
docker compose down -v
docker compose up -d --build
sleep 5
docker compose ps
```

Cronometra desde "docker compose up -d" hasta "tengo email con PDFs en MailHog UI". Objetivo: < 90 segundos completos.

Repite 3 veces. Si los tres ensayos pasan, el demo esta listo.

## 4. Cheat sheet del demo en vivo (10 min frente a Chuctaya)

**Pre-flight (10 min antes de empezar el demo):**

```bash
cd "/Users/99/2026-1/Cloud Computing/arxiv-digest"
docker compose down -v
docker compose up -d --build
sleep 10
docker compose ps      # verificar los 3 en running
open http://localhost:8025
```

**Durante el demo:**

1. **Slide 1-3 (introduccion, 1.5 min):** hablar del problema sin tocar terminal.

2. **Slide 4-6 (arquitectura, codigo, 2 min):** mostrar `docker-compose.yml`, `filters.yml`, y un snippet de `digest/filter_engine.py` en la pantalla.

3. **Slide 7-8 (transicion a demo, 30s):** "Levantamos el sistema..." aunque ya esta levantado.

4. **Demo en vivo (4 min):**

   a. **Triggerar digest:**
      ```bash
      docker compose exec digest python -c "from main import run_digest; run_digest()"
      ```
      Mostrar la salida en pantalla. ~5s.

   b. **Switch al browser con MailHog**. Email recien llegado. Abrirlo, scroll por los papers. Tomarse 30s leyendo titulos y abstracts.

   c. **"Me interesan estos: 2, 5 y 9"**. Click "Reply" en MailHog UI. Editar: `From: fer@local`, `To: fer@local`. Body: `quiero los papers 2, 5, 9`. Send.

   d. **Esperar ~30s** mientras hablas: "El listener esta haciendo poll a la API de MailHog cada 30 segundos. Cuando encuentra mi reply, parsea los numeros, busca esos papers en el snapshot del ultimo digest, descarga los PDFs de arxiv, y me los reenvia adjuntos."

   e. **Refresh de MailHog UI**. Email nuevo con prefijo "Re:" y 3 attachments PDF. Abrir uno de los PDFs, mostrar que es un paper real de arxiv completo.

5. **Slide 10-12 (resultados, deployment, cierre, 2.5 min):** cerrar el caso.

**Plan B si algo se cuelga en vivo:**

Tener grabado `demo_backup.mov` (screencast de 90s con QuickTime de los 5 pasos del demo). Si algo falla, decir "tuvimos un hiccup, dejen muestren la grabacion del flujo completo" y reproducir.

Para grabar el backup:

```bash
# en Mac: QuickTime -> File -> New Screen Recording
# graba la pantalla mientras corres el demo entero
# guarda como ~/2026-1/Cloud Computing/arxiv-digest/demo_backup.mov
```

## 5. Riesgos identificados y mitigaciones

**R1 — arxiv API timeout durante el demo.** Mitigacion: pre-fetch 24h antes y dejar el digest ya enviado en MailHog antes de la presentacion. Si arxiv falla en vivo, dices "el digest ya esta en el inbox" y pasas directo al paso del reply.

**R2 — Filtro vacio (0 papers).** Mitigacion: keywords amplias en `filters.yml`. Antes del demo, correr el digest una vez y verificar count > 0. Si es 0, ampliar.

**R3 — Conflicto de puertos.** Antes del demo:
```bash
lsof -i :1025 -i :8025
```
Si algo ya escucha ahi, cambiar a `:11025` y `:18025` en `docker-compose.yml`.

**R4 — Listener tarda mas de 30s en procesar el reply.** Mitigacion: bajar `POLL_INTERVAL_S=10` en el `.env` antes del demo. Trade-off: mas trafico al MailHog API, irrelevante en demo.

**R5 — PDF de arxiv tarda en descargar.** Mitigacion: timeout esta en 30s, suficiente para PDFs normales. Si un paper tiene PDF de 50 MB, va a ser skipped por el limite de 10 MB — eso es aceptable.

## 6. Que NO hacer

- No cambiar el schema de los dicts de paper (`arxiv_id`, `title`, `authors`, `abstract`, `published`, `pdf_url`, `categories`). Los tres modulos dependen de esos campos.
- No mover `last_digest.json` ni `papers_seen.db` fuera de `/app/data` — el listener espera leerlos ahi via volumen compartido.
- No agregar comandos al reply parser mas alla de numeros. El usuario decidio explicitamente que mantener simplicidad es prioridad sobre features.
- No usar LLM para nada. Determinismo es feature, no limitacion.
- No exponer puertos al mundo en deployment. MailHog en :8025 sin auth es trivialmente compromettible. Si va a Oracle Cloud Free Tier, ponerlo detras de un caddy/nginx con basic auth o cerrarlo al security group.

## 7. Que SI hacer al final si todo funciona

1. `git init && git add . && git commit -m "init: arxiv-digest demo funcionando"`.
2. Tag para el demo: `git tag demo-cs3p2-v1`.
3. Ensayar el demo 3 veces midiendo tiempo.
4. Grabar el screencast de backup.
5. Notificar al usuario que esta listo.

## 8. Tiempo total estimado

| Fase | Tiempo |
|---|---|
| Fase 0-1 (skeleton) | 30 min |
| Fase 2 (compose) | 30 min |
| Fase 3 (digest) | 2.5 h |
| Fase 4 (listener) | 2 h |
| Fase 5 (levantar) | 30 min |
| Fase 6 (smoke test e2e) | 1 h |
| Fase 7 (ensayar 3x) | 1 h |
| Buffer | 1.5 h |
| **Total** | **~9-10 h** |

Una tarde concentrada o 1.5 dias relajados.

Fin del handoff.
