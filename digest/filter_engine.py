"""Aplica reglas de filters.yml a una lista de papers."""

from typing import Any

import yaml


def load_filters(path: str) -> dict[str, Any]:
    """Carga el yaml de configuracion."""
    with open(path) as f:
        return yaml.safe_load(f)


def apply_filters(
    papers: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Retorna papers que matchean keywords O autores configurados.

    Anota cada paper retornado con un campo `match_reason` describiendo
    por que paso el filtro.
    """
    keywords = [k.lower() for k in filters.get("keywords") or []]
    target_authors = filters.get("authors") or []
    matched: list[dict[str, Any]] = []
    for p in papers:
        haystack = (p["title"] + " " + p["abstract"]).lower()
        kw_hits = [k for k in keywords if k in haystack]
        au_hits = [
            a for a in target_authors
            if any(a.lower() in author.lower() for author in p["authors"])
        ]
        if kw_hits or au_hits:
            reasons: list[str] = list(kw_hits)
            reasons.extend(f"autor:{a}" for a in au_hits)
            p["match_reason"] = ", ".join(reasons)
            matched.append(p)
    return matched
