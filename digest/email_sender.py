"""Envia el digest por SMTP. Configurable por env para dev (MailHog) o live."""

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
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "0") == "1"
FROM_ADDR = os.environ.get("FROM_ADDR", "arxiv-digest@local")
REPLY_TO = os.environ.get("REPLY_TO", "").strip()
TO_ADDR = os.environ.get("RECIPIENT", "fer@local")
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _wrap_abstract(abstract: str, width: int = 68) -> str:
    wrapped = textwrap.fill(abstract, width=width)
    return textwrap.indent(wrapped, "    ")


def send_digest(
    papers: list[dict[str, Any]],
    omitted: int,
    filters: dict[str, Any],
    issue: int,
) -> None:
    """Renderiza los templates (texto + HTML) y envia el email multipart."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["wrap_abstract"] = _wrap_abstract
    context = {
        "date": date.today().strftime("%d %b %Y"),
        "papers": papers,
        "omitted": omitted,
        "category_label": filters.get("category_label")
        or ", ".join(filters.get("categories") or []),
        "issue": issue,
    }
    text_body = env.get_template("digest.txt").render(**context)
    html_body = env.get_template("digest.html").render(**context)
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = TO_ADDR
    if REPLY_TO:
        msg["Reply-To"] = REPLY_TO
    msg["Subject"] = (
        f"arXiv Daily No. {issue} - {date.today().isoformat()} - "
        f"{len(papers)} papers"
    )
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        if SMTP_USE_TLS:
            s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logger.info(
        "RESULT: email enviado a %s con %d papers (No. %d)",
        TO_ADDR, len(papers), issue,
    )
