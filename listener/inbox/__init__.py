"""Inbox backends for the listener (MailHog in dev, Mailsac live)."""

import os

from .base import InboxBackend
from .mailhog import MailhogBackend
from .mailsac import InboxGuardError, MailsacBackend


def create_backend() -> InboxBackend:
    """Pick the backend from the INBOX_BACKEND env var (default 'mailhog')."""
    name = os.environ.get("INBOX_BACKEND", "mailhog").strip().lower()
    if name == "mailsac":
        return MailsacBackend.from_env()
    if name == "mailhog":
        return MailhogBackend.from_env()
    raise ValueError(f"Unknown INBOX_BACKEND: {name}")


__all__ = [
    "InboxBackend",
    "InboxGuardError",
    "MailhogBackend",
    "MailsacBackend",
    "create_backend",
]
