"""Cliente de arxiv API. Free, sin auth, devuelve Atom XML."""

import logging
from typing import Any

import feedparser

logger = logging.getLogger("digest")

ARXIV_API = "https://export.arxiv.org/api/query"


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
