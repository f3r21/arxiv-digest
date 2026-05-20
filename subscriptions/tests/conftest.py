"""Fixtures comunes: setup de SUBSCRIPTIONS_SECRET y DB temporal."""

import os
import sys
from pathlib import Path

# Aseguramos que el secret existe antes que se importe `tokens`
os.environ.setdefault(
    "SUBSCRIPTIONS_SECRET",
    "0" * 64,
)
os.environ.setdefault("CONFIRM_TTL_HOURS", "48")
# Rate-limit alto para que los tests no se choquen entre si dentro de la
# misma "hora" del limiter en memoria.
os.environ.setdefault("SUBSCRIBE_RATE_PER_HOUR", "10000")

# Permitir imports de los modulos del servicio
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Cada test corre con un subscribers.db nuevo en tmp_path."""
    import db as subs_db
    monkeypatch.setattr(subs_db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(subs_db, "DB_PATH", tmp_path / "subscribers.db")
    subs_db.init_db()
    yield tmp_path
