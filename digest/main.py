"""Daemon principal del digest. Multi-suscriptor.

Una sola consulta a arXiv por corrida (union de categorias), luego filtro
y email per-usuario en memoria. La cache del translator absorbe las
repeticiones de un mismo paper entre suscriptores.
"""

import json
import logging
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone
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
    next_issue_number,
    prune_seen_older_than,
    record_delivery,
)
from translator_client import translate_papers

logger = logging.getLogger("digest")
logging.basicConfig(
    level=logging.INFO,
    # Each message carries its own tag (INIT:, RESULT:, ...); no fixed prefix.
    format="%(asctime)s %(name)s %(message)s",
)

DIGEST_HOUR = os.environ.get("DIGEST_HOUR", "07:00")
ARXIV_MAX_RESULTS = int(os.environ.get("ARXIV_MAX_RESULTS", "200"))
ALIVE_FILE = Path("/tmp/alive")
PUBLIC_PREVIEW_PATH = Path("/app/data/public_digest_preview.json")
ARCHIVE_DIR = Path("/app/data/archive")
SEED_SUBSCRIBER_ID = 1  # convencion: el seed siempre es id=1 (creado por subscriptions startup)
HEALTHCHECK_URL = os.environ.get("HEALTHCHECK_URL", "").strip()
# A paper older than this cannot reappear in a daily announcement query.
SEEN_RETENTION_DAYS = 30


def _ping_healthcheck(status: str = "ok", body: str | None = None) -> None:
    """Report start/ok/fail to healthchecks.io.

    status: 'ok' (HEALTHCHECK_URL), 'fail' (/fail), 'start' (/start).
    body: optional text sent as a POST body; healthchecks.io shows it in the
    event log, so it carries the run's counts.
    Never raises: a monitoring outage must not interrupt the digest.
    """
    if not HEALTHCHECK_URL:
        return
    suffix = "" if status == "ok" else f"/{status}"
    data = body.encode("utf-8") if body is not None else None
    try:
        urllib.request.urlopen(
            urllib.request.Request(HEALTHCHECK_URL + suffix, data=data),
            timeout=10,
        )
    except Exception as exc:
        logger.warning("WARN: healthcheck ping (%s) failed: %s", status, exc)


def _write_archive(papers: list[dict], issue: int) -> None:
    """Escribe data/archive/{category}/{YYYY-MM-DD}.json publico para SEO.

    Cada paper se clasifica por su PRIMERA categoria arXiv (evita
    duplicate-content entre archives). El archive es publico (no contiene
    info de suscriptores) y alimenta /archive/{cat}/{date} de SEO.

    Cuando el digest se corre varias veces el mismo dia (ej. RUN_NOW + cron),
    sobreescribe el archive de ese dia. Esperable: cada corrida deduplica
    via subscriber_seen_papers, asi que los papers serian distintos.
    """
    if not papers:
        return
    from collections import defaultdict
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for p in papers:
        cats = p.get("categories") or []
        if not cats:
            continue
        primary = cats[0]
        by_cat[primary].append(p)
    if not by_cat:
        return
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total_written = 0
    for cat, papers_in_cat in by_cat.items():
        cat_dir = ARCHIVE_DIR / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        try:
            (cat_dir / f"{date_str}.json").write_text(
                json.dumps(
                    {
                        "category": cat,
                        "date": date_str,
                        "issue": issue,
                        "generated_at": generated_at,
                        "papers": [
                            {
                                "arxiv_id": p.get("arxiv_id", ""),
                                "title": p.get("title", ""),
                                "authors": list(p.get("authors") or []),
                                "abstract": p.get("abstract", ""),
                                "categories": list(p.get("categories") or []),
                                "published": p.get("published", ""),
                                "pdf_url": p.get("pdf_url", ""),
                            }
                            for p in papers_in_cat
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            total_written += 1
        except Exception as exc:
            logger.error("ERROR: archive write %s/%s: %s", cat, date_str, exc)
    logger.info(
        "RESULT: archive escrito %d categorias para %s (issue %d)",
        total_written, date_str, issue,
    )


def _write_public_preview(issue: int, papers: list[dict]) -> None:
    """Snapshot publico para /preview en la landing.

    Toma los papers del seed subscriber (id=1) como muestra representativa
    de "que recibis si te suscribis". Si el seed no recibio nada hoy, no
    sobreescribe el anterior (mantiene el preview existente).
    """
    if not papers:
        return
    try:
        PUBLIC_PREVIEW_PATH.write_text(
            json.dumps(
                {
                    "issue": issue,
                    "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "is_mock": False,
                    "papers": [
                        {
                            "arxiv_id": p.get("arxiv_id", ""),
                            "title": p.get("title", ""),
                            "authors": list(p.get("authors") or [])[:5],
                            "abstract": p.get("abstract", ""),
                            "match_reason": p.get("match_reason", ""),
                        }
                        for p in papers[:5]
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(
            "RESULT: public preview escrito issue=%d papers=%d",
            issue, len(papers),
        )
    except Exception as exc:
        logger.error("ERROR: no se pudo escribir public preview: %s", exc)


def _within_seen_retention(papers: list[dict]) -> list[dict]:
    """Drop papers published before the seen-marks retention window.

    The arXiv query has no date bound, so a low-traffic union of categories
    can return months-old papers. Their seen marks are pruned after
    SEEN_RETENTION_DAYS, so without this cut they would be sent again.
    Papers with an unparseable `published` are kept.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_RETENTION_DAYS)
    kept = []
    for p in papers:
        try:
            published = datetime.fromisoformat(
                str(p.get("published", "")).replace("Z", "+00:00")
            )
        except ValueError:
            kept.append(p)
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= cutoff:
            kept.append(p)
    return kept


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
    _ping_healthcheck("start")
    subs = list_active_subscribers()
    if not subs:
        logger.info("RESULT: no hay suscriptores activos; skip")
        _ping_healthcheck("ok")  # OK aunque haya 0 subs (sistema vivo)
        return
    union_cats = sorted({c for s in subs for c in s.categories})
    logger.info(
        "PROFILE: %d suscriptores, %d categorias union",
        len(subs), len(union_cats),
    )
    raw = fetch_papers(union_cats, max_results=ARXIV_MAX_RESULTS)
    if not raw:
        logger.warning("WARN: arXiv devolvio 0 papers; no se envia digest")
        _ping_healthcheck("fail")  # arxiv broken / rate-limited
        return

    issue = next_issue_number()

    # Escribir archive publico para SEO ANTES del loop de suscriptores.
    # El archive es global (todos los papers del fetch, no filtrados por user).
    _write_archive(raw, issue)
    candidates = _within_seen_retention(raw)
    translator_url = os.environ.get("TRANSLATOR_URL", "").strip()
    total_sent = 0
    sent_count = 0
    failed_count = 0

    for sub in subs:
        try:
            picked = _papers_for_subscriber(sub, candidates)
            if not picked:
                logger.info(
                    "PROFILE: sub id=%d has 0 new papers after filtering", sub.id
                )
                continue
            if translator_url:
                picked = translate_papers(picked, translator_url)
            # Send first; persist only what the subscriber actually received,
            # so a reply never maps onto a digest that never arrived.
            send_digest_to(
                SubscriberView(
                    id=sub.id, email=sub.email, categories=sub.categories
                ),
                picked,
                issue,
            )
            record_delivery(sub.id, issue, picked)
            total_sent += len(picked)
            sent_count += 1
            # snapshot publico para /preview: si es el seed, lo usamos
            if sub.id == SEED_SUBSCRIBER_ID:
                _write_public_preview(issue, picked)
        except Exception as exc:
            failed_count += 1
            # SMTP errors often quote the recipient; keep the address out of logs.
            reason = str(exc).replace(sub.email, f"<sub id={sub.id}>")
            logger.error(
                "ERROR: sub id=%d failed: %s: %s",
                sub.id, type(exc).__name__, reason,
            )

    finalize_issue(issue, sent_count, total_sent)
    logger.info(
        "RESULT: issue %d cerrado; %d suscriptores recibieron %d papers en total",
        issue, sent_count, total_sent,
    )
    try:
        pruned = prune_seen_older_than(SEEN_RETENTION_DAYS)
        logger.info(
            "RESULT: pruned %d seen marks older than %d days",
            pruned, SEEN_RETENTION_DAYS,
        )
    except Exception as exc:
        logger.error("ERROR: seen marks prune failed: %s", exc)
    summary = (
        f"issue={issue} sent={sent_count} failed={failed_count} "
        f"papers={total_sent}"
    )
    if failed_count:
        logger.error("ERROR: digest run had failed sends: %s", summary)
        _ping_healthcheck("fail", body=summary)
    else:
        _ping_healthcheck("ok", body=summary)


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
