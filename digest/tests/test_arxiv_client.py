"""Unit tests para arxiv_client.

Regressions:
- Parens en la query → arxiv devuelve 0 papers (bug observado en prod).
- Sin retry → un blip transitorio de 429/503 = no email ese dia (22 May 2026).
"""

from types import SimpleNamespace
from unittest.mock import patch

from arxiv_client import _build_search_query, _fetch_with_retry


def test_single_category_no_parens() -> None:
    assert _build_search_query(["cs.LG"]) == "cat:cs.LG"


def test_multi_category_no_parens() -> None:
    # CRITICAL: sin parens. Con parens arxiv devuelve 0 papers.
    got = _build_search_query(["cs.LG", "cs.AI"])
    assert got == "cat:cs.LG+OR+cat:cs.AI"
    assert "(" not in got
    assert ")" not in got


def test_three_category_format() -> None:
    got = _build_search_query(["cs.LG", "cs.AI", "cs.CL"])
    assert got == "cat:cs.LG+OR+cat:cs.AI+OR+cat:cs.CL"


def test_order_preserved() -> None:
    got = _build_search_query(["stat.ML", "cs.LG", "math.OC"])
    assert got == "cat:stat.ML+OR+cat:cs.LG+OR+cat:math.OC"


def test_fetch_with_retry_returns_immediately_on_valid_feed() -> None:
    """No bozo, hay entries → un solo call a feedparser."""
    good = SimpleNamespace(bozo=False, entries=[SimpleNamespace(id="x")])
    with patch("arxiv_client.feedparser.parse", return_value=good) as m:
        feed = _fetch_with_retry("http://test")
        assert feed is good
        assert m.call_count == 1


def test_fetch_with_retry_returns_immediately_on_empty_valid_feed() -> None:
    """Vacio pero valido (no bozo) → no reintento (puede ser legitimo)."""
    empty = SimpleNamespace(bozo=False, entries=[])
    with patch("arxiv_client.feedparser.parse", return_value=empty) as m:
        feed = _fetch_with_retry("http://test")
        assert feed is empty
        assert m.call_count == 1


def test_fetch_with_retry_retries_on_bozo_then_succeeds() -> None:
    """Primer intento bozo (rate limit), segundo OK → 2 calls, retorna OK."""
    bad = SimpleNamespace(bozo=True, entries=[], bozo_exception="syntax error")
    good = SimpleNamespace(bozo=False, entries=[SimpleNamespace(id="x")])
    with patch("arxiv_client.feedparser.parse", side_effect=[bad, good]) as m:
        with patch("arxiv_client.time.sleep") as sleep_m:
            feed = _fetch_with_retry("http://test")
            assert feed is good
            assert m.call_count == 2
            sleep_m.assert_called_once_with(15)


def test_fetch_with_retry_exhausts_all_retries() -> None:
    """Si todos los intentos son bozo, retorna el ultimo feed (vacio)."""
    bad = SimpleNamespace(bozo=True, entries=[], bozo_exception="syntax error")
    with patch("arxiv_client.feedparser.parse", return_value=bad) as m:
        with patch("arxiv_client.time.sleep"):
            feed = _fetch_with_retry("http://test")
            assert feed is bad
            assert m.call_count == 4  # 1 inicial + 3 retries
