"""Multi-subscriber reply listener daemon.

Maps the sender of each reply to its subscriber, resolves the requested
numbers through that subscriber's last-digest snapshot and replies to the same
sender with the arXiv links of those papers. Unknown senders are dropped.
"""

import logging
import os
import smtplib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from db import (
    count_replies_sent,
    init_db,
    is_processed,
    mark_processed,
    record_reply_sent,
    utc_day,
)
from email_sender import send_reply
from inbox import InboxBackend, create_backend
from reply_parser import parse_reply
from subscriber_repo import find_by_email, get_last_digest_for
from tokens import build_manage_url, build_unsubscribe_url

logger = logging.getLogger("listener")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "30"))
ALIVE_FILE = Path("/tmp/alive")
# Daily reply caps, reset at 00:00 UTC. Resend's free plan allows 100 emails/day
# shared with the digest (one per subscriber) and confirmation emails, so the
# global cap keeps replies from eating the digest's share.
REPLY_DAILY_CAP_PER_SUB = int(os.environ.get("REPLY_DAILY_CAP_PER_SUB", "5"))
REPLY_DAILY_CAP_GLOBAL = int(os.environ.get("REPLY_DAILY_CAP_GLOBAL", "10"))


def _select_papers(
    numbers: list[int], snapshot: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Map reply numbers to snapshot papers, skipping numbers out of range."""
    out: list[dict[str, Any]] = []
    for n in numbers:
        if not (1 <= n <= len(snapshot)):
            logger.info("PROFILE: number %d out of range (1-%d)", n, len(snapshot))
            continue
        p = snapshot[n - 1]
        out.append({
            "number": n,
            "title": p.get("title", ""),
            "arxiv_id": p.get("arxiv_id", ""),
        })
    return out


def _finish(msg_id: str, backend: InboxBackend) -> None:
    mark_processed(msg_id)
    backend.delete_message(msg_id)


def _cap_reached(subscriber_id: int, now: datetime) -> str | None:
    """Name of the daily cap that blocks another reply, or None."""
    day = utc_day(now)
    if count_replies_sent(day) >= REPLY_DAILY_CAP_GLOBAL:
        return f"global cap {REPLY_DAILY_CAP_GLOBAL}/day"
    if count_replies_sent(day, subscriber_id) >= REPLY_DAILY_CAP_PER_SUB:
        return f"per-subscriber cap {REPLY_DAILY_CAP_PER_SUB}/day"
    return None


def _process_message(msg: dict, backend: InboxBackend, now: datetime) -> None:
    msg_id = msg["id"]
    sender = (msg.get("sender") or "").strip().lower()
    sub = find_by_email(sender) if sender else None
    if not sub:
        logger.info("PROFILE: sender desconocido (%s), drop msg %s", sender, msg_id)
        _finish(msg_id, backend)
        return
    # Fetched only for known senders: each body costs a Mailsac API call.
    numbers = parse_reply(backend.fetch_body(msg_id))
    if not numbers:
        logger.info(
            "PROFILE: reply de sub=%s sin numeros validos, drop msg %s",
            sub.email, msg_id,
        )
        _finish(msg_id, backend)
        return
    snapshot = get_last_digest_for(sub.id)
    if not snapshot:
        logger.warning(
            "WARN: sub=%s pidio %s pero no tiene snapshot; drop", sub.email, numbers
        )
        _finish(msg_id, backend)
        return
    logger.info(
        "PROFILE: sub=%s id=%d pidio numeros %s", sub.email, sub.id, numbers
    )
    papers = _select_papers(numbers, snapshot)
    if not papers:
        _finish(msg_id, backend)
        return
    cap = _cap_reached(sub.id, now)
    if cap:
        logger.warning("WARN: sub=%d hit the %s; no reply for msg %s", sub.id, cap, msg_id)
        _finish(msg_id, backend)
        return
    try:
        send_reply(
            to_addr=sub.email,
            original_subject=msg.get("subject", ""),
            papers=papers,
            manage_url=build_manage_url(sub.id),
            unsubscribe_url=build_unsubscribe_url(sub.id),
        )
    except (smtplib.SMTPException, OSError) as exc:
        # Terminal: retrying every poll could resend or loop forever on a rejection.
        logger.error(
            "ERROR: SMTP send failed for sub=%d msg %s, not retrying: %s",
            sub.id, msg_id, exc,
        )
        _finish(msg_id, backend)
        return
    record_reply_sent(msg_id, sub.id, now)
    backend.delete_message(msg_id)


def poll_once(backend: InboxBackend, now: datetime | None = None) -> None:
    """Process every unprocessed message currently in the inbox.

    A listing error propagates. An error on one message (body fetch, locked DB)
    is logged and leaves that message unprocessed for the next poll.
    `now` (timezone-aware) dates the replies for the daily caps; defaults to the current time.
    """
    for msg in backend.list_messages():
        if is_processed(msg["id"]):
            continue
        try:
            _process_message(msg, backend, now or datetime.now(timezone.utc))
        except Exception as exc:
            logger.error("ERROR: procesando msg %s: %s", msg.get("id"), exc)


def startup_guard(
    backend: InboxBackend, sleep: Callable[[float], None] = time.sleep
) -> None:
    """Exit with status 1 unless the inbox is verified private.

    The exit is delayed by one poll interval so that Docker's restart policy
    cannot turn a failing check into a fast loop of billed Mailsac calls.
    """
    try:
        backend.verify_private()
    except Exception as exc:
        logger.error("ERROR: inbox guard refused to start: %s", exc)
        sleep(POLL_INTERVAL_S)
        sys.exit(1)


def main() -> None:
    init_db()
    backend = create_backend()
    startup_guard(backend)
    ALIVE_FILE.touch(exist_ok=True)
    logger.info(
        "INIT: listener arrancado, backend=%s polling cada %ss",
        backend.__class__.__name__, POLL_INTERVAL_S,
    )
    while True:
        try:
            poll_once(backend)
        except Exception as exc:
            logger.error("ERROR: loop: %s", exc)
        ALIVE_FILE.touch(exist_ok=True)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
