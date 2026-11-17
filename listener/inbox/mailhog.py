"""MailHog backend: polls the HTTP API and deletes by id (dev only)."""

import logging
import os
from dataclasses import dataclass

import requests

logger = logging.getLogger("listener")


@dataclass(frozen=True)
class MailhogBackend:
    """Client for MailHog's HTTP API.

    Multi-subscriber: messages are not filtered by recipient (each subscriber
    replies from their own address). Only the digest's own outgoing mail
    (SELF_ADDR) is skipped; the listener matches every other sender against the
    subscribers table.
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

    def verify_private(self) -> None:
        """Nothing to verify: MailHog is a local dev inbox."""

    def list_messages(self) -> list[dict]:
        r = requests.get(self.list_url, timeout=5)
        r.raise_for_status()
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
                "sender": from_mb,
                "recipient": to_addrs[0] if to_addrs else "",
            })
        return out

    def fetch_body(self, msg_id: str) -> str:
        r = requests.get(f"{self.delete_url}/{msg_id}", timeout=5)
        r.raise_for_status()
        return str(r.json()["Content"]["Body"])

    def delete_message(self, msg_id: str) -> None:
        try:
            requests.delete(f"{self.delete_url}/{msg_id}", timeout=5)
        except requests.RequestException as exc:
            logger.warning("WARN: mailhog delete %s failed: %s", msg_id, exc)
