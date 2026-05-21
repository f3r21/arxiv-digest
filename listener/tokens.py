"""Firma de URLs manage/unsubscribe desde el listener.

Mismo secret + salts que subscriptions/tokens.py para que los tokens
generados aca sean aceptados por los endpoints GET /manage y /unsubscribe.
"""

import os

from itsdangerous import URLSafeTimedSerializer

SECRET = os.environ.get("SUBSCRIPTIONS_SECRET", "").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def build_manage_url(subscriber_id: int) -> str:
    if not SECRET:
        return f"{PUBLIC_BASE_URL}/#manage-disabled"
    s = URLSafeTimedSerializer(SECRET, salt="manage")
    return f"{PUBLIC_BASE_URL}/manage?token={s.dumps(int(subscriber_id))}"


def build_unsubscribe_url(subscriber_id: int) -> str:
    if not SECRET:
        return f"{PUBLIC_BASE_URL}/#unsubscribe-disabled"
    s = URLSafeTimedSerializer(SECRET, salt="unsubscribe")
    return f"{PUBLIC_BASE_URL}/unsubscribe?token={s.dumps(int(subscriber_id))}"
