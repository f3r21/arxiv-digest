"""Firma de tokens de unsubscribe (debe usar el MISMO secret que subscriptions)."""

import os

from itsdangerous import URLSafeTimedSerializer

SECRET = os.environ.get("SUBSCRIPTIONS_SECRET", "").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def build_unsubscribe_url(subscriber_id: int) -> str:
    """URL HTTPS firmada para incluir en cada digest enviado.

    Si SUBSCRIPTIONS_SECRET no esta seteado devolvemos una URL placeholder
    (#unsubscribe-disabled) para que el digest no caiga en error catastrofico
    durante el desarrollo, pero loguear esto seria razonable.
    """
    if not SECRET:
        return f"{PUBLIC_BASE_URL}/#unsubscribe-disabled"
    serializer = URLSafeTimedSerializer(SECRET, salt="unsubscribe")
    token = serializer.dumps(int(subscriber_id))
    return f"{PUBLIC_BASE_URL}/unsubscribe?token={token}"
