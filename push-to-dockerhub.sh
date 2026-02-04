#!/bin/bash

################################################################################
# ISS Portal - Push Docker Images to Docker Hub
# 
# Builds and pushes Docker images to Docker Hub for easy deployment.
# Images can then be pulled on deployment servers without building.
#
# Usage: ./push-to-dockerhub.sh [docker-hub-username] [version]
# Example: ./push-to-dockerhub.sh myusername 1.0.0
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Get Docker Hub username
if [ -z "$1" ]; then
    echo -e "${YELLOW}Docker Hub username not provided.${NC}"
    read -p "Enter your Docker Hub username: " DOCKER_USERNAME
else
    DOCKER_USERNAME=$1
fi

# Get version
if [ -z "$2" ]; then
    VERSION=$(date +%Y.%m.%d)
    log_info "No version specified, using date-based version: $VERSION"
else
    VERSION=$2
    log_info "Using specified version: $VERSION"
fi

IMAGE_NAME="${DOCKER_USERNAME}/iss-portal"
IMAGE_TAG_VERSION="${IMAGE_NAME}:${VERSION}"
IMAGE_TAG_LATEST="${IMAGE_NAME}:latest"

echo ""
echo "================================================================================"
log_info "Docker Hub Push Configuration"
echo "================================================================================"
echo ""
echo "  Docker Hub User:  ${DOCKER_USERNAME}"
echo "  Image Name:       ${IMAGE_NAME}"
echo "  Version Tag:      ${IMAGE_TAG_VERSION}"
echo "  Latest Tag:       ${IMAGE_TAG_LATEST}"
echo ""
echo "================================================================================"
echo ""

read -p "Proceed with build and push? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Operation cancelled by user."
    exit 0
fi

# Check if logged in to Docker Hub
log_info "Checking Docker Hub authentication..."
if ! docker info 2>/dev/null | grep -q "Username: ${DOCKER_USERNAME}"; then
    log_warning "Not logged in to Docker Hub."
    echo "Please log in to Docker Hub:"
    docker login
    if [ $? -ne 0 ]; then
        log_error "Docker Hub login failed."
        exit 1
    fi
fi
log_success "Docker Hub authentication verified"

# Build the image
log_info "Building Docker image..."
docker build -t ${IMAGE_TAG_VERSION} -t ${IMAGE_TAG_LATEST} .

if [ $? -ne 0 ]; then
    log_error "Docker build failed."
    exit 1
fi
log_success "Docker image built successfully"

# Get image size
IMAGE_SIZE=$(docker images ${IMAGE_NAME} --format "{{.Size}}" | head -1)
log_info "Image size: ${IMAGE_SIZE}"

# Push version tag
log_info "Pushing ${IMAGE_TAG_VERSION}..."
docker push ${IMAGE_TAG_VERSION}

if [ $? -ne 0 ]; then
    log_error "Failed to push ${IMAGE_TAG_VERSION}"
    exit 1
fi
log_success "Pushed ${IMAGE_TAG_VERSION}"

# Push latest tag
log_info "Pushing ${IMAGE_TAG_LATEST}..."
docker push ${IMAGE_TAG_LATEST}

if [ $? -ne 0 ]; then
    log_error "Failed to push ${IMAGE_TAG_LATEST}"
    exit 1
fi
log_success "Pushed ${IMAGE_TAG_LATEST}"

# Create docker-compose file for pulling from Docker Hub
log_info "Creating docker-compose.hub.yml for Docker Hub deployment..."

cat > docker-compose.hub.yml << EOF
version: '3.8'

################################################################################
# ISS Portal - Docker Hub Deployment Configuration
#
# This file is used to deploy ISS Portal using pre-built images from Docker Hub
# instead of building locally.
#
# Usage:
#   docker-compose -f docker-compose.hub.yml up -d
#
################################################################################

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: iss_portal_db
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-iss_portal_db}
      - POSTGRES_USER=\${POSTGRES_USER:-iss_user}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD:-change-this-password}
    volumes:
      - iss_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER:-iss_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - iss_network

  # Django Web Application (from Docker Hub)
  web:
    image: ${IMAGE_TAG_LATEST}
    container_name: iss_portal_web
    command: gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 60 --access-logfile - --error-logfile - iss_portal.wsgi:application
    volumes:
      - ./staticfiles:/app/staticfiles
      - ./media:/app/media
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

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: iss_portal_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./staticfiles:/app/staticfiles:ro
      - ./media:/app/media:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
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
EOF

log_success "Created docker-compose.hub.yml"

# Create deployment instructions
log_info "Creating Docker Hub deployment instructions..."

cat > DOCKERHUB_DEPLOYMENT.md << EOF
# ISS Portal - Docker Hub Deployment Guide

This guide covers deploying ISS Portal using pre-built images from Docker Hub.

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- Internet access to pull images

### Installation Steps

1. **Download deployment files:**
   \`\`\`bash
   # Download the minimal deployment package
   curl -L https://github.com/your-org/iss-portal/releases/download/v${VERSION}/deployment-files.tar.gz | tar -xz
   cd iss-portal-deployment
   \`\`\`

2. **Configure environment:**
   \`\`\`bash
   cp env.example .env
   nano .env
   
   # Update these required settings:
   SECRET_KEY=<generate-new-key>
   FIELD_ENCRYPTION_KEY=<generate-new-key>
   POSTGRES_PASSWORD=<strong-password>
   ALLOWED_HOSTS=your-domain.com
   \`\`\`

3. **Deploy with Docker Hub images:**
   \`\`\`bash
   # Pull and start services
   docker-compose -f docker-compose.hub.yml up -d
   
   # Check status
   docker-compose -f docker-compose.hub.yml ps
   
   # View logs
   docker-compose -f docker-compose.hub.yml logs -f
   \`\`\`

4. **Access the application:**
   - URL: http://your-server-ip
   - Default credentials: admin / admin123
   - **Change password immediately!**

## Docker Hub Images

**Image Repository:** \`${IMAGE_NAME}\`

**Available Tags:**
- \`latest\` - Most recent stable version
- \`${VERSION}\` - Specific version tag

**Pull manually:**
\`\`\`bash
docker pull ${IMAGE_TAG_LATEST}
docker pull ${IMAGE_TAG_VERSION}
\`\`\`

## Management Commands

\`\`\`bash
# Start services
docker-compose -f docker-compose.hub.yml up -d

# Stop services
docker-compose -f docker-compose.hub.yml down

# View logs
docker-compose -f docker-compose.hub.yml logs -f web

# Restart services
docker-compose -f docker-compose.hub.yml restart

# Update to latest image
docker-compose -f docker-compose.hub.yml pull web
docker-compose -f docker-compose.hub.yml up -d
\`\`\`

## Updating to New Version

\`\`\`bash
# Pull new image
docker pull ${IMAGE_TAG_LATEST}

# Backup database
docker-compose -f docker-compose.hub.yml exec db pg_dump -U iss_user iss_portal_db > backup.sql

# Restart with new image
docker-compose -f docker-compose.hub.yml up -d
\`\`\`

## Production Deployment

For production, use the production configuration:

\`\`\`bash
docker-compose -f docker-compose.hub.yml -f docker-compose.prod.yml up -d
\`\`\`

## Advantages of Docker Hub Deployment

✅ **Fast deployment** - No build time required
✅ **Consistent images** - Same image across all environments  
✅ **Smaller download** - Only need docker-compose files, not full source
✅ **Automatic updates** - Pull latest tag to update
✅ **Bandwidth efficient** - Docker layer caching on hub

## Minimal Deployment Package

For Docker Hub deployment, you only need:
- docker-compose.hub.yml
- docker-compose.prod.yml (optional, for production)
- nginx/ directory (configuration files)
- .env file (your configuration)

Total size: <1MB vs ~124KB for full source package

## Support

For detailed deployment guide, see DEPLOYMENT.md
For source-based deployment (building locally), use docker-compose.yml

---

**Image:** ${IMAGE_NAME}:${VERSION}  
**Published:** $(date '+%Y-%m-%d')  
**Registry:** Docker Hub
EOF

log_success "Created DOCKERHUB_DEPLOYMENT.md"

echo ""
echo "================================================================================"
log_success "Push Complete!"
echo "================================================================================"
echo ""
echo "Docker Hub Images Published:"
echo "  ${IMAGE_TAG_VERSION}"
echo "  ${IMAGE_TAG_LATEST}"
echo ""
echo "Image Size: ${IMAGE_SIZE}"
echo ""
echo "Docker Hub URL:"
echo "  https://hub.docker.com/r/${IMAGE_NAME}"
echo ""
echo "Pull Commands:"
echo "  docker pull ${IMAGE_TAG_LATEST}"
echo "  docker pull ${IMAGE_TAG_VERSION}"
echo ""
echo "Deploy on Server:"
echo "  1. Copy docker-compose.hub.yml to server"
echo "  2. Create .env file with configuration"
echo "  3. Run: docker-compose -f docker-compose.hub.yml up -d"
echo ""
echo "Files Created:"
echo "  - docker-compose.hub.yml (for Docker Hub deployment)"
echo "  - DOCKERHUB_DEPLOYMENT.md (deployment instructions)"
echo ""
echo "================================================================================"
