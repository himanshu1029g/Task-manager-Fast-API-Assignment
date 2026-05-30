#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# backup.sh — PostgreSQL database backup with retention management
#
# SETUP (run once on EC2):
#   chmod +x scripts/backup.sh
#
# MANUAL RUN:
#   ./scripts/backup.sh
#
# AUTOMATED (cron) — daily at 2:00 AM UTC:
#   crontab -e
#   0 2 * * * /home/ubuntu/task-manager-api/scripts/backup.sh >> /home/ubuntu/backup.log 2>&1
#
# RESTORE:
#   gunzip -c /home/ubuntu/backups/db/taskdb_YYYYMMDD_HHMMSS.sql.gz | psql "$DATABASE_URL"
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
BACKUP_DIR="/home/ubuntu/backups/db"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/taskdb_${DATE}.sql.gz"
ENV_FILE="/home/ubuntu/task-manager-api/.env"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# ── Load DATABASE_URL from .env ───────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    # Safely extract only DATABASE_URL — avoids executing arbitrary content
    DATABASE_URL=$(grep -E '^DATABASE_URL=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    export DATABASE_URL
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "$LOG_PREFIX ❌ DATABASE_URL not set. Check $ENV_FILE. Aborting."
    exit 1
fi

# ── Create backup directory ───────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

echo "$LOG_PREFIX Starting backup → $BACKUP_FILE"

# ── Perform backup ────────────────────────────────────────────────────────────
if pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"; then
    SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "$LOG_PREFIX ✅ Backup complete — size: $SIZE"
else
    echo "$LOG_PREFIX ❌ Backup failed — removing partial file"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# ── Retention — remove backups older than N days ──────────────────────────────
echo "$LOG_PREFIX Applying retention policy: keep last $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "taskdb_*.sql.gz" -mtime "+$RETENTION_DAYS" -delete
REMAINING=$(find "$BACKUP_DIR" -name "taskdb_*.sql.gz" | wc -l)
echo "$LOG_PREFIX $REMAINING backup(s) retained in $BACKUP_DIR"

# ── Summary ───────────────────────────────────────────────────────────────────
echo "$LOG_PREFIX Backup run complete."
