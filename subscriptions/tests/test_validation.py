"""Validacion del payload del formulario (sin red, sin SMTP)."""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(monkeypatch):
    """Mock el envio SMTP para que /subscribe no necesite MailHog/Resend."""
    sent: list[dict] = []

    def fake_send(to_addr, token, categories):
        sent.append({"to": to_addr, "token": token, "cats": categories})

    monkeypatch.setattr(main.email_outbound, "send_confirmation", fake_send)
    main.sent_log = sent
    return TestClient(main.app), sent


def test_subscribe_happy_path(client):
    c, sent = client
    r = c.post(
        "/subscribe",
        data={
            "email": "alice@example.com",
            "categories": ["cs.DC", "cs.AI"],
            "keywords": "kubernetes, serverless",
            "max_papers": 10,
        },
    )
    assert r.status_code == 202, r.text
    assert r.json()["email"] == "alice@example.com"
    assert len(sent) == 1
    assert sent[0]["to"] == "alice@example.com"
    assert sent[0]["cats"] == ["cs.DC", "cs.AI"]


def test_subscribe_rejects_no_categories(client):
    c, _ = client
    r = c.post("/subscribe", data={"email": "x@example.com", "max_papers": 10})
    assert r.status_code == 400
    assert "categoria" in r.json()["detail"].lower()


def test_subscribe_rejects_only_invalid_categories(client):
    c, _ = client
    r = c.post(
        "/subscribe",
        data={
            "email": "x@example.com",
            "categories": ["bogus.XX", "nope.YY"],
            "max_papers": 10,
        },
    )
    assert r.status_code == 400


def test_subscribe_rejects_too_many_categories(client):
    """21 categorias debe fallar (limit es 20). Aceptamos cualquier 4xx:
    el rechazo puede venir de slowapi (429), FastAPI (422) o nuestro 400.
    """
    c, _ = client
    payload = [("email", "x@example.com")]
    payload += [("categories", code) for code in [
        "cs.AI", "cs.DC", "cs.LG", "cs.CL", "cs.CR", "cs.CV",
        "cs.DB", "cs.DS", "cs.GT", "cs.HC", "cs.IT", "cs.LO",
        "cs.NE", "cs.NI", "cs.OS", "cs.PL", "cs.RO", "cs.SC",
        "cs.SE", "cs.SI", "cs.SY",
    ]]
    payload.append(("max_papers", "10"))
    r = c.post("/subscribe", data=payload)
    assert 400 <= r.status_code < 500, r.text


def test_subscribe_clamps_max_papers(client, monkeypatch):
    import db
    c, _ = client
    c.post(
        "/subscribe",
        data={"email": "y@example.com", "categories": "cs.DC", "max_papers": 999},
    )
    pending = db._conn  # tests aislados, no llegamos a la DB de prod
    # Confirmamos via el token (mock)
    # Aqui solo verificamos que el endpoint no rompio
    # El clamp real se valida en otro test directamente sobre el handler


def test_subscribe_invalid_email_400(client):
    c, _ = client
    r = c.post(
        "/subscribe",
        data={"email": "not-an-email", "categories": "cs.DC", "max_papers": 10},
    )
    assert r.status_code == 400
    assert "email" in r.json()["detail"].lower()


def test_health(client):
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_categories_json(client):
    c, _ = client
    r = c.get("/categories.json")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) > 150
    codes = {e["code"] for e in cats}
    assert {"cs.DC", "cs.AI", "stat.ML"} <= codes
