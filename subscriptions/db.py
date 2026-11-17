"""Acceso a subscribers.db. Solo este servicio escribe subscribers/pending."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "subscribers.db"

# Per-recipient confirmation-email budget (subscription-bombing defense).
RECIPIENT_MAX_PER_24H = 1
RECIPIENT_MAX_PER_7D = 3


@dataclass(frozen=True)
class Subscriber:
    id: int
    email: str
    categories: list[str]
    keywords: list[str]
    max_papers: int


@dataclass(frozen=True)
class SendDecision:
    """Outcome of asking the budget for one confirmation email."""

    allowed: bool
    reason: str
    send_id: int | None = None


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

            -- Legacy: stored client IP + raw email and nothing read it.
            DROP TABLE IF EXISTS subscribe_attempts;

            -- Confirmation emails sent, keyed by HMAC(secret, email) so the
            -- send budget works without storing raw addresses.
            CREATE TABLE IF NOT EXISTS confirmation_sends (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_hmac TEXT NOT NULL,
                sent_at        TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_confirmation_sends_recipient
                ON confirmation_sends(recipient_hmac, sent_at);

            CREATE INDEX IF NOT EXISTS idx_confirmation_sends_sent_at
                ON confirmation_sends(sent_at);

            -- Recipients who followed "this wasn't me": no more
            -- confirmation emails. Same HMAC key as confirmation_sends.
            CREATE TABLE IF NOT EXISTS confirmation_suppressions (
                recipient_hmac TEXT PRIMARY KEY,
                created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        _drop_legacy_pending_ip_column(c)


def _drop_legacy_pending_ip_column(c: sqlite3.Connection) -> None:
    """Older schemas kept the client IP on each pending confirmation."""
    columns = {
        row["name"]
        for row in c.execute("PRAGMA table_info(pending_confirmations)")
    }
    if "ip" in columns:
        c.execute("ALTER TABLE pending_confirmations DROP COLUMN ip")


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


def store_pending(token_hash: str, email: str, payload: dict) -> None:
    email_norm = email.strip().lower()
    with _conn() as c:
        c.execute(
            """
            INSERT INTO pending_confirmations (token_hash, email, payload)
            VALUES (?, ?, ?)
            ON CONFLICT(token_hash) DO UPDATE SET
                email = excluded.email,
                payload = excluded.payload,
                created_at = CURRENT_TIMESTAMP
            """,
            (token_hash, email_norm, json.dumps(payload)),
        )


def _sql_utc(moment: datetime) -> str:
    """UTC timestamp in SQLite's CURRENT_TIMESTAMP format."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def prune_expired_pending(ttl_hours: int, now: datetime | None = None) -> int:
    """Delete pending confirmations older than the token TTL.

    Their tokens no longer verify, so the rows only retain an email.
    Returns the number of rows deleted.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = _sql_utc(now - timedelta(hours=ttl_hours))
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM pending_confirmations WHERE datetime(created_at) < ?",
            (cutoff,),
        )
        return cur.rowcount


def delete_pending_for_email(email: str) -> int:
    """Drop every pending confirmation for an address; returns rows deleted."""
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM pending_confirmations WHERE email = ?",
            (email.strip().lower(),),
        )
        return cur.rowcount


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


def reserve_confirmation_send(
    recipient_hmac: str, daily_cap: int, now: datetime | None = None
) -> SendDecision:
    """Record one confirmation email if the budget allows it.

    The check and the insert run in one write transaction so concurrent
    requests cannot both take the last slot.
    """
    now = now or datetime.now(timezone.utc)
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        # Retention: rows past the widest window (7 days) are not needed.
        c.execute(
            "DELETE FROM confirmation_sends WHERE sent_at <= ?",
            (_sql_utc(now - timedelta(days=7)),),
        )
        suppressed = c.execute(
            "SELECT 1 FROM confirmation_suppressions WHERE recipient_hmac = ?",
            (recipient_hmac,),
        ).fetchone()
        if suppressed:
            return SendDecision(allowed=False, reason="suppressed")
        last_24h, last_7d = c.execute(
            """
            SELECT COALESCE(SUM(sent_at > ?), 0), COUNT(*)
            FROM confirmation_sends
            WHERE recipient_hmac = ?
            """,
            (_sql_utc(now - timedelta(hours=24)), recipient_hmac),
        ).fetchone()
        if last_24h >= RECIPIENT_MAX_PER_24H:
            return SendDecision(allowed=False, reason="recipient_24h")
        if last_7d >= RECIPIENT_MAX_PER_7D:
            return SendDecision(allowed=False, reason="recipient_7d")
        utc_midnight = now.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sent_today = c.execute(
            "SELECT COUNT(*) FROM confirmation_sends WHERE sent_at >= ?",
            (_sql_utc(utc_midnight),),
        ).fetchone()[0]
        if sent_today >= daily_cap:
            return SendDecision(allowed=False, reason="global_daily_cap")
        cur = c.execute(
            "INSERT INTO confirmation_sends (recipient_hmac, sent_at) VALUES (?, ?)",
            (recipient_hmac, _sql_utc(now)),
        )
        return SendDecision(allowed=True, reason="ok", send_id=int(cur.lastrowid))


def suppress_confirmations(recipient_hmac: str) -> None:
    """Stop all future confirmation emails to this recipient."""
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO confirmation_suppressions (recipient_hmac) VALUES (?)",
            (recipient_hmac,),
        )


def release_confirmation_send(send_id: int) -> None:
    """Undo a reservation whose email could not be sent."""
    with _conn() as c:
        c.execute("DELETE FROM confirmation_sends WHERE id = ?", (send_id,))
