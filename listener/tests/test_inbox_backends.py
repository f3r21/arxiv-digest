"""Inbox backends against a mocked HTTP layer: call order (Mailsac quota) and error propagation."""

import logging

import pytest
import requests

import db
import main
from inbox.mailhog import MailhogBackend
from inbox.mailsac import MailsacBackend
from tests.conftest import make_paper

BASE = "https://mailsac.test/api"
INBOX = "replies@mailsac.com"


class FakeResponse:
    def __init__(self, status: int = 200, json_data=None, text: str = "") -> None:
        self.status_code = status
        self._json = json_data
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


class FakeHTTP:
    """Records GET URLs and answers from a URL -> response (or exception) map."""

    def __init__(self, routes: dict) -> None:
        self.routes = routes
        self.calls: list[str] = []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        answer = self.routes.get(url)
        if answer is None:
            return FakeResponse(404)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def delete(self, url, headers=None, timeout=None):
        self.calls.append("DELETE " + url)
        return FakeResponse(204)


def _mailsac_listing(*ids: str) -> FakeResponse:
    return FakeResponse(json_data=[
        {"_id": i, "subject": "Re: The Daily Abstract No. 7",
         "from": [{"address": "ana@example.com"}], "to": [{"address": INBOX}]}
        for i in ids
    ])


@pytest.fixture
def mailsac(monkeypatch):
    def _make(routes: dict) -> tuple[MailsacBackend, FakeHTTP]:
        http = FakeHTTP(routes)
        monkeypatch.setattr("inbox.mailsac.requests.get", http.get)
        monkeypatch.setattr("inbox.mailsac.requests.delete", http.delete)
        return MailsacBackend(base_url=BASE, inbox=INBOX, api_key="k_test"), http
    return _make


def test_mailsac_skips_body_fetch_for_processed_messages(
    mailsac, smtp, add_subscriber
):
    add_subscriber("ana@example.com", [make_paper("2411.00001", "One")])
    db.mark_processed("old")
    backend, http = mailsac({
        f"{BASE}/addresses/{INBOX}/messages": _mailsac_listing("old", "new"),
        f"{BASE}/text/{INBOX}/new": FakeResponse(text="1"),
    })

    main.poll_once(backend)

    gets = [c for c in http.calls if not c.startswith("DELETE")]
    assert gets == [
        f"{BASE}/addresses/{INBOX}/messages",
        f"{BASE}/text/{INBOX}/new",
    ]
    assert len(smtp.outbox) == 1


def test_mailsac_skips_body_fetch_for_unknown_senders(mailsac, smtp, subscribers_db):
    backend, http = mailsac({
        f"{BASE}/addresses/{INBOX}/messages": _mailsac_listing("m1"),
    })

    main.poll_once(backend)

    assert not any("/text/" in c for c in http.calls)
    assert db.is_processed("m1")


def test_mailsac_listing_error_propagates(mailsac):
    backend, _ = mailsac({
        f"{BASE}/addresses/{INBOX}/messages": requests.ConnectionError("down"),
    })

    with pytest.raises(requests.RequestException):
        main.poll_once(backend)


def test_mailsac_listing_http_error_propagates(mailsac):
    backend, _ = mailsac({
        f"{BASE}/addresses/{INBOX}/messages": FakeResponse(500),
    })

    with pytest.raises(requests.RequestException):
        main.poll_once(backend)


def test_mailsac_body_error_leaves_that_message_for_next_poll(
    mailsac, smtp, add_subscriber, caplog
):
    add_subscriber("ana@example.com", [make_paper("2411.00001", "One")])
    backend, _ = mailsac({
        f"{BASE}/addresses/{INBOX}/messages": _mailsac_listing("bad", "good"),
        f"{BASE}/text/{INBOX}/bad": FakeResponse(503),
        f"{BASE}/text/{INBOX}/good": FakeResponse(text="1"),
    })

    with caplog.at_level(logging.ERROR, logger="listener"):
        main.poll_once(backend)

    assert not db.is_processed("bad")
    assert db.is_processed("good")
    assert any("bad" in r.getMessage() for r in caplog.records if r.levelno == logging.ERROR)


def test_mailhog_listing_error_propagates(monkeypatch):
    def boom(*a, **kw):
        raise requests.ConnectionError("mailhog down")

    monkeypatch.setattr("inbox.mailhog.requests.get", boom)
    backend = MailhogBackend(
        list_url="http://mh/api/v2/messages",
        delete_url="http://mh/api/v1/messages",
        self_addr="digest@local",
    )

    with pytest.raises(requests.RequestException):
        backend.list_messages()


def test_mailhog_fetches_body_by_id(monkeypatch):
    http = FakeHTTP({
        "http://mh/api/v1/messages/abc": FakeResponse(
            json_data={"ID": "abc", "Content": {"Body": "1 3"}}
        ),
    })
    monkeypatch.setattr("inbox.mailhog.requests.get", http.get)
    backend = MailhogBackend(
        list_url="http://mh/api/v2/messages",
        delete_url="http://mh/api/v1/messages",
        self_addr="digest@local",
    )

    assert backend.fetch_body("abc") == "1 3"
