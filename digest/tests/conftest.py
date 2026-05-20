import os
import sys
from pathlib import Path

os.environ.setdefault("SUBSCRIPTIONS_SECRET", "0" * 64)
os.environ.setdefault("PUBLIC_BASE_URL", "https://localhost")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
