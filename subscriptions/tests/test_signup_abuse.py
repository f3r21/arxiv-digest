"""Signup abuse protection: send budget, "not me" link, privacy, retention."""

import hashlib
import hmac
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import db
import main
import tokens

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


def test_pending_confirmations_expire_after_ttl():
    db.store_pending("fresh", "a@example.com", {"categories": ["cs.DC"]})
    db.store_pending("stale", "b@example.com", {"categories": ["cs.DC"]})
    now = datetime.now(timezone.utc)

    db.prune_expired_pending(ttl_hours=48, now=now + timedelta(hours=47))
    assert db.pop_pending("fresh") is not None

    db.prune_expired_pending(ttl_hours=48, now=now + timedelta(hours=49))
    assert db.pop_pending("stale") is None


# === Confirmation-email budget ===

T0 = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
ALICE = "a" * 64  # stands in for HMAC(secret, "alice@example.com")


def _reserve(recipient: str, at: datetime, daily_cap: int = 1000):
    return db.reserve_confirmation_send(recipient, daily_cap=daily_cap, now=at)


def test_recipient_gets_at_most_one_confirmation_per_24h():
    assert _reserve(ALICE, T0).allowed
    blocked = _reserve(ALICE, T0 + timedelta(hours=23))
    assert not blocked.allowed
    assert blocked.reason == "recipient_24h"
    assert _reserve(ALICE, T0 + timedelta(hours=24, minutes=1)).allowed


def test_recipient_gets_at_most_three_confirmations_per_7_days():
    for day in range(3):
        assert _reserve(ALICE, T0 + timedelta(days=day, hours=1)).allowed
    blocked = _reserve(ALICE, T0 + timedelta(days=4))
    assert not blocked.allowed
    assert blocked.reason == "recipient_7d"
    # Once the first send is older than 7 days a slot frees up.
    assert _reserve(ALICE, T0 + timedelta(days=7, hours=2)).allowed


def test_recipient_caps_are_per_recipient():
    assert _reserve(ALICE, T0).allowed
    assert _reserve("b" * 64, T0).allowed


def test_global_daily_cap_resets_at_midnight_utc():
    late = datetime(2026, 11, 10, 23, 0, tzinfo=timezone.utc)
    assert _reserve("1" * 64, late, daily_cap=2).allowed
    assert _reserve("2" * 64, late + timedelta(minutes=10), daily_cap=2).allowed

    blocked = _reserve("3" * 64, late + timedelta(minutes=50), daily_cap=2)
    assert not blocked.allowed
    assert blocked.reason == "global_daily_cap"

    # 00:05 UTC is a new day even though the earlier sends are < 24 h old.
    assert _reserve("3" * 64, late + timedelta(hours=1, minutes=5), daily_cap=2).allowed


def test_global_daily_cap_day_follows_utc_not_local_time():
    lima = timezone(timedelta(hours=-5))
    # 20:00 in Lima is 01:00 UTC the next day.
    evening = datetime(2026, 11, 10, 20, 0, tzinfo=lima)
    assert _reserve("1" * 64, evening - timedelta(hours=2), daily_cap=1).allowed
    assert _reserve("2" * 64, evening, daily_cap=1).allowed


def test_released_send_does_not_count_against_the_budget():
    """An SMTP failure gives the slot back so the user can retry."""
    first = _reserve(ALICE, T0, daily_cap=1)
    db.release_confirmation_send(first.send_id)
    assert _reserve(ALICE, T0 + timedelta(minutes=1), daily_cap=1).allowed


def test_send_log_keeps_only_the_last_7_days(isolated_db):
    _reserve(ALICE, T0)
    _reserve("b" * 64, T0 + timedelta(days=7, minutes=1))
    stored = _all_stored_text(isolated_db / "subscribers.db")
    assert ALICE not in stored


def test_email_hmac_is_keyed_and_normalized():
    expected = hmac.new(
        os.environ["SUBSCRIPTIONS_SECRET"].encode(),
        b"alice@example.com",
        hashlib.sha256,
    ).hexdigest()
    assert tokens.email_hmac("alice@example.com") == expected
    assert tokens.email_hmac("  Alice@Example.COM ") == expected
    assert tokens.email_hmac("bob@example.com") != expected


# === /subscribe applies the budget without revealing it ===


def test_blocked_subscribe_looks_exactly_like_success(client, caplog):
    c, sent = client
    first = c.post("/subscribe", data={"email": "bomb@example.com", **FORM})
    caplog.clear()
    second = c.post("/subscribe", data={"email": "Bomb@Example.com", **FORM})

    assert second.status_code == first.status_code == 202
    assert second.json() == first.json()
    assert len(sent) == 1
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any(m.startswith("WARN:") and "recipient_24h" in m for m in warnings)
    assert not any("bomb@example.com" in m.lower() for m in caplog.messages)


def test_subscribe_stops_sending_at_the_global_daily_cap(client, monkeypatch):
    c, sent = client
    monkeypatch.setattr(main, "CONFIRM_DAILY_CAP", 2)
    for i in range(3):
        r = c.post("/subscribe", data={"email": f"user{i}@example.com", **FORM})
        assert r.status_code == 202
        assert r.json() == {
            "status": "pending_confirmation",
            "email": f"user{i}@example.com",
        }
    assert [m["to"] for m in sent] == ["user0@example.com", "user1@example.com"]


def test_failed_send_does_not_use_up_the_recipient_budget(client, monkeypatch):
    c, sent = client

    def broken_send(to_addr, token, categories):
        raise OSError("smtp down")

    monkeypatch.setattr(main.email_outbound, "send_confirmation", broken_send)
    r = c.post("/subscribe", data={"email": "retry@example.com", **FORM})
    assert r.status_code == 502

    monkeypatch.setattr(
        main.email_outbound,
        "send_confirmation",
        lambda to_addr, token, categories: sent.append({"to": to_addr}),
    )
    r = c.post("/subscribe", data={"email": "retry@example.com", **FORM})
    assert r.status_code == 202
    assert sent == [{"to": "retry@example.com"}]
