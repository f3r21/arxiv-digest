"""Mailsac backend: REST API with an API key (no password, no IMAP)."""

import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger("listener")


@dataclass(frozen=True)
class MailsacBackend:
    """Client for the Mailsac REST API (live mode).

    Every call counts against the monthly API quota (1500 on the free plan).

    Endpoints:
      GET    /addresses/{inbox}/messages          - message metadata
      GET    /text/{inbox}/{msg_id}               - plain-text body
      DELETE /addresses/{inbox}/messages/{msg_id} - delete the message
    """

    base_url: str
    inbox: str
    api_key: str

    @classmethod
    def from_env(cls) -> "MailsacBackend":
        base_url = os.environ.get(
            "MAILSAC_API_BASE", "https://mailsac.com/api"
        ).rstrip("/")
        inbox = os.environ.get("MAILSAC_INBOX", "").strip()
        api_key = os.environ.get("MAILSAC_API_KEY", "").strip()
        if not inbox or not api_key:
            raise ValueError(
                "MAILSAC_INBOX and MAILSAC_API_KEY are required for INBOX_BACKEND=mailsac"
            )
        return cls(base_url=base_url, inbox=inbox, api_key=api_key)

    def _headers(self) -> dict[str, str]:
        return {"Mailsac-Key": self.api_key, "Accept": "application/json"}

    def list_messages(self) -> list[dict]:
        url = f"{self.base_url}/addresses/{self.inbox}/messages"
        r = requests.get(url, headers=self._headers(), timeout=10)
        r.raise_for_status()
        out: list[dict] = []
        for m in r.json() or []:
            msg_id = m.get("_id") or m.get("id")
            if not msg_id:
                continue
            out.append({
                "id": msg_id,
                "subject": m.get("subject", ""),
                "sender": _first_address(m.get("from")),
                "recipient": _first_address(m.get("to")) or self.inbox,
            })
        return out

    def fetch_body(self, msg_id: str) -> str:
        url = f"{self.base_url}/text/{self.inbox}/{msg_id}"
        r = requests.get(url, headers=self._headers(), timeout=10)
        r.raise_for_status()
        return r.text

    def delete_message(self, msg_id: str) -> None:
        url = f"{self.base_url}/addresses/{self.inbox}/messages/{msg_id}"
        try:
            requests.delete(url, headers=self._headers(), timeout=10)
        except requests.RequestException as exc:
            logger.warning("WARN: mailsac delete %s failed: %s", msg_id, exc)


def _first_address(field: Any) -> str:
    """First address of a Mailsac from/to field."""
    if isinstance(field, list) and field:
        first = field[0]
        if isinstance(first, dict):
            return str(first.get("address", "")).strip()
        return str(first).strip()
    if isinstance(field, str):
        return field.strip()
    return ""
