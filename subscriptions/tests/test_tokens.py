"""Tokens de confirmacion y unsubscribe."""

import time

import pytest

import tokens


def test_confirm_token_roundtrip():
    t = tokens.make_confirm_token("alice@example.com")
    assert tokens.read_confirm_token(t) == "alice@example.com"


def test_confirm_token_normalizes_case():
    t = tokens.make_confirm_token("ALICE@EXAMPLE.COM")
    assert tokens.read_confirm_token(t) == "alice@example.com"


def test_confirm_token_garbage_returns_none():
    assert tokens.read_confirm_token("not-a-token") is None
    assert tokens.read_confirm_token("") is None


def test_confirm_token_tampered_returns_none():
    t = tokens.make_confirm_token("alice@example.com")
    # Cambiar una letra en el medio invalida la firma
    bad = t[:10] + ("X" if t[10] != "X" else "Y") + t[11:]
    assert tokens.read_confirm_token(bad) is None


def test_hash_token_deterministic():
    t = tokens.make_confirm_token("a@b.com")
    assert tokens.hash_token(t) == tokens.hash_token(t)
    assert len(tokens.hash_token(t)) == 64  # sha256 hex


def test_hash_token_diff_inputs_diff_hashes():
    a = tokens.hash_token("aaa")
    b = tokens.hash_token("bbb")
    assert a != b


def test_unsubscribe_token_roundtrip():
    t = tokens.make_unsubscribe_token(42)
    assert tokens.read_unsubscribe_token(t) == 42


def test_unsubscribe_token_garbage_returns_none():
    assert tokens.read_unsubscribe_token("garbage") is None


def test_unsubscribe_does_not_accept_confirm_token():
    """Salts distintos: un token de confirm no debe ser valido como unsub."""
    confirm = tokens.make_confirm_token("a@b.com")
    assert tokens.read_unsubscribe_token(confirm) is None
