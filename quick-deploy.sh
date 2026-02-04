#!/bin/bash

################################################################################
# ISS Portal - Quick Deploy from Docker Hub
# 
# This script sets up ISS Portal by pulling pre-built images from Docker Hub.
# No build required - just configuration and deployment.
#
# Usage: 
#   curl -fsSL https://raw.githubusercontent.com/your-org/iss-portal/main/quick-deploy.sh | bash
#   OR
#   wget -O - https://raw.githubusercontent.com/your-org/iss-portal/main/quick-deploy.sh | bash
#
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "================================================================================"
echo -e "${BLUE}ISS Portal - Quick Deploy from Docker Hub${NC}"
echo "================================================================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

log_success "Docker found: $(docker --version)"

# Create deployment directory
DEPLOY_DIR="iss-portal-deploy"
log_info "Creating deployment directory: $DEPLOY_DIR"
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

# Create docker-compose.hub.yml
log_info "Creating docker-compose.hub.yml..."
cat > docker-compose.hub.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    container_name: iss_portal_db
    environment:
      - POSTGRES_DB=${POSTGRES_DB:-iss_portal_db}
      - POSTGRES_USER=${POSTGRES_USER:-iss_user}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - iss_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-iss_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - iss_network

  web:
    image: hgisssy/iss-portal:latest
    container_name: iss_portal_web
    command: gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 60 --access-logfile - --error-logfile - iss_portal.wsgi:application
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/admin/login/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - iss_network
    restart: unless-stopped

volumes:
  iss_postgres_data:
    name: iss_postgres_data

networks:
  iss_network:
    name: iss_network
    driver: bridge
COMPOSE_EOF

log_success "Created docker-compose.hub.yml"

# Interactive configuration
echo ""
log_info "Configuration Setup"
echo "Please provide the following values:"
echo ""

read -p "Domain/IP for ALLOWED_HOSTS [localhost]: " ALLOWED_HOSTS
ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost}

read -p "Database name [iss_portal_db]: " DB_NAME
DB_NAME=${DB_NAME:-iss_portal_db}

read -p "Database username [iss_user]: " DB_USER
DB_USER=${DB_USER:-iss_user}

while true; do
    read -s -p "Database password (required): " DB_PASSWORD
    echo
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${RED}Password required.${NC}"
    else
        read -s -p "Confirm password: " DB_PASSWORD_CONFIRM
        echo
        if [ "$DB_PASSWORD" = "$DB_PASSWORD_CONFIRM" ]; then
            break
        else
            echo -e "${RED}Passwords do not match.${NC}"
        fi
    fi
done

read -p "Timezone [America/Toronto]: " TZ_VALUE
TZ_VALUE=${TZ_VALUE:-America/Toronto}

# Generate keys
log_info "Generating security keys..."
SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n')
log_success "SECRET_KEY generated"

log_info "Generating encryption key (this may take a moment)..."
ENCRYPTION_KEY=$(docker run --rm python:3.11-slim bash -c \
    "pip install -q cryptography 2>/dev/null && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"" 2>/dev/null)

if [ -z "$ENCRYPTION_KEY" ]; then
    log_error "Could not generate encryption key. Please generate manually."
    exit 1
fi
log_success "FIELD_ENCRYPTION_KEY generated"

# Create .env file
log_info "Creating .env file..."
cat > .env << ENV_EOF
# Django Settings
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$ALLOWED_HOSTS

# Database
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASSWORD

# Encryption
FIELD_ENCRYPTION_KEY=$ENCRYPTION_KEY

# Timezone
TZ=$TZ_VALUE

# Database connection
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@db:5432/$DB_NAME
ENV_EOF

log_success "Configuration saved to .env"

# Create directories
mkdir -p staticfiles media
log_success "Created staticfiles and media directories"

# Deploy
echo ""
log_info "Configuration complete! Summary:"
echo "  Domain/IP:  $ALLOWED_HOSTS"
echo "  Database:   $DB_NAME"
echo "  DB User:    $DB_USER"
echo "  Timezone:   $TZ_VALUE"
echo ""

read -p "Deploy now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Pulling Docker images..."
    docker pull hgisssy/iss-portal:latest
    docker pull postgres:15-alpine
    
    log_info "Starting services..."
    docker-compose -f docker-compose.hub.yml up -d
    
    log_info "Waiting for services to be ready..."
    sleep 10
    
    log_info "Checking status..."
    docker-compose -f docker-compose.hub.yml ps
    
    echo ""
    echo "================================================================================"
    log_success "Deployment Complete!"
    echo "================================================================================"
    echo ""
    echo "Access your application:"
    echo "  URL: http://$ALLOWED_HOSTS:8000"
    echo "  Default credentials: admin / admin123"
    echo ""
    echo -e "${RED}⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!${NC}"
    echo ""
    echo "Management commands:"
    echo "  View logs:    docker-compose -f docker-compose.hub.yml logs -f"
    echo "  Stop:         docker-compose -f docker-compose.hub.yml down"
    echo "  Restart:      docker-compose -f docker-compose.hub.yml restart"
    echo "  Update:       docker-compose -f docker-compose.hub.yml pull && docker-compose -f docker-compose.hub.yml up -d"
    echo ""
else
    echo ""
    log_info "Deployment skipped. To deploy later:"
    echo "  cd $DEPLOY_DIR"
    echo "  docker-compose -f docker-compose.hub.yml up -d"
    echo ""
fi

echo "================================================================================"
