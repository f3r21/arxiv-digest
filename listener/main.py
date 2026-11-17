"""Multi-subscriber reply listener daemon.

Maps the sender of each reply to its subscriber, resolves the requested
numbers through that subscriber's last-digest snapshot and replies to the same
sender with the arXiv links of those papers. Unknown senders are dropped.
"""

import logging
import os
import smtplib
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

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
from subscriber_repo import Subscriber, find_by_email, get_last_digest_for
from tokens import build_manage_url, build_unsubscribe_url

logger = logging.getLogger("listener")
# Each message carries its own tag (INIT:, RESULT:, WARN:, ERROR:, PROFILE:).
LOG_FORMAT = "%(asctime)s %(name)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "30"))
ALIVE_FILE = Path("/tmp/alive")
# Daily reply caps, reset at 00:00 UTC. Resend's free plan allows 100 emails/day
# shared with the digest (one per subscriber) and confirmation emails, so the
# global cap keeps replies from eating the digest's share.
REPLY_DAILY_CAP_PER_SUB = int(os.environ.get("REPLY_DAILY_CAP_PER_SUB", "5"))
REPLY_DAILY_CAP_GLOBAL = int(os.environ.get("REPLY_DAILY_CAP_GLOBAL", "10"))
# Optional healthchecks.io ping URL, hit after each poll that handled every message.
HEALTHCHECK_URL_LISTENER = os.environ.get("HEALTHCHECK_URL_LISTENER", "").strip()


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


def _describe_smtp_error(exc: BaseException) -> str:
    """Error class and SMTP code only: SMTP error texts can quote the recipient address."""
    code = getattr(exc, "smtp_code", None)
    return f"{type(exc).__name__} {code}" if code else type(exc).__name__


# Errors worth another try on the next poll: a locked or busy SQLite file, or
# an inbox API outage. Anything else would fail the same way every poll and,
# with Mailsac, re-fetch the body each time, so it is terminal for the message.
TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (
    sqlite3.OperationalError,
    requests.RequestException,
)


def _finish(msg_id: str, backend: InboxBackend) -> None:
    mark_processed(msg_id)
    backend.delete_message(msg_id)


def _finish_best_effort(msg_id: str, backend: InboxBackend) -> None:
    """Mark processed and delete, logging instead of raising: used on error paths."""
    try:
        mark_processed(msg_id)
    except Exception as exc:
        logger.error("ERROR: could not mark msg %s processed: %s", msg_id, exc)
    try:
        backend.delete_message(msg_id)
    except Exception as exc:
        logger.error("ERROR: could not delete msg %s: %s", msg_id, exc)


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
        logger.info("PROFILE: unknown sender, dropping msg %s", msg_id)
        _finish(msg_id, backend)
        return
    try:
        _reply_to(sub, msg, backend, now)
    except TRANSIENT_ERRORS:
        raise
    except Exception as exc:
        logger.error(
            "ERROR: msg %s from sub=%d failed, not retrying: %s: %s",
            msg_id, sub.id, type(exc).__name__, exc,
        )
        _finish_best_effort(msg_id, backend)


def _reply_to(sub: Subscriber, msg: dict, backend: InboxBackend, now: datetime) -> None:
    msg_id = msg["id"]
    # Fetched only for known senders: each body costs a Mailsac API call.
    numbers = parse_reply(backend.fetch_body(msg_id))
    if not numbers:
        logger.info(
            "PROFILE: sub=%d sent no valid numbers, dropping msg %s", sub.id, msg_id
        )
        _finish(msg_id, backend)
        return
    snapshot = get_last_digest_for(sub.id)
    if not snapshot:
        logger.warning(
            "WARN: sub=%d asked for %s but has no digest snapshot; dropping msg %s",
            sub.id, numbers, msg_id,
        )
        _finish(msg_id, backend)
        return
    logger.info("PROFILE: sub=%d asked for numbers %s", sub.id, numbers)
    papers = _select_papers(numbers, snapshot)
    if not papers:
        logger.info(
            "PROFILE: sub=%d asked only for out-of-range numbers, dropping msg %s",
            sub.id, msg_id,
        )
        _finish(msg_id, backend)
        return
    cap = _cap_reached(sub.id, now)
    if cap:
        logger.warning(
            "WARN: sub=%d hit the %s; no reply for msg %s", sub.id, cap, msg_id
        )
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
            sub.id, msg_id, _describe_smtp_error(exc),
        )
        _finish(msg_id, backend)
        return
    try:
        record_reply_sent(msg_id, sub.id, now)
    except Exception as exc:
        # The reply already went out: leaving the message unprocessed would
        # resend it every poll, and the caps would never see it.
        logger.error(
            "ERROR: reply sent to sub=%d for msg %s but logging it failed: %s",
            sub.id, msg_id, exc,
        )
        _finish_best_effort(msg_id, backend)
        return
    logger.info(
        "RESULT: reply sent to sub=%d with %d papers %s",
        sub.id, len(papers), [p["number"] for p in papers],
    )
    backend.delete_message(msg_id)


def poll_once(backend: InboxBackend, now: datetime | None = None) -> int:
    """Process every unprocessed message currently in the inbox.

    A listing error propagates. A transient error on one message (inbox API
    outage, locked DB) is logged and leaves it unprocessed for the next poll;
    any other error is logged and the message is marked processed and deleted.
    `now` (timezone-aware) dates the replies for the daily caps; defaults to the current time.
    Returns the number of messages left for retry.
    """
    failed = 0
    for msg in backend.list_messages():
        if is_processed(msg["id"]):
            continue
        try:
            _process_message(msg, backend, now or datetime.now(timezone.utc))
        except TRANSIENT_ERRORS as exc:
            failed += 1
            logger.error(
                "ERROR: processing msg %s failed, retrying next poll: %s",
                msg.get("id"), exc,
            )
        except Exception as exc:
            logger.error(
                "ERROR: processing msg %s failed, not retrying: %s: %s",
                msg.get("id"), type(exc).__name__, exc,
            )
            _finish_best_effort(msg["id"], backend)
    return failed


def _ping_heartbeat() -> None:
    """GET the healthchecks.io URL, if configured. Never raises."""
    if not HEALTHCHECK_URL_LISTENER:
        return
    try:
        requests.get(HEALTHCHECK_URL_LISTENER, timeout=10)
    except requests.RequestException as exc:
        logger.warning("WARN: heartbeat ping failed: %s", exc)


def run_cycle(backend: InboxBackend) -> None:
    """One loop iteration: poll, heartbeat only if every message was handled, touch /tmp/alive."""
    try:
        if poll_once(backend) == 0:
            _ping_heartbeat()
    except Exception as exc:
        logger.error("ERROR: poll failed: %s", exc)
    ALIVE_FILE.touch(exist_ok=True)


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
        "INIT: listener started, backend=%s, polling every %ss",
        backend.__class__.__name__, POLL_INTERVAL_S,
    )
    while True:
        run_cycle(backend)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
