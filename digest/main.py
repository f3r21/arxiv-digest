"""Daemon principal del digest. Loop con schedule library, 24/7-ready."""

import logging
import os
import time

import schedule

from arxiv_client import fetch_papers
from email_sender import send_digest
from filter_engine import apply_filters, load_filters
from shared_state import (
    get_unseen,
    init_db,
    mark_seen,
    record_digest_issue,
    save_last_digest,
)
from translator_client import translate_papers

logger = logging.getLogger("digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

FILTERS_PATH = "/app/filters.yml"
DIGEST_HOUR = os.environ.get("DIGEST_HOUR", "07:00")


def _resolve_categories(filters: dict) -> list[str]:
    """Env ARXIV_CATEGORIES (CSV) tiene precedencia sobre filters.yml."""
    env_cats = os.environ.get("ARXIV_CATEGORIES", "").strip()
    if env_cats:
        return [c.strip() for c in env_cats.split(",") if c.strip()]
    return list(filters["categories"])


def run_digest() -> None:
    """Ciclo completo: arxiv -> filter -> dedup -> save -> email."""
    filters = load_filters(FILTERS_PATH)
    categories = _resolve_categories(filters)
    filters["categories"] = categories
    filters["category_label"] = ", ".join(categories)
    max_papers = int(filters.get("max_papers", 15))
    raw = fetch_papers(categories, max_results=50)
    new = get_unseen(raw)
    matched = apply_filters(new, filters)
    if not matched:
        logger.info("PROFILE: 0 papers tras filtro, digest no enviado")
        return
    translator_url = os.environ.get("TRANSLATOR_URL", "").strip()
    if translator_url:
        matched = translate_papers(matched, translator_url)
    capped = matched[:max_papers]
    omitted = len(matched) - len(capped)
    save_last_digest(capped)
    issue = record_digest_issue(len(capped))
    send_digest(capped, omitted, filters, issue=issue)
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
