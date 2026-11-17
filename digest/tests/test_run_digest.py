"""End-to-end tests for main.run_digest.

Fakes sit at the external boundaries only: the arXiv fetch, the SMTP
server, the healthchecks.io HTTP ping and the translator (disabled via
an empty TRANSLATOR_URL). The SQLite DB is a real temp file.
"""

import json
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest

import email_sender
import main
import subscriber_repo


def arxiv_timestamp(days_ago: float) -> str:
    """`published` in the format the arXiv Atom feed uses."""
    t = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


PAPERS = [
    {
        "arxiv_id": "2611.00001",
        "title": "Distributed Consensus at Scale",
        "abstract": "We study consensus.",
        "authors": ["A. Author"],
        "categories": ["cs.DC"],
        "published": arxiv_timestamp(1),
        "pdf_url": "https://arxiv.org/pdf/2611.00001",
    },
    {
        "arxiv_id": "2611.00002",
        "title": "Scheduling Pods",
        "abstract": "We schedule pods.",
        "authors": ["B. Author"],
        "categories": ["cs.DC"],
        "published": arxiv_timestamp(1),
        "pdf_url": "https://arxiv.org/pdf/2611.00002",
    },
]


class FakeSMTP:
    """Stands in for smtplib.SMTP. Records sent messages; fails for chosen recipients."""

    sent: list = []
    failing_recipients: set = set()

    def __init__(self, host, port, timeout=None):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        if msg["To"] in FakeSMTP.failing_recipients:
            # Real SMTP errors (e.g. SMTPRecipientsRefused) quote the address.
            raise OSError(f"550 recipient refused: {msg['To']}")
        FakeSMTP.sent.append(msg)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Temp DB with a subscribers table plus fakes for every external service."""
    monkeypatch.setattr(subscriber_repo, "DATA_DIR", tmp_path)
    monkeypatch.setattr(subscriber_repo, "DB_PATH", tmp_path / "subscribers.db")
    monkeypatch.setattr(main, "ARCHIVE_DIR", tmp_path / "archive")
    monkeypatch.setattr(main, "PUBLIC_PREVIEW_PATH", tmp_path / "preview.json")
    monkeypatch.delenv("TRANSLATOR_URL", raising=False)

    with sqlite3.connect(tmp_path / "subscribers.db") as c:
        c.execute(
            """
            CREATE TABLE subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                categories_json TEXT NOT NULL,
                keywords_json TEXT NOT NULL DEFAULT '[]',
                max_papers INTEGER NOT NULL DEFAULT 10,
                unsubscribed_at TEXT
            )
            """
        )
    subscriber_repo.init_state_tables()

    FakeSMTP.sent = []
    FakeSMTP.failing_recipients = set()
    monkeypatch.setattr(email_sender.smtplib, "SMTP", FakeSMTP)

    fetched = {"papers": list(PAPERS)}
    monkeypatch.setattr(
        main, "fetch_papers", lambda cats, max_results=0: list(fetched["papers"])
    )

    pings: list[tuple[str, bytes | None]] = []

    def fake_urlopen(req, timeout=None):
        if isinstance(req, urllib.request.Request):
            pings.append((req.full_url, req.data))
        else:
            pings.append((req, None))

    monkeypatch.setattr(main, "HEALTHCHECK_URL", "https://hc.example/ping/abc")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    return {"tmp": tmp_path, "pings": pings, "fetched": fetched}


def add_subscriber(env, email, categories=("cs.DC",)) -> int:
    with sqlite3.connect(env["tmp"] / "subscribers.db") as c:
        cur = c.execute(
            "INSERT INTO subscribers (email, categories_json) VALUES (?, ?)",
            (email, json.dumps(list(categories))),
        )
        return int(cur.lastrowid)


def snapshot_for(env, subscriber_id):
    """Read the reply snapshot the way the listener does (cross-service contract)."""
    with sqlite3.connect(env["tmp"] / "subscribers.db") as c:
        row = c.execute(
            "SELECT issue, papers_json FROM subscriber_last_digest "
            "WHERE subscriber_id = ?",
            (subscriber_id,),
        ).fetchone()
    if row is None:
        return None
    return row[0], [p["arxiv_id"] for p in json.loads(row[1])]


def seen_ids(subscriber_id):
    ids = [p["arxiv_id"] for p in PAPERS]
    return set(ids) - subscriber_repo.get_unseen_for(subscriber_id, ids)


def test_successful_send_writes_snapshot_and_seen(env):
    sub_id = add_subscriber(env, "ok@example.com")

    main.run_digest()

    assert [m["To"] for m in FakeSMTP.sent] == ["ok@example.com"]
    issue, ids = snapshot_for(env, sub_id)
    assert ids == ["2611.00001", "2611.00002"]
    assert seen_ids(sub_id) == {"2611.00001", "2611.00002"}


def test_smtp_failure_writes_neither_snapshot_nor_seen(env):
    ok_id = add_subscriber(env, "ok@example.com")
    bad_id = add_subscriber(env, "bad@example.com")
    FakeSMTP.failing_recipients = {"bad@example.com"}

    main.run_digest()

    assert snapshot_for(env, bad_id) is None
    assert seen_ids(bad_id) == set()
    # The healthy subscriber is unaffected by the other one's failure.
    assert snapshot_for(env, ok_id) is not None
    assert seen_ids(ok_id) == {"2611.00001", "2611.00002"}


def test_any_failed_send_pings_fail_with_counts(env):
    add_subscriber(env, "ok@example.com")
    add_subscriber(env, "bad@example.com")
    FakeSMTP.failing_recipients = {"bad@example.com"}

    main.run_digest()

    urls = [u for u, _ in env["pings"]]
    assert urls == [
        "https://hc.example/ping/abc/start",
        "https://hc.example/ping/abc/fail",
    ]
    body = env["pings"][-1][1].decode()
    assert "sent=1" in body
    assert "failed=1" in body


def test_all_sends_ok_pings_ok(env):
    add_subscriber(env, "ok@example.com")

    main.run_digest()

    urls = [u for u, _ in env["pings"]]
    assert urls == [
        "https://hc.example/ping/abc/start",
        "https://hc.example/ping/abc",
    ]


def test_list_unsubscribe_is_https_one_click_without_mailto(env):
    add_subscriber(env, "ok@example.com")

    main.run_digest()

    msg = FakeSMTP.sent[0]
    header = msg["List-Unsubscribe"]
    assert "mailto:" not in header
    assert header.startswith("<https://localhost/unsubscribe?token=")
    assert header.endswith(">")
    assert header.count("<") == 1
    assert msg["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_logs_identify_subscribers_by_id_not_email(env, caplog):
    ok_id = add_subscriber(env, "ok@example.com")
    bad_id = add_subscriber(env, "bad@example.com")
    add_subscriber(env, "math@example.com", categories=("math.AG",))
    FakeSMTP.failing_recipients = {"bad@example.com"}

    with caplog.at_level("INFO", logger="digest"):
        main.run_digest()

    text = caplog.text
    assert "@example.com" not in text
    assert f"id={ok_id}" in text
    assert f"id={bad_id}" in text


def test_run_prunes_seen_marks_older_than_30_days(env):
    sub_id = add_subscriber(env, "ok@example.com", categories=("math.AG",))
    with sqlite3.connect(env["tmp"] / "subscribers.db") as c:
        c.executemany(
            "INSERT INTO subscriber_seen_papers (subscriber_id, arxiv_id, seen_at) "
            "VALUES (?, ?, datetime('now', ?))",
            [
                (sub_id, "2611.00001", "-31 days"),
                (sub_id, "2611.00002", "-29 days"),
            ],
        )

    main.run_digest()

    assert seen_ids(sub_id) == {"2611.00002"}


def test_papers_older_than_seen_retention_are_never_sent(env):
    # A low-traffic category can return months-old papers in the fetch
    # window; once their seen mark is pruned they must not be re-sent.
    sub_id = add_subscriber(env, "ok@example.com")
    old = dict(PAPERS[0], published=arxiv_timestamp(31))
    env["fetched"]["papers"] = [old, PAPERS[1]]

    main.run_digest()

    _, ids = snapshot_for(env, sub_id)
    assert ids == ["2611.00002"]


def test_empty_arxiv_pings_fail_and_sends_nothing(env):
    add_subscriber(env, "ok@example.com")
    env["fetched"]["papers"] = []

    main.run_digest()

    assert FakeSMTP.sent == []
    urls = [u for u, _ in env["pings"]]
    assert urls == [
        "https://hc.example/ping/abc/start",
        "https://hc.example/ping/abc/fail",
    ]
