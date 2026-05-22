"""Unit tests para arxiv_client._build_search_query.

Regression: con parens en la query, arxiv devuelve 0 papers (bug observado
en prod). Sin parens funciona.
"""

from arxiv_client import _build_search_query


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
