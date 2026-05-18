"""Envia el digest a MailHog via SMTP."""

import logging
import os
import smtplib
import textwrap
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("digest")

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
FROM_ADDR = "arxiv-digest@local"
TO_ADDR = os.environ.get("RECIPIENT", "fer@local")
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _wrap_abstract(abstract: str, width: int = 68) -> str:
    wrapped = textwrap.fill(abstract, width=width)
    return textwrap.indent(wrapped, "    ")


def send_digest(
    papers: list[dict[str, Any]], omitted: int, filters: dict[str, Any]
) -> None:
    """Renderiza el template y envia el email."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["wrap_abstract"] = _wrap_abstract
    template = env.get_template("digest.txt")
    body = template.render(
        date=date.today().strftime("%d %b %Y"),
        papers=papers,
        omitted=omitted,
        category=filters["category"],
    )
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    msg["Subject"] = (
        f"arxiv digest {date.today().isoformat()} - {len(papers)} papers"
    )
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    logger.info("RESULT: email enviado a %s con %d papers", TO_ADDR, len(papers))
