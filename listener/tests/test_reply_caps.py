"""Daily reply caps (per subscriber and global), reset at 00:00 UTC."""

import logging
from datetime import datetime, timedelta, timezone

import pytest

import db
import main
from tests.conftest import make_paper

PAPERS = [make_paper("2411.00001", "One"), make_paper("2411.00002", "Two")]
NOON_UTC = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def caps(monkeypatch):
    def _set(per_sub: int = 100, global_: int = 100) -> None:
        monkeypatch.setattr(main, "REPLY_DAILY_CAP_PER_SUB", per_sub)
        monkeypatch.setattr(main, "REPLY_DAILY_CAP_GLOBAL", global_)
    return _set


def test_per_subscriber_cap_blocks_extra_replies_from_that_subscriber(
    inbox, smtp, add_subscriber, caps, caplog
):
    caps(per_sub=2)
    ana = add_subscriber("ana@example.com", PAPERS)
    add_subscriber("bob@example.com", PAPERS)
    for i in range(3):
        inbox.add(f"a{i}", "ana@example.com", "1")
    inbox.add("b0", "bob@example.com", "1")

    with caplog.at_level(logging.WARNING, logger="listener"):
        main.poll_once(inbox, now=NOON_UTC)

    recipients = [m["To"] for m in smtp.outbox]
    assert recipients.count("ana@example.com") == 2
    assert recipients.count("bob@example.com") == 1
    assert all(db.is_processed(i) for i in ("a0", "a1", "a2", "b0"))
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(f"sub={ana}" in w and "cap" in w for w in warnings)
    assert not any("ana@example.com" in w for w in warnings)


def test_global_cap_blocks_replies_from_everyone(inbox, smtp, add_subscriber, caps):
    caps(global_=2)
    for name in ("ana", "bob", "cid"):
        add_subscriber(f"{name}@example.com", PAPERS)
        inbox.add(name, f"{name}@example.com", "1")

    main.poll_once(inbox, now=NOON_UTC)

    assert len(smtp.outbox) == 2
    assert all(db.is_processed(i) for i in ("ana", "bob", "cid"))


def test_caps_count_across_polls_within_the_same_utc_day(
    inbox, smtp, add_subscriber, caps
):
    caps(per_sub=1)
    add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1")
    main.poll_once(inbox, now=datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc))
    inbox.add("m2", "ana@example.com", "2")
    main.poll_once(inbox, now=datetime(2026, 11, 17, 23, 59, tzinfo=timezone.utc))

    assert len(smtp.outbox) == 1


def test_caps_reset_at_midnight_utc_not_local_time(inbox, smtp, add_subscriber, caps):
    caps(per_sub=1)
    add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1")
    main.poll_once(inbox, now=datetime(2026, 11, 17, 23, 30, tzinfo=timezone.utc))
    # 20:00 in Lima (UTC-5) on the 17th is already 01:00 UTC on the 18th.
    lima = timezone(timedelta(hours=-5))
    inbox.add("m2", "ana@example.com", "2")
    main.poll_once(inbox, now=datetime(2026, 11, 17, 20, 0, tzinfo=lima))

    assert len(smtp.outbox) == 2


def test_default_caps_come_from_the_environment():
    assert main.REPLY_DAILY_CAP_PER_SUB == 5
    assert 0 < main.REPLY_DAILY_CAP_GLOBAL < 100


def test_capped_subscriber_costs_no_body_fetch(inbox, smtp, add_subscriber, caps):
    # Each Mailsac body fetch is a billed API call; a capped sender should not cost one.
    caps(per_sub=1)
    add_subscriber("ana@example.com", PAPERS)
    inbox.add("m1", "ana@example.com", "1")
    main.poll_once(inbox, now=NOON_UTC)
    inbox.add("m2", "ana@example.com", "2")
    inbox.add("m3", "ana@example.com", "2")
    main.poll_once(inbox, now=NOON_UTC)

    assert inbox.fetched == ["m1"]
    assert db.is_processed("m2") and db.is_processed("m3")
    assert len(smtp.outbox) == 1
