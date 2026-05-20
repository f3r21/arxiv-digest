"""Catalogo de categorias arXiv."""

import categories_catalog as cats


def test_catalog_loaded():
    catalog = cats.load()
    assert len(catalog) >= 150  # taxonomia oficial tiene ~155 categorias


def test_catalog_required_keys():
    for entry in cats.load():
        assert set(entry.keys()) == {"group", "code", "name"}
        assert entry["code"]
        assert entry["name"]


def test_validate_codes_filters_invalid():
    assert cats.validate_codes(["cs.DC", "cs.AI", "bogus.XX"]) == ["cs.DC", "cs.AI"]


def test_validate_codes_dedupes_and_strips():
    assert cats.validate_codes(["cs.DC", " cs.DC ", "cs.DC"]) == ["cs.DC"]


def test_validate_codes_preserves_order():
    assert cats.validate_codes(["stat.ML", "cs.AI", "math.OC"]) == [
        "stat.ML", "cs.AI", "math.OC"
    ]


def test_validate_codes_empty():
    assert cats.validate_codes([]) == []
    assert cats.validate_codes(["invalid"]) == []


def test_is_valid_code():
    assert cats.is_valid_code("cs.DC") is True
    assert cats.is_valid_code("gr-qc") is True   # categoria sin punto, pero valida
    assert cats.is_valid_code("nope.XX") is False


def test_grouped_returns_all_categories():
    grouped = cats.grouped()
    total = sum(len(items) for items in grouped.values())
    assert total == len(cats.load())
