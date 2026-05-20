"""Extrae numeros del cuerpo de un reply.

Acepta '1 3 7', '1, 3, 7', '#1 #3 #7', 'quiero los 2, 5 y 9'.
Ignora el texto citado que Gmail y otros clientes incluyen abajo del reply
(lineas que empiezan con '>', o todo lo que viene despues de 'On ... wrote:').
"""

import re

# 'On Tue, May 19, 2026 at 10:04 PM <...> wrote:' (Gmail, Apple Mail, etc.)
_QUOTE_HEADER = re.compile(r"^On .+ wrote:\s*$", re.MULTILINE)


def _strip_quoted(body: str) -> str:
    """Devuelve solo la parte nueva del reply, sin el texto citado."""
    cut = _QUOTE_HEADER.search(body)
    if cut:
        body = body[: cut.start()]
    return "\n".join(
        line for line in body.splitlines() if not line.lstrip().startswith(">")
    )


def parse_reply(body: str) -> list[int]:
    """Lista ordenada por orden de aparicion, deduplicada, cap a 10."""
    body = _strip_quoted(body)
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
