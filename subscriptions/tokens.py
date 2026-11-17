"""Tokens firmados con itsdangerous (confirm 48h, unsubscribe sin TTL)."""

import hashlib
import hmac
import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET = os.environ.get("SUBSCRIPTIONS_SECRET", "").strip()
if not SECRET:
    raise RuntimeError("SUBSCRIPTIONS_SECRET no esta seteado")

CONFIRM_TTL_HOURS = int(os.environ.get("CONFIRM_TTL_HOURS", "48"))

_confirm = URLSafeTimedSerializer(SECRET, salt="confirm")
_unsub = URLSafeTimedSerializer(SECRET, salt="unsubscribe")
_manage = URLSafeTimedSerializer(SECRET, salt="manage")
# Local to this service: only the confirmation email carries it and only
# /not-me reads it. Not shared with digest/listener.
_not_me = URLSafeTimedSerializer(SECRET, salt="not-me")
NOT_ME_TTL_DAYS = 30


def make_not_me_token(email: str) -> str:
    return _not_me.dumps(email.strip().lower())


def read_not_me_token(token: str) -> str | None:
    """Email signed into a "this wasn't me" link, or None if invalid/expired."""
    try:
        return str(_not_me.loads(token, max_age=NOT_ME_TTL_DAYS * 86400))
    except BadSignature:  # SignatureExpired is a subclass
        return None


def make_confirm_token(email: str) -> str:
    return _confirm.dumps(email.strip().lower())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def email_hmac(email: str) -> str:
    """HMAC-SHA256(secret, normalized email): a stable key that is not the address."""
    normalized = email.strip().lower().encode("utf-8")
    return hmac.new(SECRET.encode("utf-8"), normalized, hashlib.sha256).hexdigest()


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


def make_manage_token(subscriber_id: int) -> str:
    return _manage.dumps(int(subscriber_id))


def read_manage_token(token: str) -> int | None:
    try:
        return int(_manage.loads(token))
    except (BadSignature, ValueError, TypeError):
        return None
