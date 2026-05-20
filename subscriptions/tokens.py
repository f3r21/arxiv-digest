"""Tokens firmados con itsdangerous (confirm 48h, unsubscribe sin TTL)."""

import hashlib
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET = os.environ.get("SUBSCRIPTIONS_SECRET", "").strip()
if not SECRET:
    raise RuntimeError("SUBSCRIPTIONS_SECRET no esta seteado")

CONFIRM_TTL_HOURS = int(os.environ.get("CONFIRM_TTL_HOURS", "48"))

_confirm = URLSafeTimedSerializer(SECRET, salt="confirm")
_unsub = URLSafeTimedSerializer(SECRET, salt="unsubscribe")


def make_confirm_token(email: str) -> str:
    return _confirm.dumps(email.strip().lower())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def read_confirm_token(token: str) -> str | None:
    """Devuelve el email firmado, o None si invalido/expirado."""
    try:
        return str(_confirm.loads(token, max_age=CONFIRM_TTL_HOURS * 3600))
    except SignatureExpired:
        return None
    except BadSignature:
        return None


def make_unsubscribe_token(subscriber_id: int) -> str:
    return _unsub.dumps(int(subscriber_id))


def read_unsubscribe_token(token: str) -> int | None:
    try:
        return int(_unsub.loads(token))
    except (BadSignature, ValueError, TypeError):
        return None
