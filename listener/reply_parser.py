"""Extrae numeros del cuerpo de un reply.

Acepta '1 3 7', '1, 3, 7', '#1 #3 #7', 'quiero los 2, 5 y 9'.
"""

import re


def parse_reply(body: str) -> list[int]:
    """Lista ordenada por orden de aparicion, deduplicada, cap a 10."""
    tokens = re.findall(r"\b(\d{1,2})\b", body)
    seen: set[int] = set()
    out: list[int] = []
    for t in tokens:
        n = int(t)
        if 1 <= n <= 99 and n not in seen:
            seen.add(n)
            out.append(n)
        if len(out) >= 10:
            break
    return out
