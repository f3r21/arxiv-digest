"""The listener's own SQLite DB: idempotency (replies_processed) and sent-reply log for daily caps."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "replies_processed.db"
LAST_DIGEST_JSON = DATA_DIR / "last_digest.json"


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS replies_processed (
                msg_id TEXT PRIMARY KEY,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # One row per reply actually sent; sent_day is the UTC date used by the caps.
        c.execute("""
            CREATE TABLE IF NOT EXISTS replies_sent (
                msg_id        TEXT PRIMARY KEY,
                subscriber_id INTEGER NOT NULL,
                sent_day      TEXT NOT NULL,
                sent_at       TEXT NOT NULL
            )
        """)
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_replies_sent_day "
            "ON replies_sent(sent_day, subscriber_id)"
        )


def utc_day(when: datetime) -> str:
    """UTC calendar date of `when` (aware datetime), e.g. '2026-11-17'."""
    return when.astimezone(timezone.utc).date().isoformat()


def is_processed(msg_id: str) -> bool:
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM replies_processed WHERE msg_id = ?", (msg_id,)
        ).fetchone()
    return row is not None


def mark_processed(msg_id: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO replies_processed (msg_id) VALUES (?)",
            (msg_id,),
        )


def record_reply_sent(msg_id: str, subscriber_id: int, when: datetime) -> None:
    """Log a sent reply and mark its message processed in one transaction."""
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO replies_sent "
            "(msg_id, subscriber_id, sent_day, sent_at) VALUES (?, ?, ?, ?)",
            (msg_id, subscriber_id, utc_day(when),
             when.astimezone(timezone.utc).isoformat(timespec="seconds")),
        )
        c.execute(
            "INSERT OR IGNORE INTO replies_processed (msg_id) VALUES (?)",
            (msg_id,),
        )


def count_replies_sent(day: str, subscriber_id: int | None = None) -> int:
    """Replies sent on UTC `day`, for one subscriber or (None) for everyone."""
    with _conn() as c:
        if subscriber_id is None:
            row = c.execute(
                "SELECT COUNT(*) FROM replies_sent WHERE sent_day = ?", (day,)
            ).fetchone()
        else:
            row = c.execute(
                "SELECT COUNT(*) FROM replies_sent "
                "WHERE sent_day = ? AND subscriber_id = ?",
                (day, subscriber_id),
            ).fetchone()
    return int(row[0])


def get_last_digest_papers() -> list[dict[str, Any]]:
    """Read the legacy single-user digest snapshot. Empty if none was ever sent."""
    if not LAST_DIGEST_JSON.exists():
        return []
    return json.loads(LAST_DIGEST_JSON.read_text())
