#!/bin/bash
# Backup pgvector memories table to S3
# Usage: ./backup_memories.sh

set -e

# Fix PATH for brew-installed tools (cron uses minimal PATH)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin"

# Source DATABASE_URL from memory-pre-action hook's .env (has real credentials with sslmode)
source /dev/stdin <<<"$(grep DATABASE_URL ~/.openclaw/hooks/memory-pre-action/.env)"

# Configuration
S3_BUCKET="roger-backups"
S3_PATH="memories"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/memories_backup_${TIMESTAMP}.sql"

echo "=== Backing up memories table ==="
echo "Timestamp: $TIMESTAMP"
echo "Database: $DB_NAME"

# Check for AWS CLI (optional - backup can still run without it)
S3_UPLOAD=false
if command -v aws &> /dev/null; then
    S3_UPLOAD=true
    echo "AWS CLI found - will upload to S3"
else
    echo "WARNING: AWS CLI not found - will create local backup only"
    echo "To enable S3 upload: brew install awscli"
fi

# Parse DATABASE_URL components
DB_HOST=$(echo $DATABASE_URL | sed 's/.*@\([^:]*\):.*//')
DB_PORT=$(echo $DATABASE_URL | sed 's/.*:\([0-9]*\)\/.*//')
DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*//')
DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\([^:]*\):.*//')
DB_PASS=$(echo $DATABASE_URL | sed 's/.*:\([^@]*\)@.*//')

echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"

# Export memories table to SQL
echo "Exporting memories table..."
export PGPASSWORD="$DB_PASS"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t memories -f "$BACKUP_FILE"

# Compress backup
echo "Compressing..."
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Upload to S3 (if awscli available)
if [ "$S3_UPLOAD" = true ]; then
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/${S3_PATH}/memories_${TIMESTAMP}.sql.gz"
    
    # List recent backups
    echo "=== Recent backups ==="
    aws s3 ls "s3://${S3_BUCKET}/${S3_PATH}/" | tail -5
else
    # Save locally if no awscli
    LOCAL_BACKUP_DIR="$HOME/.openclaw/backups"
    mkdir -p "$LOCAL_BACKUP_DIR"
    mv "$BACKUP_FILE" "$LOCAL_BACKUP_DIR/memories_${TIMESTAMP}.sql.gz"
    echo "Local backup saved to: $LOCAL_BACKUP_DIR/memories_${TIMESTAMP}.sql.gz"
fi

# Cleanup temp file
rm -f "$BACKUP_FILE" 2>/dev/null || true

echo "=== Backup complete: memories_${TIMESTAMP}.sql.gz ==="
