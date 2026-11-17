"""Log hygiene: subscriber ids instead of emails, tagged lines, no fixed INIT: prefix."""

import logging
import re
import smtplib

import main
from tests.conftest import make_paper

TAG = re.compile(r"^(INIT|RESULT|WARN|ERROR|PROFILE): ")


def test_log_format_has_no_fixed_tag():
    record = logging.LogRecord("listener", logging.INFO, __file__, 1,
                               "RESULT: done", None, None)
    line = logging.Formatter(main.LOG_FORMAT).format(record)

    assert line.endswith(" listener RESULT: done")
    assert "INIT:" not in line


def test_reply_flow_logs_ids_not_emails(inbox, smtp, add_subscriber, caplog):
    ana = add_subscriber("ana@example.com", [make_paper("2411.00001", "One")])
    bob = add_subscriber("bob@example.com")  # no snapshot
    inbox.add("ok", "ana@example.com", "1 7")
    inbox.add("empty", "ana@example.com", "thanks!")
    inbox.add("nosnap", "bob@example.com", "1")
    inbox.add("stranger", "eve@example.com", "1")

    with caplog.at_level(logging.DEBUG, logger="listener"):
        main.poll_once(inbox)

    lines = [r.getMessage() for r in caplog.records if r.name == "listener"]
    assert lines
    assert not [line for line in lines if "@" in line]
    assert all(TAG.match(line) for line in lines), lines
    assert any(f"sub={ana}" in line and line.startswith("RESULT:") for line in lines)
    assert any(f"sub={bob}" in line for line in lines)


def test_smtp_error_log_does_not_leak_the_recipient(inbox, smtp, add_subscriber, caplog):
    sub_id = add_subscriber("ana@example.com", [make_paper("2411.00001", "One")])
    inbox.add("m1", "ana@example.com", "1")
    smtp.fail_with = smtplib.SMTPRecipientsRefused(
        {"ana@example.com": (550, b"mailbox unavailable")}
    )

    with caplog.at_level(logging.ERROR, logger="listener"):
        main.poll_once(inbox)

    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any(f"sub={sub_id}" in e and "SMTPRecipientsRefused" in e for e in errors)
    assert not [e for e in errors if "@" in e]
