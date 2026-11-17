"""Mailsac private-inbox guard at startup (HTTP mocked)."""

import logging

import pytest
import requests

import main
from inbox.mailsac import InboxGuardError, MailsacBackend
from tests.test_inbox_backends import BASE, INBOX, FakeHTTP, FakeResponse

ADDRESS_URL = f"{BASE}/addresses/{INBOX}"


@pytest.fixture
def backend_with(monkeypatch):
    def _make(answer) -> tuple[MailsacBackend, FakeHTTP]:
        http = FakeHTTP({ADDRESS_URL: answer})
        monkeypatch.setattr("inbox.mailsac.requests.get", http.get)
        return MailsacBackend(base_url=BASE, inbox=INBOX, api_key="k_test"), http
    return _make


def test_owned_address_passes(backend_with):
    backend, http = backend_with(FakeResponse(json_data={"_id": INBOX, "owner": "acct"}))

    backend.verify_private()

    assert http.calls == [ADDRESS_URL]


@pytest.mark.parametrize("answer", [
    FakeResponse(json_data={"_id": INBOX}),  # public: no owner key
    FakeResponse(json_data={"_id": INBOX, "owner": ""}),
    FakeResponse(401, json_data={"message": "owned by another account"}),
    FakeResponse(404),
    FakeResponse(500),
    requests.ConnectionError("down"),
], ids=["public", "empty-owner", "401", "404", "500", "network"])
def test_unverifiable_or_public_address_is_refused(backend_with, answer):
    backend, _ = backend_with(answer)

    with pytest.raises(InboxGuardError):
        backend.verify_private()


def test_startup_guard_exits_non_zero_after_a_delay(backend_with, caplog):
    backend, _ = backend_with(FakeResponse(json_data={"_id": INBOX}))
    slept: list[float] = []

    with caplog.at_level(logging.ERROR, logger="listener"):
        with pytest.raises(SystemExit) as exc_info:
            main.startup_guard(backend, sleep=slept.append)

    assert exc_info.value.code == 1
    assert slept == [main.POLL_INTERVAL_S]
    assert any(r.getMessage().startswith("ERROR:") for r in caplog.records)


def test_startup_guard_passes_for_an_owned_address(backend_with):
    backend, _ = backend_with(FakeResponse(json_data={"_id": INBOX, "owner": "acct"}))

    main.startup_guard(backend, sleep=pytest.fail)
