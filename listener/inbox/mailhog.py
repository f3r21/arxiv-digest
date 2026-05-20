"""Backend MailHog: polling de la HTTP API y borrado por ID."""

import logging
import os
from dataclasses import dataclass

import requests

logger = logging.getLogger("listener")


@dataclass(frozen=True)
class MailhogBackend:
    """Cliente de la API HTTP de MailHog (modo dev).

    Multi-suscriptor: ya no filtramos por RECIPIENT (cada suscriptor tiene su
    propio email). Solo excluimos mensajes salientes del propio digest
    (SELF_ADDR), el resto se entrega al listener que hace sender-lookup contra
    la tabla subscribers.
    """

    list_url: str
    delete_url: str
    self_addr: str

    @classmethod
    def from_env(cls) -> "MailhogBackend":
        return cls(
            list_url=os.environ.get(
                "MAILHOG_API", "http://mailhog:8025/api/v2/messages"
            ),
            delete_url=os.environ.get(
                "MAILHOG_DELETE_API", "http://mailhog:8025/api/v1/messages"
            ),
            self_addr=os.environ.get("SELF_ADDR", "arxiv-digest@local"),
        )

    def fetch_messages(self) -> list[dict]:
        try:
            r = requests.get(self.list_url, timeout=5)
            r.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("WARN: mailhog list fallo: %s", exc)
            return []
        out: list[dict] = []
        for m in r.json().get("items", []):
            to_addrs = [t["Mailbox"] + "@" + t["Domain"] for t in m["To"]]
            from_mb = m["From"]["Mailbox"] + "@" + m["From"]["Domain"]
            if from_mb == self.self_addr:
                continue
            subject = m["Content"]["Headers"].get("Subject", [""])[0]
            out.append({
                "id": m["ID"],
                "subject": subject,
                "body": m["Content"]["Body"],
                "sender": from_mb,
                "recipient": to_addrs[0] if to_addrs else "",
            })
        return out

    def delete_message(self, msg_id: str) -> None:
        try:
            requests.delete(f"{self.delete_url}/{msg_id}", timeout=5)
        except requests.RequestException as exc:
            logger.warning("WARN: mailhog delete %s fallo: %s", msg_id, exc)
