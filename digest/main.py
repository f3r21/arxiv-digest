"""Daemon principal del digest. Multi-suscriptor.

Una sola consulta a arXiv por corrida (union de categorias), luego filtro
y email per-usuario en memoria. La cache del translator absorbe las
repeticiones de un mismo paper entre suscriptores.
"""

import json
import logging
import os
import time
from pathlib import Path

import schedule

from arxiv_client import fetch_papers
from email_sender import SubscriberView, send_digest_to
from filter_engine import apply_filters
from subscriber_repo import (
    Subscriber,
    finalize_issue,
    get_unseen_for,
    init_state_tables,
    list_active_subscribers,
    mark_seen_for,
    next_issue_number,
    save_last_digest_for,
)
from translator_client import translate_papers

logger = logging.getLogger("digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

DIGEST_HOUR = os.environ.get("DIGEST_HOUR", "07:00")
ARXIV_MAX_RESULTS = int(os.environ.get("ARXIV_MAX_RESULTS", "200"))
ALIVE_FILE = Path("/tmp/alive")


def _papers_for_subscriber(
    sub: Subscriber, raw: list[dict]
) -> list[dict]:
    """Filtro per-suscriptor (categorias + dedup + keywords)."""
    sub_cats = set(sub.categories)
    in_cats = [p for p in raw if sub_cats.intersection(p.get("categories", []))]
    if not in_cats:
        return []
    candidate_ids = [p["arxiv_id"] for p in in_cats]
    unseen_ids = get_unseen_for(sub.id, candidate_ids)
    unseen = [p for p in in_cats if p["arxiv_id"] in unseen_ids]
    if not unseen:
        return []
    if sub.keywords:
        matched = apply_filters(unseen, {"keywords": sub.keywords, "authors": []})
    else:
        # Sin keywords = matchear todos los de la categoria
        matched = [dict(p, match_reason="categoria") for p in unseen]
    return matched[: sub.max_papers]


def run_digest() -> None:
    """Ciclo completo: 1 fetch arXiv -> N filtros/emails -> 1 finalize_issue."""
    subs = list_active_subscribers()
    if not subs:
        logger.info("RESULT: no hay suscriptores activos; skip")
        return
    union_cats = sorted({c for s in subs for c in s.categories})
    logger.info(
        "PROFILE: %d suscriptores, %d categorias union",
        len(subs), len(union_cats),
    )
    raw = fetch_papers(union_cats, max_results=ARXIV_MAX_RESULTS)
    if not raw:
        logger.warning("WARN: arXiv devolvio 0 papers; no se envia digest")
        return

    issue = next_issue_number()
    translator_url = os.environ.get("TRANSLATOR_URL", "").strip()
    total_sent = 0
    sent_count = 0

    for sub in subs:
        try:
            picked = _papers_for_subscriber(sub, raw)
            if not picked:
                logger.info(
                    "PROFILE: sub=%s 0 papers nuevos tras filtro", sub.email
                )
                continue
            if translator_url:
                picked = translate_papers(picked, translator_url)
            save_last_digest_for(sub.id, issue, picked)
            send_digest_to(
                SubscriberView(
                    id=sub.id, email=sub.email, categories=sub.categories
                ),
                picked,
                issue,
            )
            mark_seen_for(sub.id, [p["arxiv_id"] for p in picked])
            total_sent += len(picked)
            sent_count += 1
        except Exception as exc:
            logger.error(
                "ERROR: sub=%s id=%d fallo: %s", sub.email, sub.id, exc
            )

    finalize_issue(issue, sent_count, total_sent)
    logger.info(
        "RESULT: issue %d cerrado; %d suscriptores recibieron %d papers en total",
        issue, sent_count, total_sent,
    )


def main() -> None:
    init_state_tables()
    ALIVE_FILE.touch(exist_ok=True)
    if os.environ.get("RUN_NOW", "0") == "1":
        logger.info("INIT: RUN_NOW=1, ejecutando digest inmediato")
        try:
            run_digest()
        except Exception as exc:
            logger.error("ERROR: RUN_NOW digest fallo: %s", exc)
    schedule.every().day.at(DIGEST_HOUR).do(run_digest)
    logger.info("INIT: scheduler arrancado, proximo digest a las %s", DIGEST_HOUR)
    while True:
        schedule.run_pending()
        ALIVE_FILE.touch(exist_ok=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
