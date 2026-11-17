"""Read-only access to subscribers.db from the listener.

Only a missing table (subscriptions has not created the schema yet) counts as
"no match". Any other SQLite error, such as "database is locked", propagates so
the caller leaves the message unprocessed for the next poll.
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "subscribers.db"
BUSY_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class Subscriber:
    id: int
    email: str


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=BUSY_TIMEOUT_S)
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.row_factory = sqlite3.Row
        yield c
    finally:
        c.close()


def _is_missing_table(exc: sqlite3.OperationalError) -> bool:
    return str(exc).startswith("no such table")


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
    except sqlite3.OperationalError as exc:
        if _is_missing_table(exc):
            return None
        raise
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
    except sqlite3.OperationalError as exc:
        if _is_missing_table(exc):
            return []
        raise
    if not row:
        return []
    try:
        return list(json.loads(row["papers_json"]))
    except (ValueError, TypeError):
        return []
