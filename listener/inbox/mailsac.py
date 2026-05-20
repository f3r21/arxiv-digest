"""Backend Mailsac: HTTP REST con API key (sin password ni IMAP)."""

import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger("listener")


@dataclass(frozen=True)
class MailsacBackend:
    """Cliente de la REST API de Mailsac (modo live).

    Endpoints:
      GET    /addresses/{inbox}/messages          - lista metadatos
      GET    /text/{msg_id}                       - cuerpo en texto plano
      DELETE /addresses/{inbox}/messages/{msg_id} - elimina el mensaje
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
                "MAILSAC_INBOX y MAILSAC_API_KEY son obligatorios para INBOX_BACKEND=mailsac"
            )
        return cls(base_url=base_url, inbox=inbox, api_key=api_key)

    def _headers(self) -> dict[str, str]:
        return {"Mailsac-Key": self.api_key, "Accept": "application/json"}

    def fetch_messages(self) -> list[dict]:
        url = f"{self.base_url}/addresses/{self.inbox}/messages"
        try:
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("WARN: mailsac list fallo: %s", exc)
            return []
        out: list[dict] = []
        for m in r.json() or []:
            msg_id = m.get("_id") or m.get("id")
            if not msg_id:
                continue
            body = self._fetch_body(msg_id)
            if body is None:
                continue
            out.append({
                "id": msg_id,
                "subject": m.get("subject", ""),
                "body": body,
                "sender": _first_address(m.get("from")),
                "recipient": _first_address(m.get("to")) or self.inbox,
            })
        return out

    def _fetch_body(self, msg_id: str) -> str | None:
        url = f"{self.base_url}/text/{self.inbox}/{msg_id}"
        try:
            r = requests.get(url, headers=self._headers(), timeout=10)
            r.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("WARN: mailsac body %s fallo: %s", msg_id, exc)
            return None
        return r.text

    def delete_message(self, msg_id: str) -> None:
        url = f"{self.base_url}/addresses/{self.inbox}/messages/{msg_id}"
        try:
            requests.delete(url, headers=self._headers(), timeout=10)
        except requests.RequestException as exc:
            logger.warning("WARN: mailsac delete %s fallo: %s", msg_id, exc)


def _first_address(field: Any) -> str:
    """Extrae la primera direccion de un campo from/to de Mailsac."""
    if isinstance(field, list) and field:
        first = field[0]
        if isinstance(first, dict):
            return str(first.get("address", "")).strip()
        return str(first).strip()
    if isinstance(field, str):
        return field.strip()
    return ""
