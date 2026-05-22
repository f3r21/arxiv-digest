#!/usr/bin/env bash
# Backup off-VM: sube el ultimo backup local a Google Drive via rclone.
# Asume que backup_local.sh ya corrio (encadenado en cron).
# Rotation: mantiene ultimos 30 dias en Drive (mas que local que son 7).
set -e

BACKUP_DIR="/var/backups/arxiv"
LATEST=$(ls -t "$BACKUP_DIR"/arxiv-*.tar.gz 2>/dev/null | head -1)

if [[ -z "$LATEST" ]]; then
    echo "[$(date -u +%H:%M:%S)] no local backup found, skip Drive sync"
    exit 0
fi

echo "[$(date -u +%H:%M:%S)] uploading $LATEST to gdrive:arxiv-backup/"
rclone copy "$LATEST" gdrive:arxiv-backup/ --quiet

# Prune Drive (mantener ultimos 30 dias)
rclone delete gdrive:arxiv-backup/ --min-age 30d --quiet 2>/dev/null || true

REMOTE_COUNT=$(rclone size gdrive:arxiv-backup/ 2>/dev/null | grep -oE '[0-9]+ objects' | head -1)
echo "[$(date -u +%H:%M:%S)] drive backup done. remote: $REMOTE_COUNT"
