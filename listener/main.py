"""Daemon listener. Polls el backend de inbox configurado y procesa replies."""

import logging
import os
import time

from db import init_db, is_processed, mark_processed
from email_sender import send_reply
from inbox import create_backend
from pdf_downloader import download_pdfs
from reply_parser import parse_reply

logger = logging.getLogger("listener")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "30"))


def main() -> None:
    init_db()
    backend = create_backend()
    logger.info(
        "INIT: listener arrancado, backend=%s polling cada %ss",
        backend.__class__.__name__, POLL_INTERVAL_S,
    )
    while True:
        try:
            for msg in backend.fetch_messages():
                if is_processed(msg["id"]):
                    continue
                numbers = parse_reply(msg["body"])
                if not numbers:
                    mark_processed(msg["id"])
                    backend.delete_message(msg["id"])
                    continue
                logger.info(
                    "PROFILE: reply %s con numeros %s", msg["id"], numbers
                )
                pdfs = download_pdfs(numbers)
                if pdfs:
                    send_reply(msg["subject"], numbers, pdfs)
                mark_processed(msg["id"])
                backend.delete_message(msg["id"])
        except Exception as exc:
            logger.error("ERROR: loop: %s", exc)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
