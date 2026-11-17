"""Multi-subscriber reply listener daemon.

Maps the sender of each reply to its subscriber, resolves the requested
numbers through that subscriber's last-digest snapshot and replies to the same
sender with the arXiv links of those papers. Unknown senders are dropped.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any

from db import init_db, is_processed, mark_processed
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


def _process_message(msg: dict, backend: InboxBackend) -> None:
    msg_id = msg["id"]
    sender = (msg.get("sender") or "").strip().lower()
    sub = find_by_email(sender) if sender else None
    if not sub:
        logger.info("PROFILE: sender desconocido (%s), drop msg %s", sender, msg_id)
        _finish(msg_id, backend)
        return
    numbers = parse_reply(msg.get("body", ""))
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
    if papers:
        send_reply(
            to_addr=sub.email,
            original_subject=msg.get("subject", ""),
            numbers=numbers,
            papers=papers,
            manage_url=build_manage_url(sub.id),
            unsubscribe_url=build_unsubscribe_url(sub.id),
        )
    _finish(msg_id, backend)


def poll_once(backend: InboxBackend) -> None:
    """Process every unprocessed message currently in the inbox."""
    for msg in backend.fetch_messages():
        if is_processed(msg["id"]):
            continue
        try:
            _process_message(msg, backend)
        except Exception as exc:
            logger.error("ERROR: procesando msg %s: %s", msg.get("id"), exc)


def main() -> None:
    init_db()
    backend = create_backend()
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
