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

from manage_tokens import build_manage_url
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
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Singleton Jinja env: NO recrear por send (perf con N suscriptores)
_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _wrap_abstract(abstract: str, width: int = 68) -> str:
    wrapped = textwrap.fill(abstract, width=width)
    return textwrap.indent(wrapped, "    ")


def _authors_short(authors: list[str], max_visible: int = 3) -> str:
    """First N authors + 'et al.' si hay más. 'A. Vaswani, N. Shazeer, N. Parmar et al.'"""
    if not authors:
        return ""
    if len(authors) <= max_visible:
        return ", ".join(authors)
    return ", ".join(authors[:max_visible]) + " et al."


_env.filters["wrap_abstract"] = _wrap_abstract
_env.filters["authors_short"] = _authors_short


@dataclass(frozen=True)
class SubscriberView:
    """Subset minimo que el sender necesita; lo pasa el orquestador."""

    id: int
    email: str
    categories: list[str]


def send_digest_to(
    subscriber: SubscriberView,
    papers: list[dict[str, Any]],
    issue: int,
) -> None:
    """Renderiza y envia el digest a un solo suscriptor."""
    unsubscribe_url = build_unsubscribe_url(subscriber.id)
    manage_url = build_manage_url(subscriber.id)
    context = {
        "date": date.today().strftime("%A, %d %b %Y"),  # weekday + date editorial
        "date_iso": date.today().isoformat(),  # for read time / archive links
        "papers": papers,
        "omitted": 0,
        "category_label": ", ".join(subscriber.categories),
        "primary_category": subscriber.categories[0] if subscriber.categories else "",
        "issue": issue,
        "subscriber_email": subscriber.email,
        "unsubscribe_url": unsubscribe_url,
        "manage_url": manage_url,
        "view_in_browser_url": f"{PUBLIC_BASE_URL}/archive/{subscriber.categories[0]}/{date.today().isoformat()}" if subscriber.categories else f"{PUBLIC_BASE_URL}/preview",
        "read_time_min": max(1, len(papers) * 3),  # ~3 min per paper estimate
    }
    text_body = _env.get_template("digest.txt").render(**context)
    html_body = _env.get_template("digest.html").render(**context)
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = subscriber.email
    if REPLY_TO:
        msg["Reply-To"] = REPLY_TO
    msg["Subject"] = (
        f"The Daily Abstract No. {issue} - {date.today().isoformat()} - "
        f"{len(papers)} papers"
    )
    msg["List-Id"] = f"The Daily Abstract <digest.{SUBSCRIPTIONS_DOMAIN}>"
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
