"""One poll cycle: /tmp/alive touch plus the optional healthchecks heartbeat."""

import logging

import pytest
import requests

import main
from tests.conftest import FakeInbox

HC_URL = "https://hc-ping.test/uuid"


class BrokenInbox(FakeInbox):
    def list_messages(self) -> list[dict]:
        raise requests.ConnectionError("inbox down")


@pytest.fixture
def alive(tmp_path, monkeypatch):
    path = tmp_path / "alive"
    monkeypatch.setattr(main, "ALIVE_FILE", path)
    return path


@pytest.fixture
def pings(monkeypatch):
    calls: list[str] = []

    def fake_get(url, timeout=None):
        calls.append(url)

    monkeypatch.setattr(main.requests, "get", fake_get)
    monkeypatch.setattr(main, "HEALTHCHECK_URL_LISTENER", HC_URL)
    return calls


def test_successful_cycle_pings_heartbeat_and_touches_alive(alive, pings, inbox):
    main.run_cycle(inbox)

    assert pings == [HC_URL]
    assert alive.exists()


def test_failed_listing_skips_heartbeat_but_keeps_loop_alive(alive, pings, caplog):
    with caplog.at_level(logging.ERROR, logger="listener"):
        main.run_cycle(BrokenInbox())

    assert pings == []
    assert alive.exists()
    assert any(r.getMessage().startswith("ERROR:") for r in caplog.records)


def test_message_left_for_retry_skips_heartbeat(alive, pings, add_subscriber):
    class BodylessInbox(FakeInbox):
        def fetch_body(self, msg_id: str) -> str:
            raise requests.HTTPError("503")

    add_subscriber("ana@example.com", [])
    inbox = BodylessInbox()
    inbox.add("m1", "ana@example.com", "1")

    main.run_cycle(inbox)

    assert pings == []
    assert alive.exists()


def test_heartbeat_network_error_is_tolerated(alive, inbox, monkeypatch, caplog):
    def boom(url, timeout=None):
        raise requests.ConnectionError("hc down")

    monkeypatch.setattr(main.requests, "get", boom)
    monkeypatch.setattr(main, "HEALTHCHECK_URL_LISTENER", HC_URL)

    with caplog.at_level(logging.WARNING, logger="listener"):
        main.run_cycle(inbox)

    assert alive.exists()
    assert any(r.getMessage().startswith("WARN:") for r in caplog.records)


def test_no_heartbeat_when_url_is_unset(alive, pings, inbox, monkeypatch):
    monkeypatch.setattr(main, "HEALTHCHECK_URL_LISTENER", "")

    main.run_cycle(inbox)

    assert pings == []
