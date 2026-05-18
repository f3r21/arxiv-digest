"""Estado persistente del digest.

Dos archivos en el volumen /app/data:
- papers_seen.db: SQLite con arxiv_ids ya enviados (solo digest escribe).
- last_digest.json: snapshot del ultimo digest (digest escribe, listener lee).
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DATA_DIR = Path("/app/data")
DB_PATH = DATA_DIR / "papers_seen.db"
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
    """Crea la tabla papers_seen si no existe."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS papers_seen (
                arxiv_id TEXT PRIMARY KEY,
                seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_unseen(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra papers que aun no estan en papers_seen."""
    with _conn() as c:
        seen = {row[0] for row in c.execute("SELECT arxiv_id FROM papers_seen")}
    return [p for p in papers if p["arxiv_id"] not in seen]


def mark_seen(arxiv_ids: list[str]) -> None:
    """Marca los arxiv_ids como vistos."""
    with _conn() as c:
        c.executemany(
            "INSERT OR IGNORE INTO papers_seen (arxiv_id) VALUES (?)",
            [(aid,) for aid in arxiv_ids],
        )


def save_last_digest(papers: list[dict[str, Any]]) -> None:
    """Guarda los papers del digest enviado para que el listener los mapee."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LAST_DIGEST_JSON.write_text(json.dumps(papers, ensure_ascii=False, indent=2))
