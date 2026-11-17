"""Shared fixtures: isolated SQLite files, an in-memory inbox and a fake SMTP server."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeInbox:
    """In-memory inbox backend implementing the InboxBackend protocol."""

    def __init__(self) -> None:
        self.messages: dict[str, dict] = {}
        self.deleted: list[str] = []

    def add(self, msg_id: str, sender: str, body: str,
            subject: str = "Re: The Daily Abstract No. 7 - cs.LG") -> None:
        self.messages[msg_id] = {
            "id": msg_id,
            "subject": subject,
            "body": body,
            "sender": sender,
            "recipient": "replies@example.test",
        }

    def list_messages(self) -> list[dict]:
        return [
            {k: v for k, v in m.items() if k != "body"}
            for m in self.messages.values()
        ]

    def fetch_body(self, msg_id: str) -> str:
        return self.messages[msg_id]["body"]

    def delete_message(self, msg_id: str) -> None:
        self.deleted.append(msg_id)
        self.messages.pop(msg_id, None)


class FakeSMTP:
    """Stands in for smtplib.SMTP; every sent message lands in `outbox`."""

    outbox: list = []
    fail_with: BaseException | None = None

    def __init__(self, host, port, timeout=None) -> None:
        self.host = host

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def starttls(self) -> None:
        pass

    def login(self, user, password) -> None:
        pass

    def send_message(self, msg) -> None:
        if FakeSMTP.fail_with is not None:
            raise FakeSMTP.fail_with
        FakeSMTP.outbox.append(msg)


@pytest.fixture(autouse=True)
def listener_db(tmp_path, monkeypatch):
    """Each test gets a fresh replies_processed.db."""
    import db

    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "replies_processed.db")
    db.init_db()
    return tmp_path


@pytest.fixture
def subscribers_db(tmp_path, monkeypatch):
    """A subscribers.db with the tables the listener reads, mirroring subscriptions/db.py."""
    import subscriber_repo

    path = tmp_path / "subscribers.db"
    monkeypatch.setattr(subscriber_repo, "DATA_DIR", tmp_path)
    monkeypatch.setattr(subscriber_repo, "DB_PATH", path)
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE subscribers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            email           TEXT NOT NULL UNIQUE COLLATE NOCASE,
            categories_json TEXT NOT NULL DEFAULT '[]',
            unsubscribed_at TEXT
        );
        CREATE TABLE subscriber_last_digest (
            subscriber_id INTEGER PRIMARY KEY,
            issue         INTEGER NOT NULL,
            papers_json   TEXT NOT NULL
        );
    """)
    c.commit()
    c.close()
    return path


def make_paper(arxiv_id: str, title: str) -> dict:
    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": ["Ada Lovelace"],
        "published": "2026-11-16",
        "pdf_url": f"http://arxiv.org/pdf/{arxiv_id}",
    }


@pytest.fixture
def add_subscriber(subscribers_db):
    """Insert an active subscriber, optionally with a last-digest snapshot. Returns its id."""

    def _add(email: str, papers: list[dict] | None = None) -> int:
        c = sqlite3.connect(subscribers_db)
        cur = c.execute("INSERT INTO subscribers (email) VALUES (?)", (email,))
        sub_id = int(cur.lastrowid)
        if papers is not None:
            c.execute(
                "INSERT INTO subscriber_last_digest (subscriber_id, issue, papers_json) "
                "VALUES (?, 7, ?)",
                (sub_id, json.dumps(papers)),
            )
        c.commit()
        c.close()
        return sub_id

    return _add


@pytest.fixture
def inbox() -> FakeInbox:
    return FakeInbox()


@pytest.fixture
def smtp(monkeypatch):
    """Replace the SMTP client used by email_sender; yields the FakeSMTP class."""
    import email_sender

    FakeSMTP.outbox = []
    FakeSMTP.fail_with = None
    monkeypatch.setattr(email_sender.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP
