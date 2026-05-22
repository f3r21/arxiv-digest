"""Extrae numeros del cuerpo de un reply.

Acepta '1 3 7', '1, 3, 7', '#1 #3 #7', 'quiero los 2, 5 y 9'.
Ignora el texto citado que Gmail/Apple Mail/Outlook incluyen debajo del reply:
- lineas que empiezan con '>'
- 'On ... wrote:' (Gmail/Apple ingles)
- 'El ... escribio:' (Gmail espanol — con o sin acento)
- 'Le ... a ecrit:' (Gmail frances)
- 'Am ... schrieb:' (Gmail aleman)
- 'Em ... escreveu:' (Gmail portugues)
- separators ('---', '___')
- 'From:' / 'Sent:' / 'De:' / 'Enviado:' headers (Outlook style)

Safety net: si no se detecta quote header, solo lee las primeras 5 lineas
no-vacias del body (los usuarios responden con los numeros arriba).
"""

import re

# Quote headers en multiples idiomas. Linea entera.
_QUOTE_HEADER = re.compile(
    r"^("
    r"On .+ wrote:|"                      # Gmail/Apple English
    r"El .+ escribi[oó]:|"                # Gmail Spanish (con o sin tilde)
    r"Le .+ a [eé]crit ?:|"               # Gmail French
    r"Am .+ schrieb .+:|"                 # Gmail German
    r"Em .+ escreveu:|"                   # Gmail Portuguese
    r"_{3,}|-{3,}|={3,}"                  # separators (___, ---, ===)
    r")\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Outlook headers (mas dificil porque pueden romperse en multiples lineas)
_OUTLOOK_HEADERS = re.compile(
    r"^(From|Sent|To|Subject|De|Enviado|Para|Asunto):\s+.+$",
    re.MULTILINE | re.IGNORECASE,
)

_MAX_LINES_NO_QUOTE = 5  # safety net: si no hay quote header, solo primeras N lineas


def _strip_quoted(body: str) -> str:
    """Devuelve solo la parte nueva del reply, sin el texto citado."""
    # 1) Cortar en el primer quote header detectado
    cut = _QUOTE_HEADER.search(body)
    if cut:
        body = body[: cut.start()]
    else:
        # 2) Cortar en el primer Outlook-style header
        cut = _OUTLOOK_HEADERS.search(body)
        if cut:
            body = body[: cut.start()]
        else:
            # 3) Safety net: si no detectamos quote, solo primeras 5 lineas no-vacias
            non_empty = [l for l in body.splitlines() if l.strip()]
            body = "\n".join(non_empty[:_MAX_LINES_NO_QUOTE])

    # 4) Quitar lineas que empiezan con '>'
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
