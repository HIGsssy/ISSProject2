#!/bin/bash
# ISS Portal - Initial Deployment Script
# This script handles first-time installation of the ISS Portal application

set -e  # Exit on error

echo "========================================"
echo "ISS Portal - Initial Deployment"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Please install Docker first: https://docs.docker.com/engine/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed."
    echo "Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo ""
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    echo "IMPORTANT: Set the following required variables:"
    echo "  - FIELD_ENCRYPTION_KEY (generate with: docker-compose run --rm web python manage.py generate_encryption_key)"
    echo "  - POSTGRES_PASSWORD (use a strong password)"
    echo "  - SECRET_KEY (Django secret key)"
    exit 1
fi

# Check if encryption key is set
if ! grep -q "FIELD_ENCRYPTION_KEY=.\+" .env; then
    echo "ERROR: FIELD_ENCRYPTION_KEY is not set in .env file!"
    echo ""
    echo "Generate and set encryption key:"
    echo "  1. Temporarily start containers: docker-compose up -d db"
    echo "  2. Generate key: docker-compose run --rm --no-deps web python manage.py generate_encryption_key"
    echo "  3. Add key to .env file: FIELD_ENCRYPTION_KEY=<generated_key>"
    echo "  4. Stop containers: docker-compose down"
    echo "  5. Run this script again"
    exit 1
fi

echo "✓ Configuration file (.env) exists"
echo ""

# Build images
echo "Building Docker images..."
docker-compose build
echo ""

# Start database first
echo "Starting database..."
docker-compose up -d db

# Wait for database to be healthy
echo "Waiting for database to be ready..."
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U iss_user &> /dev/null; then
        echo "✓ Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: Database failed to start within 30 seconds"
        docker-compose logs db
        exit 1
    fi
    sleep 1
done
echo ""

# Run migrations
echo "Running database migrations..."
docker-compose run --rm --no-deps web python manage.py migrate
echo ""

# Collect static files
echo "Collecting static files..."
docker-compose run --rm --no-deps web python manage.py collectstatic --noinput
echo ""

# Start all services
echo "Starting all services..."
docker-compose up -d
echo ""

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 5

# Show status
echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
docker-compose ps
echo ""
echo "Next steps:"
echo "  1. Create superuser: docker-compose exec web python manage.py createsuperuser"
echo "  2. Access application: http://localhost (or http://your-server-ip)"
echo "  3. Login with the superuser credentials you created"
echo ""
echo "Management commands:"
echo "  - View logs: docker-compose logs -f web"
echo "  - Stop: docker-compose stop"
echo "  - Restart: docker-compose restart"
echo "  - Backup: ./backup.sh"
echo ""
echo "To enable auto-start on server reboot:"
echo "  sudo systemctl enable docker"
echo "  sudo cp iss-portal.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable iss-portal"
echo ""
