"""Failure handling: which errors are terminal for a message and which leave it for the next poll."""

import logging
import smtplib

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
