"""Signup abuse protection: send budget, "not me" link, privacy, retention."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

import db
import main

FORM = {"categories": ["cs.DC"], "max_papers": 10}


@pytest.fixture
def client(monkeypatch):
    """TestClient with SMTP replaced by an in-memory outbox."""
    sent: list[dict] = []

    def fake_send(to_addr, token, categories):
        sent.append({"to": to_addr, "token": token, "cats": categories})

    monkeypatch.setattr(main.email_outbound, "send_confirmation", fake_send)
    return TestClient(main.app), sent


def _all_stored_text(db_path) -> list[str]:
    """Every text value in every table of the DB."""
    conn = sqlite3.connect(db_path)
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        ]
        values: list[str] = []
        for t in tables:
            for row in conn.execute(f"SELECT * FROM {t}"):
                values.extend(str(v) for v in row if isinstance(v, str))
        return values
    finally:
        conn.close()


def test_subscribe_does_not_store_client_ip(client, isolated_db):
    c, sent = client
    r = c.post("/subscribe", data={"email": "ip@example.com", **FORM})
    assert r.status_code == 202, r.text
    assert len(sent) == 1
    # TestClient reports the client host as "testclient".
    stored = _all_stored_text(isolated_db / "subscribers.db")
    assert stored, "the pending confirmation should be stored"
    assert not any("testclient" in v for v in stored)


def test_init_db_purges_ips_from_a_legacy_database(isolated_db):
    """A DB created by the old schema loses its stored IPs on startup."""
    path = isolated_db / "subscribers.db"
    path.unlink()
    for suffix in ("-wal", "-shm"):
        (isolated_db / f"subscribers.db{suffix}").unlink(missing_ok=True)
    legacy = sqlite3.connect(path)
    legacy.executescript("""
        CREATE TABLE pending_confirmations (
            token_hash TEXT PRIMARY KEY,
            email      TEXT NOT NULL COLLATE NOCASE,
            payload    TEXT NOT NULL,
            ip         TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO pending_confirmations (token_hash, email, payload, ip)
            VALUES ('h1', 'old@example.com', '{"categories": ["cs.DC"]}', '203.0.113.9');
        CREATE TABLE subscribe_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT, email TEXT, at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO subscribe_attempts (ip, email) VALUES ('203.0.113.9', 'old@example.com');
    """)
    legacy.commit()
    legacy.close()

    db.init_db()

    assert not any("203.0.113.9" in v for v in _all_stored_text(path))
    # The pending confirmation itself survives the migration.
    assert db.pop_pending("h1")["email"] == "old@example.com"
