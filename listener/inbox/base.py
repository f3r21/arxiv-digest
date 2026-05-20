"""Contrato comun para los backends de inbox.

Cada backend devuelve mensajes normalizados como dicts con las claves:
    id        str  - identificador unico del mensaje
    subject   str  - asunto
    body      str  - cuerpo en texto plano
    sender    str  - email del remitente
    recipient str  - email del destinatario (la propia inbox)
"""

from typing import Protocol


class InboxBackend(Protocol):
    """Protocol structural - cualquier objeto con estos metodos califica."""

    def fetch_messages(self) -> list[dict]:
        """Devuelve todos los mensajes visibles. Lista vacia ante errores."""
        ...

    def delete_message(self, msg_id: str) -> None:
        """Best-effort: elimina el mensaje del backend. No levanta excepciones."""
        ...
