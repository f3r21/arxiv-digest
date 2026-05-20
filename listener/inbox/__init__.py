"""Backends de inbox para el listener (MailHog en dev, Mailsac en live)."""

import os

from .base import InboxBackend
from .mailhog import MailhogBackend
from .mailsac import MailsacBackend


def create_backend() -> InboxBackend:
    """Selecciona el backend segun INBOX_BACKEND env (default 'mailhog')."""
    name = os.environ.get("INBOX_BACKEND", "mailhog").strip().lower()
    if name == "mailsac":
        return MailsacBackend.from_env()
    if name == "mailhog":
        return MailhogBackend.from_env()
    raise ValueError(f"INBOX_BACKEND desconocido: {name}")


__all__ = ["InboxBackend", "MailhogBackend", "MailsacBackend", "create_backend"]
