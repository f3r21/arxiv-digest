"""Unsubscribe flow: side-effect-free GET, POST (form and RFC 8058 one-click)
that purges every row about the subscriber."""

import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

import db
import main
import tokens

# Tables that hold rows about one subscriber. digest writes the two
# subscriber_* tables; subscriptions writes the rest.
PER_SUBSCRIBER_TABLES = (
    "subscribers",
    "pending_confirmations",
    "subscriber_seen_papers",
    "subscriber_last_digest",
    "subscribe_attempts",
)


@pytest.fixture
def client():
    return TestClient(main.app)


def _raw() -> sqlite3.Connection:
    return sqlite3.connect(db.DB_PATH)


def _seed_full_subscriber(email: str) -> int:
    """Create a subscriber plus one row in every table that refers to them,
    the way the running system would (subscriptions + digest writes)."""
    sub_id = db.insert_subscriber(email, ["cs.DC"], ["kubernetes"], 10)
    db.store_pending(f"hash-{email}", email, {"categories": ["cs.AI"]}, "10.0.0.1")
    db.log_subscribe_attempt("10.0.0.1", email)
    with _raw() as c:
        c.execute(
            "INSERT INTO subscriber_seen_papers (subscriber_id, arxiv_id) VALUES (?, ?)",
            (sub_id, "2401.00001"),
        )
        c.execute(
            "INSERT INTO subscriber_last_digest (subscriber_id, issue, papers_json) "
            "VALUES (?, ?, ?)",
            (sub_id, 1, "[]"),
        )
    return sub_id


def _rows_about(sub_id: int, email: str) -> dict[str, int]:
    with _raw() as c:
        return {
            "subscribers": c.execute(
                "SELECT COUNT(*) FROM subscribers WHERE id = ? OR email = ?",
                (sub_id, email),
            ).fetchone()[0],
            "pending_confirmations": c.execute(
                "SELECT COUNT(*) FROM pending_confirmations WHERE email = ?", (email,)
            ).fetchone()[0],
            "subscriber_seen_papers": c.execute(
                "SELECT COUNT(*) FROM subscriber_seen_papers WHERE subscriber_id = ?",
                (sub_id,),
            ).fetchone()[0],
            "subscriber_last_digest": c.execute(
                "SELECT COUNT(*) FROM subscriber_last_digest WHERE subscriber_id = ?",
                (sub_id,),
            ).fetchone()[0],
            "subscribe_attempts": c.execute(
                "SELECT COUNT(*) FROM subscribe_attempts WHERE email = ?", (email,)
            ).fetchone()[0],
        }


ALL_PRESENT = {t: 1 for t in PER_SUBSCRIBER_TABLES}
NONE_PRESENT = {t: 0 for t in PER_SUBSCRIBER_TABLES}


def test_get_unsubscribe_has_no_side_effects(client):
    sub_id = _seed_full_subscriber("alice@example.com")
    token = tokens.make_unsubscribe_token(sub_id)

    r = client.get(f"/unsubscribe?token={token}")

    assert r.status_code == 200
    assert _rows_about(sub_id, "alice@example.com") == ALL_PRESENT
    assert db.list_active()[0].id == sub_id


def test_get_unsubscribe_renders_post_form_carrying_token(client):
    sub_id = _seed_full_subscriber("alice@example.com")
    token = tokens.make_unsubscribe_token(sub_id)

    r = client.get(f"/unsubscribe?token={token}")

    assert 'method="post"' in r.text.lower()
    assert f'action="/unsubscribe?token={token}"' in r.text


def test_purge_subscriber_deletes_every_row_about_them_only():
    alice = _seed_full_subscriber("alice@example.com")
    bob = _seed_full_subscriber("bob@example.com")

    db.purge_subscriber(alice)

    assert _rows_about(alice, "alice@example.com") == NONE_PRESENT
    assert _rows_about(bob, "bob@example.com") == ALL_PRESENT


def test_form_post_unsubscribe_purges_and_renders_goodbye_page(client):
    sub_id = _seed_full_subscriber("alice@example.com")
    token = tokens.make_unsubscribe_token(sub_id)

    r = client.post(f"/unsubscribe?token={token}")

    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert _rows_about(sub_id, "alice@example.com") == NONE_PRESENT


def test_one_click_post_unsubscribe_purges(client):
    """RFC 8058: the mailbox provider POSTs the List-Unsubscribe URI with
    this exact form body, no cookies and no page interaction."""
    sub_id = _seed_full_subscriber("alice@example.com")
    token = tokens.make_unsubscribe_token(sub_id)

    r = client.post(
        f"/unsubscribe?token={token}",
        data={"List-Unsubscribe": "One-Click"},
    )

    assert r.status_code == 200
    assert _rows_about(sub_id, "alice@example.com") == NONE_PRESENT


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize(
    "make_token",
    [
        lambda sub_id: "not-a-token",
        lambda sub_id: tokens.make_unsubscribe_token(sub_id) + "x",
        # Right signature, wrong salt: a manage token must not unsubscribe.
        lambda sub_id: tokens.make_manage_token(sub_id),
    ],
    ids=["garbage", "tampered", "wrong-salt"],
)
def test_invalid_unsubscribe_token_shows_expired_page_and_keeps_data(
    client, method, make_token
):
    sub_id = _seed_full_subscriber("alice@example.com")

    r = getattr(client, method)(f"/unsubscribe?token={make_token(sub_id)}")

    assert r.status_code == 400
    assert "link</em> has expired" in r.text
    assert _rows_about(sub_id, "alice@example.com") == ALL_PRESENT


@pytest.mark.parametrize("method", ["get", "post"])
def test_stale_unsubscribe_token_after_purge_shows_expired_page(client, method):
    sub_id = _seed_full_subscriber("alice@example.com")
    token = tokens.make_unsubscribe_token(sub_id)
    client.post(f"/unsubscribe?token={token}")

    r = getattr(client, method)(f"/unsubscribe?token={token}")

    assert r.status_code == 400
    assert "link</em> has expired" in r.text


def test_stale_manage_token_after_purge_shows_expired_page(client):
    sub_id = _seed_full_subscriber("alice@example.com")
    manage_token = tokens.make_manage_token(sub_id)
    client.post(f"/unsubscribe?token={tokens.make_unsubscribe_token(sub_id)}")

    r_get = client.get(f"/manage?token={manage_token}")
    r_post = client.post(
        f"/manage?token={manage_token}",
        data={"categories": ["cs.AI"], "keywords": "", "max_papers": "5"},
    )

    assert r_get.status_code == 400
    assert "link</em> has expired" in r_get.text
    assert r_post.status_code == 400
    assert "link</em> has expired" in r_post.text
    assert _rows_about(sub_id, "alice@example.com") == NONE_PRESENT


def test_manage_page_unsubscribe_goes_through_confirm_and_purge(client):
    sub_id = _seed_full_subscriber("alice@example.com")
    manage = client.get(f"/manage?token={tokens.make_manage_token(sub_id)}")
    unsubscribe_url = re.search(r'href="([^"]*/unsubscribe\?token=[^"]+)"', manage.text)[1]

    confirm = client.get(unsubscribe_url)
    assert _rows_about(sub_id, "alice@example.com") == ALL_PRESENT
    action = re.search(r'<form method="post" action="([^"]+)"', confirm.text)[1]
    done = client.post(action)

    assert done.status_code == 200
    assert _rows_about(sub_id, "alice@example.com") == NONE_PRESENT


def test_resubscribe_after_purge_is_a_fresh_signup(client, monkeypatch):
    sent: list[str] = []
    monkeypatch.setattr(
        main.email_outbound,
        "send_confirmation",
        lambda to_addr, token, categories: sent.append(token),
    )
    old_id = _seed_full_subscriber("alice@example.com")
    old_unsub = tokens.make_unsubscribe_token(old_id)
    client.post(f"/unsubscribe?token={old_unsub}")

    r = client.post(
        "/subscribe",
        data={"email": "alice@example.com", "categories": ["cs.LG"], "max_papers": 7},
    )
    assert r.status_code == 202, r.text
    assert client.get(f"/confirm?token={sent[-1]}").status_code == 200

    [fresh] = db.list_active()
    assert fresh.email == "alice@example.com"
    assert fresh.id != old_id
    assert (fresh.categories, fresh.keywords, fresh.max_papers) == (["cs.LG"], [], 7)
    # The old link must not reach the new subscription (ids are never reused).
    assert client.post(f"/unsubscribe?token={old_unsub}").status_code == 400
    assert db.list_active() == [fresh]


def test_landing_does_not_promise_unsubscribe_by_reply(client):
    """No handler acts on STOP/DELETE replies; the page must not offer it."""
    text = client.get("/").text

    assert "STOP" not in text
    assert "DELETE" not in text


def test_goodbye_page_states_immediate_deletion_not_a_24h_purge(client):
    sub_id = _seed_full_subscriber("alice@example.com")

    text = client.post(f"/unsubscribe?token={tokens.make_unsubscribe_token(sub_id)}").text

    assert "24&nbsp;hours" not in text
    assert "deleted" in text


def _mark_legacy_soft_deleted(sub_id: int) -> None:
    """What the old unsubscribe did: set unsubscribed_at and keep everything."""
    with _raw() as c:
        c.execute(
            "UPDATE subscribers SET unsubscribed_at = '2026-01-01T00:00:00+00:00' "
            "WHERE id = ?",
            (sub_id,),
        )


def test_purge_legacy_unsubscribed_removes_soft_deleted_rows_idempotently():
    gone = _seed_full_subscriber("gone@example.com")
    kept = _seed_full_subscriber("kept@example.com")
    _mark_legacy_soft_deleted(gone)

    assert db.purge_legacy_unsubscribed() == 1
    assert db.purge_legacy_unsubscribed() == 0

    assert _rows_about(gone, "gone@example.com") == NONE_PRESENT
    assert _rows_about(kept, "kept@example.com") == ALL_PRESENT


def test_startup_purges_legacy_soft_deleted_rows(monkeypatch):
    monkeypatch.delenv("RECIPIENT", raising=False)
    gone = _seed_full_subscriber("gone@example.com")
    _mark_legacy_soft_deleted(gone)

    with TestClient(main.app):
        pass

    assert _rows_about(gone, "gone@example.com") == NONE_PRESENT


def test_purge_subscriber_unknown_id_is_a_no_op():
    bob = _seed_full_subscriber("bob@example.com")

    db.purge_subscriber(bob + 999)

    assert _rows_about(bob, "bob@example.com") == ALL_PRESENT


# Copy of digest/subscriber_repo.py init_state_tables() DDL: no foreign keys.
# When digest creates these tables before subscriptions does, ON DELETE
# CASCADE does not exist and the purge has to delete the rows explicitly.
DIGEST_FK_LESS_DDL = """
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
"""


@pytest.fixture
def digest_created_tables(tmp_path, monkeypatch):
    """A fresh DB where digest created its tables first (no FKs, no cascade)."""
    path = tmp_path / "digest-first" / "subscribers.db"
    path.parent.mkdir()
    monkeypatch.setattr(db, "DATA_DIR", path.parent)
    monkeypatch.setattr(db, "DB_PATH", path)
    with sqlite3.connect(path) as c:
        c.executescript(DIGEST_FK_LESS_DDL)
    db.init_db()


@pytest.mark.parametrize(
    "form", [None, {"List-Unsubscribe": "One-Click"}], ids=["form", "one-click"]
)
def test_unsubscribe_purges_rows_in_tables_without_cascade(
    client, digest_created_tables, form
):
    with _raw() as c:
        ddl = c.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'subscriber_seen_papers'"
        ).fetchone()[0]
    assert "REFERENCES" not in ddl
    sub_id = _seed_full_subscriber("alice@example.com")

    r = client.post(f"/unsubscribe?token={tokens.make_unsubscribe_token(sub_id)}", data=form)

    assert r.status_code == 200
    assert _rows_about(sub_id, "alice@example.com") == NONE_PRESENT

