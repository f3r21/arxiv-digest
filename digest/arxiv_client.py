"""Cliente de arxiv API. Free, sin auth, devuelve Atom XML."""

import logging
import os
import time
from typing import Any

import feedparser

logger = logging.getLogger("digest")

ARXIV_API = "https://export.arxiv.org/api/query"

# arxiv rate-limita clientes sin User-Agent identificable. Su API etiquette
# pide un UA con nombre del proyecto + email de contacto.
_CONTACT_EMAIL = os.environ.get("ARXIV_CONTACT_EMAIL", "99bigdatacloud@gmail.com")
USER_AGENT = f"arxiv-digest/1.0 (+https://arxivdaily.ignorelist.com; mailto:{_CONTACT_EMAIL})"

# arxiv tiene blips transitorios de 429/503 (visto en prod el 22 May 2026 a las
# 07:00 UTC-5). Sin retry, un blip = no email ese dia. Backoff exponencial.
_RETRY_DELAYS_SECONDS = (15, 30, 60)


def _fetch_with_retry(url: str) -> Any:
    """Llama feedparser con retry-exponencial cuando arxiv devuelve respuesta
    no parseable (rate-limit transitorio, 503, etc).

    Detecta fallo via `feed.bozo` (feedparser flag para parse error). Si la
    respuesta es valida pero vacia (0 entries, no bozo), no reintenta — es
    legitimo no tener papers nuevos para la query.
    """
    for attempt, delay in enumerate((0, *_RETRY_DELAYS_SECONDS)):
        if delay:
            logger.warning(
                "PROFILE: arxiv blip — retry %d/%d en %ds",
                attempt, len(_RETRY_DELAYS_SECONDS), delay,
            )
            time.sleep(delay)
        feed = feedparser.parse(url, agent=USER_AGENT)
        if not getattr(feed, "bozo", False):
            return feed
        # Bozo + no entries = respuesta corrupta (probable rate-limit). Reintento.
        if feed.entries:
            return feed  # bozo pero hay entries — preferimos no perderlos
        raw_err = getattr(feed, "bozo_exception", None)
        logger.warning("PROFILE: bozo en intento %d: %s", attempt + 1, raw_err)
    logger.error("PROFILE: arxiv fallo tras %d retries", len(_RETRY_DELAYS_SECONDS))
    return feed


def _build_search_query(categories: list[str]) -> str:
    """Construye la clausula `search_query=...` para una o varias categorias.

    Una sola categoria -> `cat:cs.DC`.
    Multiples -> `cat:cs.DC+OR+cat:cs.AI` (sin parens — arxiv devuelve 0
    resultados cuando se le pasan parens en la query, incluso aunque el
    formato grammatical sea valido).
    """
    if len(categories) == 1:
        return f"cat:{categories[0]}"
    return "+OR+".join(f"cat:{c}" for c in categories)


def fetch_papers(
    categories: list[str], max_results: int = 50
) -> list[dict[str, Any]]:
    """Consulta arxiv API por papers recientes en una o varias categorias.

    :param categories: lista de codigos de categoria (ej ["cs.DC", "cs.AI"]).
    :param max_results: limite de papers a traer.
    :returns: lista de dicts con arxiv_id, title, authors, abstract,
        published, pdf_url, categories.
    """
    if not categories:
        raise ValueError("fetch_papers requiere al menos una categoria")
    search_query = _build_search_query(categories)
    url = (
        f"{ARXIV_API}?search_query={search_query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    logger.info(
        "PROFILE: query arxiv categories=%s max=%d",
        ",".join(categories), max_results,
    )
    feed = _fetch_with_retry(url)
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
