"""Carga arxiv_categories.json y valida codigos contra el whitelist."""

import json
from collections import OrderedDict
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "arxiv_categories.json"

_catalog: list[dict[str, str]] = []
_codes: set[str] = set()


def load() -> list[dict[str, str]]:
    global _catalog, _codes
    if _catalog:
        return _catalog
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    _catalog = [
        {"group": str(e["group"]), "code": str(e["code"]), "name": str(e["name"])}
        for e in raw
    ]
    _codes = {e["code"] for e in _catalog}
    return _catalog


def grouped() -> "OrderedDict[str, list[dict[str, str]]]":
    """Devuelve dict ordenado: group -> [entries] (orden de aparicion)."""
    out: "OrderedDict[str, list[dict[str, str]]]" = OrderedDict()
    for e in load():
        out.setdefault(e["group"], []).append(e)
    return out


def is_valid_code(code: str) -> bool:
    if not _codes:
        load()
    return code in _codes


def validate_codes(codes: list[str]) -> list[str]:
    """Devuelve solo codigos validos, en orden, sin duplicados."""
    if not _codes:
        load()
    seen: set[str] = set()
    out: list[str] = []
    for c in codes:
        c_clean = c.strip()
        if c_clean in _codes and c_clean not in seen:
            seen.add(c_clean)
            out.append(c_clean)
    return out
