"""Read-only acceso al archive publico en /app/data/archive/.

El digest service escribe data/archive/{category}/{YYYY-MM-DD}.json en cada
corrida. Este modulo provee helpers para enumerar/leer esos archivos desde
el servicio subscriptions, que es quien expone /archive/* y /sitemap.xml.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("subscriptions")

ARCHIVE_DIR = Path("/app/data/archive")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ArchiveEdition:
    category: str
    date_str: str  # YYYY-MM-DD
    issue: int
    generated_at: str
    papers: list[dict]


def list_categories() -> list[tuple[str, int]]:
    """Lista (category, num_editions) para todas las categorias con archive.

    Ordenada por num_editions desc, despues alfabetica.
    """
    if not ARCHIVE_DIR.exists():
        return []
    result: list[tuple[str, int]] = []
    for cat_dir in sorted(ARCHIVE_DIR.iterdir()):
        if not cat_dir.is_dir():
            continue
        n = sum(1 for f in cat_dir.glob("*.json"))
        if n > 0:
            result.append((cat_dir.name, n))
    return sorted(result, key=lambda x: (-x[1], x[0]))


def list_editions(category: str, limit: int | None = None) -> list[str]:
    """Lista YYYY-MM-DD dates para una categoria, ordenada desc (mas reciente primero)."""
    cat_dir = ARCHIVE_DIR / category
    if not cat_dir.is_dir():
        return []
    dates = []
    for f in cat_dir.glob("*.json"):
        stem = f.stem
        if DATE_RE.match(stem):
            dates.append(stem)
    dates.sort(reverse=True)
    if limit:
        dates = dates[:limit]
    return dates


def load_edition(category: str, date_str: str) -> ArchiveEdition | None:
    """Lee la edicion (category, date). None si no existe o corrupta."""
    if not DATE_RE.match(date_str):
        return None
    path = ARCHIVE_DIR / category / f"{date_str}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("WARN: archive load %s/%s fallo: %s", category, date_str, exc)
        return None
    return ArchiveEdition(
        category=str(data.get("category") or category),
        date_str=str(data.get("date") or date_str),
        issue=int(data.get("issue") or 0),
        generated_at=str(data.get("generated_at") or ""),
        papers=list(data.get("papers") or []),
    )


def iter_all_editions() -> Iterator[tuple[str, str]]:
    """Genera (category, date_str) para TODAS las ediciones (para sitemap)."""
    for cat, _ in list_categories():
        for date_str in list_editions(cat):
            yield cat, date_str
