"""Acceso a subscribers.db desde el digest.

- Lectura: subscribers (lista de activos).
- Escritura: subscriber_seen_papers, subscriber_last_digest, digest_issues.

La tabla subscribers la administra el servicio `subscriptions`; aqui solo
leemos. Las tablas de estado per-usuario y el contador de issues son nuestros.
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

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


def init_state_tables() -> None:
    """Crea tablas que el digest necesita. Idempotente.

    Si el servicio subscriptions arranco primero (lo normal), las tablas ya
    existen y esto es no-op. Si no, las creamos para no chocar al primer run.
    """
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS subscriber_seen_papers (
                subscriber_id INTEGER NOT NULL,
                arxiv_id      TEXT NOT NULL,
                seen_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (subscriber_id, arxiv_id)
            );
            CREATE TABLE IF NOT EXISTS subscriber_last_digest (
                subscriber_id INTEGER PRIMARY KEY,
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
        """)


def list_active_subscribers() -> list[Subscriber]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, email, categories_json, keywords_json, max_papers "
            "FROM subscribers WHERE unsubscribed_at IS NULL ORDER BY id"
        ).fetchall()
    return [
        Subscriber(
            id=int(r["id"]),
            email=str(r["email"]),
            categories=list(json.loads(r["categories_json"])),
            keywords=list(json.loads(r["keywords_json"])),
            max_papers=int(r["max_papers"]),
        )
        for r in rows
    ]


def get_unseen_for(subscriber_id: int, arxiv_ids: list[str]) -> set[str]:
    """Devuelve el subconjunto de arxiv_ids que NO han sido enviados a este sub."""
    if not arxiv_ids:
        return set()
    with _conn() as c:
        placeholders = ",".join("?" for _ in arxiv_ids)
        rows = c.execute(
            f"SELECT arxiv_id FROM subscriber_seen_papers "
            f"WHERE subscriber_id = ? AND arxiv_id IN ({placeholders})",
            (subscriber_id, *arxiv_ids),
        ).fetchall()
    seen = {r["arxiv_id"] for r in rows}
    return {aid for aid in arxiv_ids if aid not in seen}


def record_delivery(
    subscriber_id: int, issue: int, papers: list[dict[str, Any]]
) -> None:
    """Persist a sent digest: reply snapshot plus seen marks, atomically.

    Call only after the email was accepted by SMTP. Both writes share one
    connection and one commit, so either both land or neither does.
    """
    payload = json.dumps(papers, ensure_ascii=False)
    with _conn() as c:
        c.execute(
            """
            INSERT INTO subscriber_last_digest
                (subscriber_id, issue, papers_json, sent_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(subscriber_id) DO UPDATE SET
                issue       = excluded.issue,
                papers_json = excluded.papers_json,
                sent_at     = CURRENT_TIMESTAMP
            """,
            (subscriber_id, issue, payload),
        )
        c.executemany(
            "INSERT OR IGNORE INTO subscriber_seen_papers "
            "(subscriber_id, arxiv_id) VALUES (?, ?)",
            [(subscriber_id, p["arxiv_id"]) for p in papers],
        )


def prune_seen_older_than(days: int) -> int:
    """Delete seen marks older than `days`; return how many rows went.

    Pruning is not safe on its own: the arXiv query has no date bound and
    can return old papers again. It is safe only because run_digest drops
    papers published more than SEEN_RETENTION_DAYS ago before filtering
    (main._within_seen_retention), and a seen mark is never older than its
    paper's publication. Pass the same `days` as that cut.
    """
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM subscriber_seen_papers "
            "WHERE seen_at < datetime('now', ?)",
            (f"-{int(days)} days",),
        )
        return int(cur.rowcount)


def issue_started_since(since_utc: datetime) -> bool:
    """True if a digest issue was reserved at or after `since_utc`.

    digest_issues.sent_at is SQLite CURRENT_TIMESTAMP: UTC text in
    'YYYY-MM-DD HH:MM:SS', which compares correctly as a string.
    """
    threshold = since_utc.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        row = c.execute(
            "SELECT 1 FROM digest_issues WHERE sent_at >= ? LIMIT 1",
            (threshold,),
        ).fetchone()
    return row is not None


def next_issue_number() -> int:
    """Reserva el siguiente numero de issue, lo devuelve."""
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO digest_issues "
            "(subscriber_count, total_papers_sent) VALUES (0, 0)"
        )
        return int(cur.lastrowid)


def finalize_issue(
    issue: int, subscriber_count: int, total_papers_sent: int
) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE digest_issues SET subscriber_count = ?, total_papers_sent = ? "
            "WHERE id = ?",
            (subscriber_count, total_papers_sent, issue),
        )
