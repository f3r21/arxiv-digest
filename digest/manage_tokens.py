"""Firma del token 'manage' que va en el footer del digest.

Mismo secret + salt 'manage' que subscriptions/tokens.py, para que el link
desde el email digest sea aceptado por el endpoint /manage del servicio
subscriptions.
"""

import os

from itsdangerous import URLSafeTimedSerializer

SECRET = os.environ.get("SUBSCRIPTIONS_SECRET", "").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def build_manage_url(subscriber_id: int) -> str:
    if not SECRET:
        return f"{PUBLIC_BASE_URL}/#manage-disabled"
    serializer = URLSafeTimedSerializer(SECRET, salt="manage")
    token = serializer.dumps(int(subscriber_id))
    return f"{PUBLIC_BASE_URL}/manage?token={token}"
