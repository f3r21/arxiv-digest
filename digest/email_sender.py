"""Envia el digest por SMTP, personalizado por suscriptor."""

import logging
import os
import smtplib
import textwrap
from dataclasses import dataclass
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from unsubscribe_tokens import build_unsubscribe_url

logger = logging.getLogger("digest")

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "0") == "1"
FROM_ADDR = os.environ.get("FROM_ADDR", "arxiv-digest@local")
REPLY_TO = os.environ.get("REPLY_TO", "").strip()
SUBSCRIPTIONS_DOMAIN = os.environ.get("SUBSCRIPTIONS_DOMAIN", "localhost").strip()
TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class SubscriberView:
    """Subset minimo que el sender necesita; lo pasa el orquestador."""

    id: int
    email: str
    categories: list[str]


def _wrap_abstract(abstract: str, width: int = 68) -> str:
    wrapped = textwrap.fill(abstract, width=width)
    return textwrap.indent(wrapped, "    ")


def send_digest_to(
    subscriber: SubscriberView,
    papers: list[dict[str, Any]],
    issue: int,
) -> None:
    """Renderiza y envia el digest a un solo suscriptor."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["wrap_abstract"] = _wrap_abstract
    unsubscribe_url = build_unsubscribe_url(subscriber.id)
    context = {
        "date": date.today().strftime("%d %b %Y"),
        "papers": papers,
        "omitted": 0,
        "category_label": ", ".join(subscriber.categories),
        "issue": issue,
        "subscriber_email": subscriber.email,
        "unsubscribe_url": unsubscribe_url,
    }
    text_body = env.get_template("digest.txt").render(**context)
    html_body = env.get_template("digest.html").render(**context)
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = subscriber.email
    if REPLY_TO:
        msg["Reply-To"] = REPLY_TO
    msg["Subject"] = (
        f"arXiv Daily No. {issue} - {date.today().isoformat()} - "
        f"{len(papers)} papers"
    )
    msg["List-Id"] = f"arXiv Daily <digest.{SUBSCRIPTIONS_DOMAIN}>"
    msg["List-Unsubscribe"] = (
        f"<{unsubscribe_url}>, "
        f"<mailto:unsubscribe@{SUBSCRIPTIONS_DOMAIN}?subject=unsub-{subscriber.id}>"
    )
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        if SMTP_USE_TLS:
            s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logger.info(
        "RESULT: email enviado a %s con %d papers (No. %d)",
        subscriber.email, len(papers), issue,
    )
