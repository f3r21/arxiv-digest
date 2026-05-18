"""SQLite local del listener. Tabla replies_processed para idempotencia."""

import json
import sqlite3
from contextlib import contextmanager
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


def get_last_digest_papers() -> list[dict[str, Any]]:
    """Lee el snapshot del ultimo digest. Vacio si nunca se envio uno."""
    if not LAST_DIGEST_JSON.exists():
        return []
    return json.loads(LAST_DIGEST_JSON.read_text())
