"""SMTP saliente para confirmacion y welcome. Reusa envs SMTP_* del stack."""

import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("subscriptions")

SMTP_HOST = os.environ.get("SMTP_HOST", "mailhog")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "0") == "1"
FROM_ADDR = os.environ.get("FROM_ADDR", "arxiv-digest@local")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))


def _send(to_addr: str, subject: str, text_body: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
        if SMTP_USE_TLS:
            s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logger.info("RESULT: email enviado a %s subject=%s", to_addr, subject)


def send_confirmation(to_addr: str, token: str, categories: list[str]) -> None:
    confirm_url = f"{PUBLIC_BASE_URL}/confirm?token={token}"
    ctx = {
        "confirm_url": confirm_url,
        "categories": categories,
        "email": to_addr,
    }
    text_body = _env.get_template("email_confirm.txt").render(**ctx)
    html_body = _env.get_template("email_confirm.html").render(**ctx)
    _send(to_addr, "Confirma tu suscripcion al arXiv Daily", text_body, html_body)
