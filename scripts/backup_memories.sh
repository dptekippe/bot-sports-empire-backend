#!/bin/bash
# Backup pgvector memories table to S3
# Usage: ./backup_memories.sh

set -e

# Configuration
DATABASE_URL="postgresql://dynastydroid_user:BKJZCv57P3sYpi5RGL3ciU9CylXsFRWv@dpg-d6g7g3pdrdic73d9jdrg-a.oregon-postgres.render.com/dynastydroid"
S3_BUCKET="roger-backups"
S3_PATH="memories"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/memories_backup_${TIMESTAMP}.sql"

echo "=== Backing up memories table ==="

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: aws CLI not found"
    exit 1
fi

# Export memories table to SQL
echo "Exporting memories table..."
PGPASSWORD=$(echo $DATABASE_URL | sed 's/.*:\([^@]*\)@.*/\1/') \
DB_HOST=$(echo $DATABASE_URL | sed 's/.*@\([^:]*\):.*/\1/') \
DB_PORT=$(echo $DATABASE_URL | sed 's/.*:\([0-9]*\)\/.*/\1/') \
DB_NAME=$(echo $DATABASE_URL | sed 's/.*\/\([^?]*\).*/\1/') \
DB_USER=$(echo $DATABASE_URL | sed 's/.*:\/\([^:]*\):.*/\1/') \
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t memories -f "$BACKUP_FILE"

# Compress backup
echo "Compressing..."
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/${S3_PATH}/memories_${TIMESTAMP}.sql.gz"

# Cleanup
rm -f "$BACKUP_FILE"

# List recent backups
echo "=== Recent backups ==="
aws s3 ls "s3://${S3_BUCKET}/${S3_PATH}/" | tail -5

echo "=== Backup complete: memories_${TIMESTAMP}.sql.gz ==="
