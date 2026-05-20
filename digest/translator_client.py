"""Cliente HTTP del servicio translator. Degrada a ingles si falla."""

import logging
from typing import Any

import requests

logger = logging.getLogger("digest")

REQUEST_TIMEOUT_S = 5.0


def _translate_text(text: str, translator_url: str) -> str:
    """Llama al translator. Devuelve el texto original si algo sale mal."""
    if not text:
        return text
    try:
        resp = requests.post(
            f"{translator_url}/translate",
            json={"text": text, "source": "en", "target": "es"},
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json().get("translated", text) or text
    except (requests.RequestException, ValueError) as exc:
        logger.warning("PROFILE: translator fallo (%s), uso texto original", exc)
        return text


def translate_papers(
    papers: list[dict[str, Any]], translator_url: str
) -> list[dict[str, Any]]:
    """Traduce title+abstract de cada paper sin mutar el input."""
    translated: list[dict[str, Any]] = []
    for paper in papers:
        new_paper = dict(paper)
        new_paper["title"] = _translate_text(paper.get("title", ""), translator_url)
        new_paper["abstract"] = _translate_text(
            paper.get("abstract", ""), translator_url
        )
        translated.append(new_paper)
    logger.info("PROFILE: traducidos %d papers EN->ES", len(translated))
    return translated
