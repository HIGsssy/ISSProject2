#!/bin/bash
# ISS Portal - Backup Script
# Creates a complete backup of the database and configuration

set -eo pipefail  # Exit on error, fail on pipe errors

# Preflight: .env must exist to read database credentials
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Cannot read database credentials."
    echo "Copy .env.example to .env and configure it first."
    exit 1
fi

# Load environment variables (POSTGRES_USER, POSTGRES_DB, etc.)
set -a
# shellcheck source=.env
source .env
set +a

# Apply defaults in case variables are absent from .env
POSTGRES_USER="${POSTGRES_USER:-iss_user}"
POSTGRES_DB="${POSTGRES_DB:-iss_portal_db}"

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="db_backup_${TIMESTAMP}.sql.gz"
ENV_BACKUP_FILE=".env_${TIMESTAMP}"
RETENTION_DAYS=30  # Keep backups for 30 days

echo "========================================"
echo "ISS Portal - Backup"
echo "========================================"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker is not running."
    exit 1
fi

# Check if database container is running
if ! docker-compose ps | grep -q "db.*Up"; then
    echo "ERROR: Database container is not running."
    echo "Start it with: docker-compose up -d db"
    exit 1
fi

# Backup database
echo "Backing up database..."
docker-compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP_DIR/$DB_BACKUP_FILE"
if [ ! -s "$BACKUP_DIR/$DB_BACKUP_FILE" ]; then
    echo "ERROR: pg_dump produced an empty file. Removing and aborting."
    rm -f "$BACKUP_DIR/$DB_BACKUP_FILE"
    exit 1
fi
DB_SIZE=$(du -h "$BACKUP_DIR/$DB_BACKUP_FILE" | cut -f1)
echo "✓ Database backed up: $BACKUP_DIR/$DB_BACKUP_FILE ($DB_SIZE)"
echo ""

# Backup .env file
if [ -f .env ]; then
    echo "Backing up configuration..."
    cp .env "$BACKUP_DIR/$ENV_BACKUP_FILE"
    echo "✓ Configuration backed up: $BACKUP_DIR/$ENV_BACKUP_FILE"
    echo ""
fi

# Backup media files (if directory exists and not empty)
if [ -d media ] && [ "$(ls -A media)" ]; then
    echo "Backing up media files..."
    tar -czf "$BACKUP_DIR/media_${TIMESTAMP}.tar.gz" media/
    MEDIA_SIZE=$(du -h "$BACKUP_DIR/media_${TIMESTAMP}.tar.gz" | cut -f1)
    echo "✓ Media files backed up: $BACKUP_DIR/media_${TIMESTAMP}.tar.gz ($MEDIA_SIZE)"
    echo ""
fi

# Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/backup_${TIMESTAMP}.manifest" <<EOF
ISS Portal Backup Manifest
==========================
Backup Date: $(date)
Hostname: $(hostname)
Database Size: $DB_SIZE

Files in this backup:
- $DB_BACKUP_FILE (PostgreSQL database dump)
- $ENV_BACKUP_FILE (Environment configuration)
$([ -f "$BACKUP_DIR/media_${TIMESTAMP}.tar.gz" ] && echo "- media_${TIMESTAMP}.tar.gz (Uploaded media files)")

Restore Instructions:
1. Extract backup to new installation directory
2. Copy $ENV_BACKUP_FILE to .env
3. Start database: docker-compose up -d db
4. Restore database:
   gunzip -c $DB_BACKUP_FILE | docker-compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB
5. Restore media (if exists):
   tar -xzf media_${TIMESTAMP}.tar.gz
6. Start application: docker-compose up -d

IMPORTANT: Keep encryption key from .env file in a secure location!
EOF

echo "✓ Backup manifest created"
echo ""

# Clean up old backups
echo "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -name "db_backup_*.sql.gz" -delete 2>/dev/null || true
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -name ".env_*" -delete 2>/dev/null || true
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -name "media_*.tar.gz" -delete 2>/dev/null || true
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -name "backup_*.manifest" -delete 2>/dev/null || true
echo "✓ Old backups cleaned"
echo ""

# Summary
echo "========================================"
echo "Backup Complete!"
echo "========================================"
echo ""
echo "Backup location: $BACKUP_DIR/"
echo "Backup timestamp: $TIMESTAMP"
echo ""
echo "Files created:"
ls -lh "$BACKUP_DIR" | grep "$TIMESTAMP"
echo ""
echo "To restore this backup:"
echo "  ./restore.sh   (interactive)"
echo "  -- or manually:"
echo "  gunzip -c $BACKUP_DIR/$DB_BACKUP_FILE | docker-compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB"
echo ""
echo "IMPORTANT: Store backups in a secure, off-site location!"
echo "Consider copying to: cloud storage, external drive, or backup server"
echo ""
