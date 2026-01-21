#!/bin/bash
# ISS Portal - Upgrade Script
# This script safely upgrades the ISS Portal application to a new version

set -e  # Exit on error

echo "========================================"
echo "ISS Portal - Application Upgrade"
echo "========================================"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ] && [ -z "$SUDO_USER" ]; then
    echo "WARNING: Not running as root. You may need sudo for some operations."
    echo ""
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker is not running."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Make sure you copied .env from the previous version."
    exit 1
fi

echo "✓ Configuration file exists"
echo ""

# Create backup before upgrade
echo "Step 1: Creating backup..."
if [ -f backup.sh ]; then
    ./backup.sh
else
    # Manual backup if script doesn't exist
    BACKUP_DIR="backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"
    
    echo "Backing up database..."
    docker-compose exec -T db pg_dump -U iss_user iss_portal_db | gzip > "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql.gz"
    
    echo "Backing up .env file..."
    cp .env "$BACKUP_DIR/.env_${TIMESTAMP}"
    
    echo "✓ Backup saved to $BACKUP_DIR/"
fi
echo ""

# Stop application (keep database running)
echo "Step 2: Stopping application services..."
docker-compose stop web nginx
echo "✓ Application stopped (database still running)"
echo ""

# Pull/build new images
echo "Step 3: Building new application version..."
docker-compose build web
echo "✓ New version built"
echo ""

# Run migrations
echo "Step 4: Running database migrations..."
docker-compose run --rm --no-deps web python manage.py migrate
echo "✓ Migrations complete"
echo ""

# Collect static files
echo "Step 5: Collecting static files..."
docker-compose run --rm --no-deps web python manage.py collectstatic --noinput
echo "✓ Static files collected"
echo ""

# Restart all services
echo "Step 6: Starting services with new version..."
docker-compose up -d
echo ""

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 5

# Check health
echo ""
echo "========================================"
echo "Upgrade Complete!"
echo "========================================"
echo ""
docker-compose ps
echo ""

# Check if web service is healthy
if docker-compose ps | grep -q "web.*Up.*healthy"; then
    echo "✓ Application is running and healthy"
else
    echo "⚠ WARNING: Application may not be fully healthy yet"
    echo "Check logs: docker-compose logs -f web"
fi

echo ""
echo "Upgrade summary:"
echo "  - Database migrated"
echo "  - Static files updated"
echo "  - Application restarted with new version"
echo "  - Backup saved in backups/ directory"
echo ""
echo "Verify the upgrade:"
echo "  1. Access application: http://localhost (or http://your-server-ip)"
echo "  2. Test key functionality"
echo "  3. Check logs: docker-compose logs -f web"
echo ""
echo "Rollback (if needed):"
echo "  1. Stop: docker-compose down"
echo "  2. Restore previous version"
echo "  3. Restore database: gunzip -c backups/db_backup_*.sql.gz | docker-compose exec -T db psql -U iss_user -d iss_portal_db"
echo ""
