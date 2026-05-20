"""Descarga PDFs de arxiv para los numeros del reply."""

import logging
import re
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("listener")

PDFS_DIR = Path("/app/pdfs")
MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


def _slugify(text: str, max_len: int = 30) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return cleaned.strip("_")[:max_len]


def download_pdfs(
    numbers: list[int], papers: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Descarga los PDFs y devuelve lista con paths locales y titulos.

    `papers` viene del snapshot per-suscriptor (subscriber_last_digest).
    """
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for n in numbers:
        if not (1 <= n <= len(papers)):
            logger.info("PROFILE: numero %d fuera de rango (1-%d)", n, len(papers))
            continue
        p = papers[n - 1]
        first_author = (
            p["authors"][0].split()[-1] if p.get("authors") else "unknown"
        )
        year = (p.get("published") or "0000")[:4]
        slug = _slugify(p.get("title") or "untitled")
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
                "title": p.get("title", ""),
                "arxiv_id": p.get("arxiv_id", ""),
            })
            logger.info(
                "PROFILE: descargado paper %d (%s) -> %s",
                n, p.get("arxiv_id", "?"), filename,
            )
        except Exception as exc:
            logger.error("ERROR: descarga del paper %d fallo: %s", n, exc)
            if path.exists():
                path.unlink()
    return out
