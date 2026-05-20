"""Lectura de subscribers.db desde el listener. Solo lectura."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "subscribers.db"


@dataclass(frozen=True)
class Subscriber:
    id: int
    email: str


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def find_by_email(email: str) -> Subscriber | None:
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return None
    try:
        with _conn() as c:
            row = c.execute(
                "SELECT id, email FROM subscribers "
                "WHERE email = ? AND unsubscribed_at IS NULL",
                (email_norm,),
            ).fetchone()
    except sqlite3.OperationalError:
        # DB todavia no existe (subscriptions aun no arranco). Tratar como no match.
        return None
    if not row:
        return None
    return Subscriber(id=int(row["id"]), email=str(row["email"]))


def get_last_digest_for(subscriber_id: int) -> list[dict[str, Any]]:
    try:
        with _conn() as c:
            row = c.execute(
                "SELECT papers_json FROM subscriber_last_digest WHERE subscriber_id = ?",
                (subscriber_id,),
            ).fetchone()
    except sqlite3.OperationalError:
        return []
    if not row:
        return []
    try:
        return list(json.loads(row["papers_json"]))
    except (ValueError, TypeError):
        return []
