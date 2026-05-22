"""Extrae numeros del cuerpo de un reply.

Acepta '1 3 7', '1, 3, 7', '#1 #3 #7', 'quiero los 2, 5 y 9'.

Estrategia (en orden):
1. Tomar SOLO el primer paragraph (separado por linea vacia) del reply.
   Esto es robusto a Gmail rompiendo "On ... wrote:" en 2 lineas (bug
   observado en prod) y a quote headers en cualquier idioma.
2. Dentro de ese paragraph, quitar lineas que empiezan con '>' (quoted).
3. Tambien quitar lineas que parecen header "Field: value".
4. Cap a 10 numeros.
"""

import re

# Detecta linea tipo "Field: ..." (Outlook style + headers en general).
_HEADER_LINE = re.compile(
    r"^(From|Sent|To|Subject|De|Enviado|Para|Asunto|On|El|Le|Am|Em):?\s",
    re.IGNORECASE,
)

# Separators ("---", "___", "===" de 3+ chars)
_SEPARATOR_LINE = re.compile(r"^[_\-=]{3,}\s*$")


def _strip_quoted(body: str) -> str:
    """Devuelve solo la parte nueva del reply.

    Heuristica robusta: el primer paragraph (antes del primer doble salto
    de linea) es el reply del usuario. Todo lo que viene despues es el
    quoted original que el email client agrego. Esto evita bugs cuando
    el quote header se rompe en multiples lineas (Gmail con line-wrap).
    """
    # Normalizar line endings
    body = body.replace("\r\n", "\n").replace("\r", "\n")

    # Tomar solo el primer paragraph no-vacio
    paragraphs = re.split(r"\n\s*\n", body)
    first = ""
    for p in paragraphs:
        if p.strip():
            first = p
            break

    # Dentro de ese paragraph, filtrar lineas quoted (>) o que parezcan headers
    keep = []
    for line in first.splitlines():
        stripped = line.lstrip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            continue
        if _HEADER_LINE.match(stripped):
            # Si la PRIMERA linea es un header, dropear todo (no hay reply)
            continue
        if _SEPARATOR_LINE.match(stripped):
            break
        keep.append(line)
    return "\n".join(keep)


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
