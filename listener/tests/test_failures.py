"""Failure handling: which errors are terminal for a message and which leave it for the next poll."""

import logging
import smtplib
import sqlite3

import pytest

import db
import main
from tests.conftest import make_paper

PAPERS = [make_paper("2411.00001", "One")]


@pytest.mark.parametrize("error", [
    smtplib.SMTPDataError(554, b"rejected"),
    smtplib.SMTPServerDisconnected("gone"),
    ConnectionRefusedError("smtp down"),
])
def test_smtp_failure_is_terminal_for_the_message(
    error, inbox, smtp, add_subscriber, caplog
):
    sub_id = add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1")
    smtp.fail_with = error

    with caplog.at_level(logging.ERROR, logger="listener"):
        main.poll_once(inbox)

    assert db.is_processed("m1")
    assert inbox.deleted == ["m1"]
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any("SMTP" in e and f"sub={sub_id}" in e for e in errors)

    smtp.fail_with = None
    inbox.add("m1", "ana@example.com", "1")  # a backend that failed to delete it
    main.poll_once(inbox)
    assert smtp.outbox == []


@pytest.fixture
def lock_subscribers_db(subscribers_db, monkeypatch):
    """Callable that takes an exclusive lock on subscribers.db and returns its release function."""
    import subscriber_repo

    monkeypatch.setattr(subscriber_repo, "BUSY_TIMEOUT_S", 0.05)
    holders: list[sqlite3.Connection] = []

    def _lock():
        holder = sqlite3.connect(subscribers_db, isolation_level=None)
        holder.execute("BEGIN EXCLUSIVE")
        holders.append(holder)
        return holder.close

    yield _lock
    for holder in holders:
        holder.close()


def test_locked_subscribers_db_leaves_message_for_next_poll(
    inbox, smtp, add_subscriber, lock_subscribers_db, caplog
):
    add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1")
    release = lock_subscribers_db()

    with caplog.at_level(logging.ERROR, logger="listener"):
        main.poll_once(inbox)

    assert not db.is_processed("m1")
    assert inbox.deleted == []
    assert smtp.outbox == []
    assert any(r.levelno == logging.ERROR for r in caplog.records)

    release()
    main.poll_once(inbox)
    assert len(smtp.outbox) == 1
    assert db.is_processed("m1")


def test_missing_subscribers_table_counts_as_unknown_sender(
    inbox, smtp, tmp_path, monkeypatch
):
    import subscriber_repo

    monkeypatch.setattr(subscriber_repo, "DATA_DIR", tmp_path)
    monkeypatch.setattr(subscriber_repo, "DB_PATH", tmp_path / "empty.db")
    inbox.add("m1", "ana@example.com", "1")

    main.poll_once(inbox)

    assert db.is_processed("m1")
    assert smtp.outbox == []


def test_snapshot_lookup_raises_on_locked_db(add_subscriber, lock_subscribers_db):
    import subscriber_repo

    sub_id = add_subscriber("ana@example.com", PAPERS)
    lock_subscribers_db()
    with pytest.raises(sqlite3.OperationalError):
        subscriber_repo.get_last_digest_for(sub_id)


def test_snapshot_lookup_is_empty_when_table_is_missing(tmp_path, monkeypatch):
    import subscriber_repo

    monkeypatch.setattr(subscriber_repo, "DATA_DIR", tmp_path)
    monkeypatch.setattr(subscriber_repo, "DB_PATH", tmp_path / "empty.db")

    assert subscriber_repo.get_last_digest_for(1) == []


def test_subject_with_line_break_is_replied_and_processed_in_one_poll(
    inbox, smtp, add_subscriber
):
    add_subscriber("ana@example.com", PAPERS)
    # A decoded RFC 2047 subject can carry CR/LF, which EmailMessage rejects in headers.
    inbox.add("m1", "ana@example.com", "1",
              subject="Re: The Daily Abstract No. 7\r\nBcc: x@example.com")

    main.poll_once(inbox)
    main.poll_once(inbox)

    assert db.is_processed("m1")
    assert inbox.fetched == ["m1"]
    assert len(smtp.outbox) == 1
    subject = smtp.outbox[0]["Subject"]
    assert "\n" not in subject and "\r" not in subject
    assert smtp.outbox[0]["Bcc"] is None


def test_unexpected_error_is_terminal_for_the_message(
    inbox, smtp, add_subscriber, caplog
):
    # A snapshot whose entries are not objects makes paper selection blow up.
    sub_id = add_subscriber("ana@example.com", [1, 2])
    inbox.add("m1", "ana@example.com", "1")

    with caplog.at_level(logging.ERROR, logger="listener"):
        main.poll_once(inbox)
    inbox.add("m1", "ana@example.com", "1")  # a backend that failed to delete it
    main.poll_once(inbox)

    assert db.is_processed("m1")
    assert inbox.fetched == ["m1"]
    assert smtp.outbox == []
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any(f"sub={sub_id}" in e and "m1" in e for e in errors)


def test_bookkeeping_failure_after_send_does_not_resend(
    inbox, smtp, add_subscriber, monkeypatch, caplog
):
    sub_id = add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1")

    def disk_full(*args, **kwargs):
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(main, "record_reply_sent", disk_full)
    with caplog.at_level(logging.ERROR, logger="listener"):
        main.poll_once(inbox)
        main.poll_once(inbox)

    assert len(smtp.outbox) == 1
    assert inbox.deleted == ["m1"]
    assert db.is_processed("m1")
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any(f"sub={sub_id}" in e and "m1" in e for e in errors)
