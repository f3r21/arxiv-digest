"""Refresca subscriptions/arxiv_categories.json desde arxiv.org/category_taxonomy.

Uso: python tools/build_arxiv_categories.py

Scrapea la pagina oficial (HTML) y rearma el JSON. Pensado para correrse
trimestralmente; el JSON se commitea al repo. Si la pagina cambia de
estructura, los selectores aqui deben actualizarse.
"""

import json
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

TAXONOMY_URL = "https://arxiv.org/category_taxonomy"
OUTPUT = Path(__file__).parent.parent / "subscriptions" / "arxiv_categories.json"


def fetch_taxonomy() -> list[dict[str, str]]:
    resp = requests.get(TAXONOMY_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    out: list[dict[str, str]] = []
    current_group = ""
    for el in soup.select("h2.accordion-head, h4"):
        if el.name == "h2":
            current_group = el.get_text(strip=True)
            continue
        text = el.get_text(strip=True)
        if " (" not in text or not text.endswith(")"):
            continue
        code, _, rest = text.partition(" (")
        name = rest.rstrip(")").strip()
        code = code.strip()
        if not code or not name:
            continue
        out.append({"group": current_group, "code": code, "name": name})
    return out


def main() -> None:
    cats = fetch_taxonomy()
    if not cats:
        print("ERROR: no categories parsed; check selectors against current HTML",
              file=sys.stderr)
        sys.exit(1)
    OUTPUT.write_text(json.dumps(cats, ensure_ascii=False, indent=2) + "\n")
    print(f"OK: {len(cats)} categories -> {OUTPUT}")


if __name__ == "__main__":
    main()
