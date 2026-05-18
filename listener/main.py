"""Daemon listener. Polls MailHog API y procesa replies con numeros."""

import logging
import os
import time
from typing import Any

import requests

from db import init_db, is_processed, mark_processed
from email_sender import send_reply
from pdf_downloader import download_pdfs
from reply_parser import parse_reply

logger = logging.getLogger("listener")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s INIT: %(message)s",
)

MAILHOG_API = os.environ.get("MAILHOG_API", "http://mailhog:8025/api/v2/messages")
POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "30"))
RECIPIENT = os.environ.get("RECIPIENT", "fer@local")
SELF_ADDR = "arxiv-digest@local"


def fetch_replies() -> list[dict[str, Any]]:
    """Mensajes dirigidos al RECIPIENT, excluyendo los que envio el mismo digest."""
    r = requests.get(MAILHOG_API, timeout=5)
    r.raise_for_status()
    out: list[dict[str, Any]] = []
    for m in r.json().get("items", []):
        to_addrs = [t["Mailbox"] + "@" + t["Domain"] for t in m["To"]]
        from_mb = m["From"]["Mailbox"] + "@" + m["From"]["Domain"]
        # solo procesar mensajes hacia el usuario y desde alguien que NO sea el digest
        if RECIPIENT not in to_addrs:
            continue
        if from_mb == SELF_ADDR:
            continue
        subject = m["Content"]["Headers"].get("Subject", [""])[0]
        body = m["Content"]["Body"]
        out.append({"id": m["ID"], "subject": subject, "body": body})
    return out


def main() -> None:
    init_db()
    logger.info(
        "INIT: listener arrancado, polling %s cada %ss",
        MAILHOG_API, POLL_INTERVAL_S,
    )
    while True:
        try:
            for msg in fetch_replies():
                if is_processed(msg["id"]):
                    continue
                numbers = parse_reply(msg["body"])
                if not numbers:
                    mark_processed(msg["id"])
                    continue
                logger.info(
                    "PROFILE: reply %s con numeros %s", msg["id"], numbers
                )
                pdfs = download_pdfs(numbers)
                if pdfs:
                    send_reply(msg["subject"], numbers, pdfs)
                mark_processed(msg["id"])
        except Exception as exc:
            logger.error("ERROR: loop: %s", exc)
        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
