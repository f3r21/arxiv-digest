#!/usr/bin/env bash
# Backup local: subscribers.db + archive/ tar.gz a /var/backups con rotation
# de 7 dias. Funciona sin Drive. Te salva de:
# - container corrupt
# - disk corruption (parcial)
# - rm -rf accidental
# NO te salva de: VM destruida, Oracle revoke free tier (necesitas Drive
# o equivalente off-VM para eso).
set -e
cd "$(dirname "$0")/.."

BACKUP_DIR="/var/backups/arxiv"
TS=$(date -u +%Y%m%d-%H%M)
ARCHIVE="$BACKUP_DIR/arxiv-$TS.tar.gz"

sudo mkdir -p "$BACKUP_DIR"
sudo chown ubuntu:ubuntu "$BACKUP_DIR"

# tar de subscribers.db + replies_processed.db + archive/ + public_preview
tar czf "$ARCHIVE" \
    -C data/ \
    subscribers.db replies_processed.db public_digest_preview.json archive/ \
    2>/dev/null || true

SIZE_KB=$(du -k "$ARCHIVE" | cut -f1)
echo "[$(date -u +%H:%M:%S)] backup: $ARCHIVE (${SIZE_KB}KB)"

# Rotation: mantener ultimos 7
ls -t "$BACKUP_DIR"/arxiv-*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
echo "[$(date -u +%H:%M:%S)] backup local done. mantienendo ultimos 7."
