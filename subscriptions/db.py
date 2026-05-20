"""Acceso a subscribers.db. Solo este servicio escribe subscribers/pending."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "subscribers.db"


@dataclass(frozen=True)
class Subscriber:
    id: int
    email: str
    categories: list[str]
    keywords: list[str]
    max_papers: int


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    """Crea todas las tablas del sistema multi-suscriptor."""
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT NOT NULL UNIQUE COLLATE NOCASE,
                categories_json TEXT NOT NULL,
                keywords_json   TEXT NOT NULL DEFAULT '[]',
                max_papers      INTEGER NOT NULL DEFAULT 15,
                confirmed_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                unsubscribed_at TEXT,
                source          TEXT DEFAULT 'web'
            );

            CREATE INDEX IF NOT EXISTS idx_subscribers_active
                ON subscribers(unsubscribed_at)
                WHERE unsubscribed_at IS NULL;

            CREATE TABLE IF NOT EXISTS pending_confirmations (
                token_hash TEXT PRIMARY KEY,
                email      TEXT NOT NULL COLLATE NOCASE,
                payload    TEXT NOT NULL,
                ip         TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS subscriber_seen_papers (
                subscriber_id INTEGER NOT NULL
                    REFERENCES subscribers(id) ON DELETE CASCADE,
                arxiv_id      TEXT NOT NULL,
                seen_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (subscriber_id, arxiv_id)
            );

            CREATE TABLE IF NOT EXISTS subscriber_last_digest (
                subscriber_id INTEGER PRIMARY KEY
                    REFERENCES subscribers(id) ON DELETE CASCADE,
                issue         INTEGER NOT NULL,
                sent_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                papers_json   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS digest_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                subscriber_count INTEGER NOT NULL,
                total_papers_sent INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subscribe_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                email TEXT,
                at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)


def _row_to_subscriber(row: sqlite3.Row) -> Subscriber:
    return Subscriber(
        id=int(row["id"]),
        email=str(row["email"]),
        categories=list(json.loads(row["categories_json"])),
        keywords=list(json.loads(row["keywords_json"])),
        max_papers=int(row["max_papers"]),
    )


def find_by_email(email: str) -> Subscriber | None:
    email_norm = email.strip().lower()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM subscribers WHERE email = ? AND unsubscribed_at IS NULL",
            (email_norm,),
        ).fetchone()
    return _row_to_subscriber(row) if row else None


def list_active() -> list[Subscriber]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM subscribers WHERE unsubscribed_at IS NULL ORDER BY id"
        ).fetchall()
    return [_row_to_subscriber(r) for r in rows]


def insert_subscriber(
    email: str,
    categories: list[str],
    keywords: list[str],
    max_papers: int,
    source: str = "web",
) -> int:
    email_norm = email.strip().lower()
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO subscribers
                (email, categories_json, keywords_json, max_papers, source)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                categories_json = excluded.categories_json,
                keywords_json   = excluded.keywords_json,
                max_papers      = excluded.max_papers,
                unsubscribed_at = NULL,
                confirmed_at    = CURRENT_TIMESTAMP
            """,
            (
                email_norm,
                json.dumps(categories),
                json.dumps(keywords),
                int(max_papers),
                source,
            ),
        )
        if cur.lastrowid:
            return int(cur.lastrowid)
        row = c.execute(
            "SELECT id FROM subscribers WHERE email = ?", (email_norm,)
        ).fetchone()
        return int(row["id"])


def soft_delete_subscriber(subscriber_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn() as c:
        c.execute(
            "UPDATE subscribers SET unsubscribed_at = ? WHERE id = ?",
            (now, subscriber_id),
        )


def get_subscriber_by_id(subscriber_id: int) -> Subscriber | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM subscribers WHERE id = ?", (subscriber_id,)
        ).fetchone()
    return _row_to_subscriber(row) if row else None


def update_subscription_for(
    subscriber_id: int,
    categories: list[str],
    keywords: list[str],
    max_papers: int,
) -> bool:
    """Actualiza categories/keywords/max_papers de un suscriptor activo.

    Devuelve True si actualizo, False si el suscriptor no existe o ya
    esta dado de baja.
    """
    with _conn() as c:
        cur = c.execute(
            """
            UPDATE subscribers
            SET categories_json = ?,
                keywords_json   = ?,
                max_papers      = ?
            WHERE id = ? AND unsubscribed_at IS NULL
            """,
            (
                json.dumps(categories),
                json.dumps(keywords),
                int(max_papers),
                subscriber_id,
            ),
        )
        return cur.rowcount > 0


def store_pending(
    token_hash: str, email: str, payload: dict, ip: str | None
) -> None:
    email_norm = email.strip().lower()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO pending_confirmations (token_hash, email, payload, ip)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(token_hash) DO UPDATE SET
                email = excluded.email,
                payload = excluded.payload,
                ip = excluded.ip,
                created_at = CURRENT_TIMESTAMP
            """,
            (token_hash, email_norm, json.dumps(payload), ip),
        )


def pop_pending(token_hash: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT email, payload FROM pending_confirmations WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        c.execute(
            "DELETE FROM pending_confirmations WHERE token_hash = ?",
            (token_hash,),
        )
    return {
        "email": str(row["email"]),
        "payload": dict(json.loads(row["payload"])),
    }


def log_subscribe_attempt(ip: str | None, email: str | None) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO subscribe_attempts (ip, email) VALUES (?, ?)",
            (ip or "", (email or "").strip().lower() or None),
        )
