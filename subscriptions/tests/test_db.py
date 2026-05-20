"""Operaciones del repo de suscriptores."""

import pytest

import db


def test_insert_and_lookup():
    sub_id = db.insert_subscriber(
        email="Alice@Example.com",
        categories=["cs.DC", "cs.AI"],
        keywords=["kubernetes"],
        max_papers=10,
        source="web",
    )
    assert sub_id > 0
    sub = db.find_by_email("alice@example.com")
    assert sub is not None
    assert sub.id == sub_id
    assert sub.email == "alice@example.com"
    assert sub.categories == ["cs.DC", "cs.AI"]
    assert sub.keywords == ["kubernetes"]
    assert sub.max_papers == 10


def test_find_by_email_case_insensitive():
    db.insert_subscriber("a@b.com", ["cs.DC"], [], 15)
    assert db.find_by_email("a@b.com") is not None
    assert db.find_by_email("A@B.COM") is not None
    assert db.find_by_email("  a@b.com  ") is not None


def test_insert_same_email_upserts():
    sub_id_1 = db.insert_subscriber("x@y.com", ["cs.DC"], [], 5)
    sub_id_2 = db.insert_subscriber("x@y.com", ["cs.AI"], ["nlp"], 20)
    assert sub_id_1 == sub_id_2
    sub = db.find_by_email("x@y.com")
    assert sub.categories == ["cs.AI"]
    assert sub.keywords == ["nlp"]
    assert sub.max_papers == 20


def test_soft_delete_excludes_from_active_list():
    sub_id = db.insert_subscriber("a@b.com", ["cs.DC"], [], 15)
    assert len(db.list_active()) == 1
    db.soft_delete_subscriber(sub_id)
    assert db.list_active() == []
    # find_by_email tambien lo filtra
    assert db.find_by_email("a@b.com") is None


def test_resubscribe_after_unsubscribe_reactivates():
    sub_id = db.insert_subscriber("a@b.com", ["cs.DC"], [], 15)
    db.soft_delete_subscriber(sub_id)
    assert db.list_active() == []
    sub_id_2 = db.insert_subscriber("a@b.com", ["cs.AI"], [], 10)
    assert sub_id_2 == sub_id  # mismo registro
    assert len(db.list_active()) == 1


def test_pending_confirmation_roundtrip():
    db.store_pending("hash1", "a@b.com", {"categories": ["cs.DC"]}, "1.2.3.4")
    popped = db.pop_pending("hash1")
    assert popped is not None
    assert popped["email"] == "a@b.com"
    assert popped["payload"]["categories"] == ["cs.DC"]
    # Una vez popped, ya no existe
    assert db.pop_pending("hash1") is None


def test_pop_missing_pending_returns_none():
    assert db.pop_pending("nope") is None


def test_log_attempts():
    db.log_subscribe_attempt("1.2.3.4", "spam@x.com")
    db.log_subscribe_attempt("5.6.7.8", None)
    # No raises = ok
