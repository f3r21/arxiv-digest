"""Cliente de arxiv API. Free, sin auth, devuelve Atom XML."""

import logging
from typing import Any

import feedparser

logger = logging.getLogger("digest")

ARXIV_API = "https://export.arxiv.org/api/query"


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
