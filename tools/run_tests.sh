#!/usr/bin/env bash
# Corre pytest en los 3 servicios. Requiere docker compose up corriendo.
set -e

cd "$(dirname "$0")/.."

echo "=== subscriptions tests ==="
docker compose exec -T subscriptions sh -c "
  pip install --quiet pytest httpx 2>/dev/null
  cd /app && python -m pytest tests/ -q
"

echo
echo "=== listener tests ==="
docker compose exec -T listener sh -c "
  pip install --quiet pytest 2>/dev/null
  cd /app && python -m pytest tests/ -q
"

echo
echo "=== digest tests ==="
docker compose exec -T digest sh -c "
  pip install --quiet pytest 2>/dev/null
  cd /app && python -m pytest tests/ -q
"
