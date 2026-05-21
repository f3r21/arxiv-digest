"""Daemon listener multi-suscriptor.

Mapea el sender de cada reply al suscriptor correspondiente; usa el snapshot
per-usuario del ultimo digest para resolver numeros -> arxiv_ids; responde
con los PDFs al mismo sender. Mensajes de senders desconocidos se dropean.
"""

import logging
import os
import time
from pathlib import Path

from db import init_db, is_processed, mark_processed
from email_sender import send_reply
from inbox import create_backend
from pdf_downloader import download_pdfs
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


def _process_message(msg: dict, backend) -> None:
    msg_id = msg["id"]
    sender = (msg.get("sender") or "").strip().lower()
    sub = find_by_email(sender) if sender else None
    if not sub:
        logger.info("PROFILE: sender desconocido (%s), drop msg %s", sender, msg_id)
        mark_processed(msg_id)
        backend.delete_message(msg_id)
        return
    numbers = parse_reply(msg.get("body", ""))
    if not numbers:
        logger.info(
            "PROFILE: reply de sub=%s sin numeros validos, drop msg %s",
            sub.email, msg_id,
        )
        mark_processed(msg_id)
        backend.delete_message(msg_id)
        return
    papers = get_last_digest_for(sub.id)
    if not papers:
        logger.warning(
            "WARN: sub=%s pidio %s pero no tiene snapshot; drop", sub.email, numbers
        )
        mark_processed(msg_id)
        backend.delete_message(msg_id)
        return
    logger.info(
        "PROFILE: sub=%s id=%d pidio numeros %s", sub.email, sub.id, numbers
    )
    pdfs = download_pdfs(numbers, papers)
    if pdfs:
        send_reply(
            to_addr=sub.email,
            original_subject=msg.get("subject", ""),
            numbers=numbers,
            pdfs=pdfs,
            manage_url=build_manage_url(sub.id),
            unsubscribe_url=build_unsubscribe_url(sub.id),
        )
    mark_processed(msg_id)
    backend.delete_message(msg_id)


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
            for msg in backend.fetch_messages():
                if is_processed(msg["id"]):
                    continue
                try:
                    _process_message(msg, backend)
                except Exception as exc:
                    logger.error(
                        "ERROR: procesando msg %s: %s", msg.get("id"), exc
                    )
        except Exception as exc:
            logger.error("ERROR: loop: %s", exc)
        ALIVE_FILE.touch(exist_ok=True)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
