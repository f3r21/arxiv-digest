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
