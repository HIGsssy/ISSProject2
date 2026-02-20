#!/bin/bash
# ISS Portal - Interactive Restore Script
# Restores database, .env, and/or media from a backup set in backups/

set -eo pipefail

BACKUP_DIR="backups"

echo "========================================"
echo "ISS Portal - Restore"
echo "========================================"
echo ""

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
if ! docker info &> /dev/null; then
    echo "ERROR: Docker is not running."
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory '$BACKUP_DIR' not found."
    exit 1
fi

# Load .env for credentials (used when restoring DB)
if [ -f .env ]; then
    set -a
    # shellcheck source=.env
    source .env
    set +a
fi
POSTGRES_USER="${POSTGRES_USER:-iss_user}"
POSTGRES_DB="${POSTGRES_DB:-iss_portal_db}"

# ---------------------------------------------------------------------------
# Discover available backup timestamps
# ---------------------------------------------------------------------------
mapfile -t TIMESTAMPS < <(
    ls "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null \
    | sed 's|.*db_backup_||; s|\.sql\.gz||' \
    | sort -r
)

if [ ${#TIMESTAMPS[@]} -eq 0 ]; then
    echo "ERROR: No database backup files found in $BACKUP_DIR/."
    exit 1
fi

echo "Available backups (most recent first):"
echo ""
for i in "${!TIMESTAMPS[@]}"; do
    TS="${TIMESTAMPS[$i]}"
    DB_FILE="$BACKUP_DIR/db_backup_${TS}.sql.gz"
    DB_SIZE=$(du -h "$DB_FILE" 2>/dev/null | cut -f1 || echo "?")
    ENV_MARKER=""
    MEDIA_MARKER=""
    [ -f "$BACKUP_DIR/.env_${TS}" ]          && ENV_MARKER="  [.env]"
    [ -f "$BACKUP_DIR/media_${TS}.tar.gz" ]  && MEDIA_MARKER="  [media]"
    printf "  %2d) %s  (%s DB%s%s)\n" "$((i+1))" "$TS" "$DB_SIZE" "$ENV_MARKER" "$MEDIA_MARKER"
done
echo ""

# ---------------------------------------------------------------------------
# Select backup
# ---------------------------------------------------------------------------
read -rp "Enter backup number to restore (or q to quit): " SELECTION
[[ "$SELECTION" == "q" || "$SELECTION" == "Q" ]] && echo "Aborted." && exit 0

if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -gt "${#TIMESTAMPS[@]}" ]; then
    echo "ERROR: Invalid selection."
    exit 1
fi

TIMESTAMP="${TIMESTAMPS[$((SELECTION-1))]}"
DB_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"
ENV_FILE="$BACKUP_DIR/.env_${TIMESTAMP}"
MEDIA_FILE="$BACKUP_DIR/media_${TIMESTAMP}.tar.gz"

echo ""
echo "Selected backup: $TIMESTAMP"
echo ""

# ---------------------------------------------------------------------------
# Choose what to restore
# ---------------------------------------------------------------------------
RESTORE_DB=false
RESTORE_ENV=false
RESTORE_MEDIA=false

read -rp "Restore DATABASE from $DB_FILE? [y/N]: " ANS
[[ "$ANS" =~ ^[Yy]$ ]] && RESTORE_DB=true

if [ -f "$ENV_FILE" ]; then
    read -rp "Restore .env file from $ENV_FILE? [y/N]: " ANS
    [[ "$ANS" =~ ^[Yy]$ ]] && RESTORE_ENV=true
fi

if [ -f "$MEDIA_FILE" ]; then
    read -rp "Restore media files from $MEDIA_FILE? [y/N]: " ANS
    [[ "$ANS" =~ ^[Yy]$ ]] && RESTORE_MEDIA=true
fi

if ! $RESTORE_DB && ! $RESTORE_ENV && ! $RESTORE_MEDIA; then
    echo ""
    echo "Nothing selected to restore. Aborted."
    exit 0
fi

echo ""
echo "⚠  WARNING: This will OVERWRITE the selected data with the backup contents."
read -rp "Type 'yes' to confirm: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# ---------------------------------------------------------------------------
# Restore .env first (if selected) so DB credentials are correct
# ---------------------------------------------------------------------------
if $RESTORE_ENV; then
    echo ""
    echo "Restoring .env ..."
    cp "$ENV_FILE" .env
    echo "✓ .env restored from $ENV_FILE"
    # Reload credentials from the restored .env
    set -a
    source .env
    set +a
    POSTGRES_USER="${POSTGRES_USER:-iss_user}"
    POSTGRES_DB="${POSTGRES_DB:-iss_portal_db}"
    echo "  NOTE: You must run 'docker-compose down && docker-compose up -d' after this restore"
    echo "        for all services to pick up the new .env values."
fi

# ---------------------------------------------------------------------------
# Restore database
# ---------------------------------------------------------------------------
if $RESTORE_DB; then
    echo ""
    echo "Restoring database ..."

    # Ensure DB container is up
    if ! docker-compose ps | grep -q "db.*Up\|db.*running"; then
        echo "  Starting database container ..."
        docker-compose up -d db
        sleep 5
    fi

    # Stop web so there are no active connections
    if docker-compose ps | grep -q "web.*Up\|web.*running"; then
        echo "  Stopping web container to release DB connections ..."
        docker-compose stop web
        WEB_WAS_RUNNING=true
    fi

    # Drop all connections, drop and recreate the database
    echo "  Terminating existing DB connections ..."
    docker-compose exec -T db psql -U "$POSTGRES_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$POSTGRES_DB' AND pid <> pg_backend_pid();" \
        > /dev/null 2>&1 || true

    echo "  Dropping and recreating database '$POSTGRES_DB' ..."
    docker-compose exec -T db psql -U "$POSTGRES_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";" > /dev/null
    docker-compose exec -T db psql -U "$POSTGRES_USER" -d postgres \
        -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";" > /dev/null

    echo "  Loading backup data ..."
    gunzip -c "$DB_FILE" | docker-compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null

    echo "✓ Database restored from $DB_FILE"

    # Restart web if it was running
    if [ "${WEB_WAS_RUNNING:-false}" = "true" ]; then
        echo "  Restarting web container ..."
        docker-compose start web

        echo "  Running database migrations as a sanity check ..."
        sleep 3
        docker-compose exec web python manage.py migrate --run-syncdb 2>&1 \
            | grep -E "Apply|No migrations|OK|Running" || true
        echo "✓ Web container restarted and migrations verified"
    fi
fi

# ---------------------------------------------------------------------------
# Restore media files
# ---------------------------------------------------------------------------
if $RESTORE_MEDIA; then
    echo ""
    echo "Restoring media files ..."
    tar -xzf "$MEDIA_FILE"
    echo "✓ Media files restored from $MEDIA_FILE"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "========================================"
echo "Restore Complete!"
echo "========================================"
echo ""
$RESTORE_DB    && echo "  ✓ Database restored (timestamp: $TIMESTAMP)"
$RESTORE_ENV   && echo "  ✓ .env restored     (timestamp: $TIMESTAMP)"
$RESTORE_MEDIA && echo "  ✓ Media restored    (timestamp: $TIMESTAMP)"
echo ""
if $RESTORE_ENV; then
    echo "NEXT STEP: Restart all services to apply the restored .env:"
    echo "  docker-compose down && docker-compose up -d"
    echo ""
fi
echo "IMPORTANT: Verify the application is working correctly before declaring"
echo "           the restore complete."
echo ""
