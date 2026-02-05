#!/bin/bash

################################################################################
# ISS Portal - Build Deployment Package
# 
# Creates a distributable deployment package with versioning, checksums,
# and comprehensive manifest files for production deployments.
#
# Usage: ./build-package.sh [version]
# Example: ./build-package.sh 1.0.0
#          ./build-package.sh (uses date-based version: YYYY.MM.DD)
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

# Determine version
if [ -z "$1" ]; then
    VERSION=$(date +%Y.%m.%d)
    log_info "No version specified, using date-based version: $VERSION"
else
    VERSION=$1
    log_info "Using specified version: $VERSION"
fi

PACKAGE_NAME="iss-portal-v${VERSION}"
BUILD_DIR="dist/${PACKAGE_NAME}"
PACKAGE_FILE="dist/${PACKAGE_NAME}.tar.gz"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "Starting build process for ${PACKAGE_NAME}..."

# Create clean build directory
log_info "Creating build directory..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Files and directories to include in package
log_info "Copying application files..."

# Core application files
cp -r accounts "$BUILD_DIR/"
cp -r audit "$BUILD_DIR/"
cp -r core "$BUILD_DIR/"
cp -r iss_portal "$BUILD_DIR/"
cp -r nginx "$BUILD_DIR/"
cp -r reports "$BUILD_DIR/"
cp -r static "$BUILD_DIR/"
cp -r templates "$BUILD_DIR/"

# Configuration and Docker files
cp docker-compose.yml "$BUILD_DIR/"
cp Dockerfile "$BUILD_DIR/"
cp docker-entrypoint.sh "$BUILD_DIR/"
cp .dockerignore "$BUILD_DIR/"

# Docker Hub deployment files (if they exist)
if [ -f "docker-compose.hub.yml" ]; then
    cp docker-compose.hub.yml "$BUILD_DIR/"
    log_info "Added docker-compose.hub.yml for Docker Hub deployment"
fi

if [ -f "DOCKERHUB_DEPLOYMENT.md" ]; then
    cp DOCKERHUB_DEPLOYMENT.md "$BUILD_DIR/"
    log_info "Added Docker Hub deployment guide"
fi

# Python dependencies
cp requirements.txt "$BUILD_DIR/"
cp manage.py "$BUILD_DIR/"

# Scripts
cp deploy.sh "$BUILD_DIR/"
cp upgrade.sh "$BUILD_DIR/"
cp backup.sh "$BUILD_DIR/"
cp start.sh "$BUILD_DIR/"
cp stop.sh "$BUILD_DIR/"
cp status.sh "$BUILD_DIR/"

# Systemd service file
cp iss-portal.service "$BUILD_DIR/"

# Documentation
cp README.md "$BUILD_DIR/"
cp DEPLOYMENT.md "$BUILD_DIR/"
cp CSV_IMPORT_FORMAT.md "$BUILD_DIR/"

# Package-specific README (becomes main README in package)
if [ -f "PACKAGE_README.md" ]; then
    cp PACKAGE_README.md "$BUILD_DIR/PACKAGE_README.md"
    log_info "Added package-specific README"
fi

# Environment template
cp .env.example "$BUILD_DIR/env.example"

log_info "Creating installation structure..."

# Create necessary directories
mkdir -p "$BUILD_DIR/media"
mkdir -p "$BUILD_DIR/staticfiles"
mkdir -p "$BUILD_DIR/backups"
mkdir -p "$BUILD_DIR/logs"

# Create .gitkeep files for empty directories
touch "$BUILD_DIR/media/.gitkeep"
touch "$BUILD_DIR/staticfiles/.gitkeep"
touch "$BUILD_DIR/backups/.gitkeep"
touch "$BUILD_DIR/logs/.gitkeep"

# Generate manifest file
log_info "Generating package manifest..."
MANIFEST_FILE="$BUILD_DIR/MANIFEST.txt"

cat > "$MANIFEST_FILE" << EOF
================================================================================
ISS Portal - Deployment Package Manifest
================================================================================

Package Information:
-------------------
Package Name: ${PACKAGE_NAME}
Version: ${VERSION}
Build Date: $(date '+%Y-%m-%d %H:%M:%S %Z')
Built By: $(whoami)
Build Host: $(hostname)

Package Contents:
----------------
EOF

# List all files in the package
find "$BUILD_DIR" -type f -not -path "*/.*" -not -name "MANIFEST.txt" | sort | sed "s|^$BUILD_DIR/|  - |" >> "$MANIFEST_FILE"

cat >> "$MANIFEST_FILE" << EOF

Installation Instructions:
-------------------------
1. Extract this package:
   tar -xzf ${PACKAGE_NAME}.tar.gz

2. Navigate to extracted directory:
   cd ${PACKAGE_NAME}

3. Copy env.example to .env and configure:
   cp env.example .env
   nano .env

4. Run the deployment script:
   chmod +x deploy.sh
   sudo ./deploy.sh

5. Access the application:
   http://your-server-ip

For detailed instructions, see DEPLOYMENT.md

Requirements:
------------
- Docker Engine 20.10 or later
- Docker Compose 2.0 or later
- 2GB RAM minimum (4GB recommended)
- 20GB disk space minimum
- Ubuntu 20.04/22.04 or similar Linux distribution

Support:
--------
For issues or questions, refer to:
- DEPLOYMENT.md - Comprehensive deployment guide
- README.md - Application overview and quick start
- PROJECT_STATUS.md - Current implementation status

Security Notes:
--------------
- Change all default passwords in .env file
- Generate new SECRET_KEY and FIELD_ENCRYPTION_KEY
- Configure firewall rules appropriately
- Enable SSL/HTTPS for production (see DEPLOYMENT.md)
- Regularly backup encryption keys (stored in .env)

================================================================================
EOF

log_success "Manifest file created: $MANIFEST_FILE"

# Generate installation script
log_info "Creating quick installation script..."
INSTALL_SCRIPT="$BUILD_DIR/install.sh"

cat > "$INSTALL_SCRIPT" << 'EOF'
#!/bin/bash
################################################################################
# ISS Portal - Quick Installation Script
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}ISS Portal - Quick Installation${NC}"
echo -e "${BLUE}================================${NC}\n"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${YELLOW}[WARNING]${NC} Running as root. Consider using sudo instead."
fi

# Check for required commands
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}[ERROR]${NC} Required command not found: $1"
        echo "Please install $1 and try again."
        exit 1
    fi
}

echo -e "${BLUE}[STEP 1/5]${NC} Checking requirements..."
check_command docker
check_command docker-compose

echo -e "${GREEN}✓${NC} Docker found: $(docker --version)"
echo -e "${GREEN}✓${NC} Docker Compose found: $(docker-compose --version)\n"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[STEP 2/5]${NC} Creating .env file from template..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo -e "${GREEN}✓${NC} .env file created"
        
        echo -e "\n${BLUE}════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}          ISS Portal Configuration Setup            ${NC}"
        echo -e "${BLUE}════════════════════════════════════════════════════${NC}\n"
        
        # Prompt for configuration values
        echo -e "${BLUE}Please provide the following configuration values:${NC}"
        echo -e "${YELLOW}(Press Enter to use default value shown in brackets)${NC}\n"
        
        # ALLOWED_HOSTS
        read -p "Domain/IP for ALLOWED_HOSTS [localhost]: " ALLOWED_HOSTS_INPUT
        ALLOWED_HOSTS=${ALLOWED_HOSTS_INPUT:-localhost}
        sed -i "s/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$ALLOWED_HOSTS/" .env
        echo -e "${GREEN}✓${NC} ALLOWED_HOSTS set to: $ALLOWED_HOSTS\n"
        
        # Database name
        read -p "Database name [iss_portal_db]: " DB_NAME_INPUT
        DB_NAME=${DB_NAME_INPUT:-iss_portal_db}
        sed -i "s/POSTGRES_DB=.*/POSTGRES_DB=$DB_NAME/" .env
        echo -e "${GREEN}✓${NC} Database name set to: $DB_NAME\n"
        
        # Database user
        read -p "Database username [iss_user]: " DB_USER_INPUT
        DB_USER=${DB_USER_INPUT:-iss_user}
        sed -i "s/POSTGRES_USER=.*/POSTGRES_USER=$DB_USER/" .env
        echo -e "${GREEN}✓${NC} Database username set to: $DB_USER\n"
        
        # Database password
        while true; do
            read -s -p "Database password (required, will not echo): " DB_PASSWORD
            echo
            if [ -z "$DB_PASSWORD" ]; then
                echo -e "${RED}Password cannot be empty. Please try again.${NC}\n"
            else
                read -s -p "Confirm password: " DB_PASSWORD_CONFIRM
                echo
                if [ "$DB_PASSWORD" = "$DB_PASSWORD_CONFIRM" ]; then
                    # Escape special characters for sed
                    ESCAPED_PASSWORD=$(echo "$DB_PASSWORD" | sed 's/[\/&]/\\&/g')
                    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$ESCAPED_PASSWORD/" .env
                    echo -e "${GREEN}✓${NC} Database password set\n"
                    break
                else
                    echo -e "${RED}Passwords do not match. Please try again.${NC}\n"
                fi
            fi
        done
        
        # Timezone
        read -p "Timezone [America/Toronto]: " TZ_INPUT
        TZ_VALUE=${TZ_INPUT:-America/Toronto}
        sed -i "s|TZ=.*|TZ=$TZ_VALUE|" .env
        echo -e "${GREEN}✓${NC} Timezone set to: $TZ_VALUE\n"
        
        echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
        echo -e "${BLUE}[STEP 3/5]${NC} Generating security keys..."
        echo -e "${BLUE}════════════════════════════════════════════════════${NC}\n"
        
        # Generate SECRET_KEY
        echo -e "${BLUE}Generating Django SECRET_KEY...${NC}"
        SECRET_KEY=$(openssl rand -base64 50 | tr -d '\n')
        if [ -n "$SECRET_KEY" ]; then
            # Escape special characters for sed
            ESCAPED_KEY=$(echo "$SECRET_KEY" | sed 's/[\/&]/\\&/g')
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$ESCAPED_KEY/" .env
            echo -e "${GREEN}✓${NC} SECRET_KEY generated and added to .env\n"
        else
            echo -e "${YELLOW}[WARNING]${NC} Could not generate SECRET_KEY, please set manually\n"
        fi
        
        # Generate FIELD_ENCRYPTION_KEY (uses temporary Python container, not the app image)
        echo -e "${BLUE}Generating FIELD_ENCRYPTION_KEY...${NC}"
        echo -e "${YELLOW}(This will pull python:3.11-slim image if not already present)${NC}"
        ENCRYPTION_KEY=$(docker run --rm python:3.11-slim bash -c \
            "pip install -q cryptography && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"" 2>/dev/null)
        
        if [ -n "$ENCRYPTION_KEY" ]; then
            sed -i "s/FIELD_ENCRYPTION_KEY=.*/FIELD_ENCRYPTION_KEY=$ENCRYPTION_KEY/" .env
            echo -e "${GREEN}✓${NC} FIELD_ENCRYPTION_KEY generated and added to .env\n"
        else
            echo -e "${YELLOW}[WARNING]${NC} Could not generate FIELD_ENCRYPTION_KEY automatically"
            echo "You can generate it manually after installation with:"
            echo '  docker run --rm python:3.11-slim bash -c "pip install -q cryptography && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""'
            echo ""
        fi
        
        echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ Configuration Complete!${NC}"
        echo -e "${BLUE}════════════════════════════════════════════════════${NC}\n"
        
        echo -e "${BLUE}Configuration Summary:${NC}"
        echo "  Domain/IP:      $ALLOWED_HOSTS"
        echo "  Database:       $DB_NAME"
        echo "  DB User:        $DB_USER"
        echo "  Timezone:       $TZ_VALUE"
        echo "  SECRET_KEY:     [generated]"
        echo "  ENCRYPTION_KEY: [generated]"
        echo ""
        echo -e "${YELLOW}Note:${NC} All settings have been saved to .env file"
        echo "You can edit .env directly if you need to change anything."
        echo ""
        read -p "Press Enter to continue..."
    else
        echo -e "${RED}[ERROR]${NC} env.example not found!"
        exit 1
    fi
else
    echo -e "${BLUE}[STEP 2/5]${NC} Using existing .env file"
    echo -e "${BLUE}[STEP 3/5]${NC} Skipping configuration (using existing .env)"
fi

echo -e "\n${BLUE}[STEP 4/5]${NC} Making scripts executable..."
chmod +x *.sh
echo -e "${GREEN}✓${NC} Scripts are now executable\n"

echo -e "${BLUE}[STEP 5/5]${NC} Would you like to run the full deployment now?"
echo "This will:"
echo "  - Build Docker images"
echo "  - Create database"
echo "  - Run migrations"
echo "  - Collect static files"
echo "  - Start all services"
echo ""
read -p "Proceed with deployment? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${BLUE}[STEP 5/5]${NC} Running deployment..."
    ./deploy.sh
else
    echo -e "\n${YELLOW}[SKIPPED]${NC} Deployment skipped."
    echo "To deploy later, run: ./deploy.sh"
fi

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}================================${NC}\n"
echo "Next steps:"
echo "  - Review DEPLOYMENT.md for detailed configuration"
echo "  - Access the application at http://localhost or your server IP"
echo "  - Default admin credentials: admin / admin123"
echo "  - Change default passwords immediately!"
echo ""
echo "Useful commands:"
echo "  ./status.sh    - Check service status"
echo "  ./backup.sh    - Create backup"
echo "  ./stop.sh      - Stop services"
echo "  ./start.sh     - Start services"
echo ""
EOF

chmod +x "$INSTALL_SCRIPT"
log_success "Quick installation script created"

# Create version file
log_info "Creating version file..."
VERSION_FILE="$BUILD_DIR/VERSION"
cat > "$VERSION_FILE" << EOF
VERSION=$VERSION
BUILD_DATE=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
BUILD_HOST=$(hostname)
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "not-available")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "not-available")
EOF

log_success "Version file created"

# Create tarball
log_info "Creating compressed package..."
cd dist
tar -czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}"
cd ..

if [ ! -f "$PACKAGE_FILE" ]; then
    log_error "Failed to create package file!"
    exit 1
fi

PACKAGE_SIZE=$(du -h "$PACKAGE_FILE" | cut -f1)
log_success "Package created: ${PACKAGE_FILE} (${PACKAGE_SIZE})"

# Generate checksums
log_info "Generating checksums..."
CHECKSUM_FILE="${PACKAGE_FILE}.sha256"

if command -v sha256sum &> /dev/null; then
    cd dist
    sha256sum "${PACKAGE_NAME}.tar.gz" > "${PACKAGE_NAME}.tar.gz.sha256"
    cd ..
    CHECKSUM=$(cat "$CHECKSUM_FILE")
    log_success "SHA256 checksum: ${CHECKSUM}"
else
    log_warning "sha256sum not available, skipping checksum generation"
fi

# Create release notes
log_info "Creating release notes..."
RELEASE_NOTES="dist/${PACKAGE_NAME}-RELEASE_NOTES.txt"

cat > "$RELEASE_NOTES" << EOF
================================================================================
ISS Portal - Release Notes
================================================================================

Version: ${VERSION}
Release Date: $(date '+%Y-%m-%d')

Package Details:
--------------
File: ${PACKAGE_NAME}.tar.gz
Size: ${PACKAGE_SIZE}
SHA256: $(cat "$CHECKSUM_FILE" 2>/dev/null | cut -d' ' -f1 || echo "not-generated")

What's Included:
---------------
- Complete Django application with all apps
- Docker and Docker Compose configuration
- Nginx reverse proxy configuration
- Database migration scripts
- Deployment and management scripts
- Comprehensive documentation
- Systemd service file for auto-start

System Requirements:
-------------------
- Docker Engine 20.10+
- Docker Compose 2.0+
- Linux server (Ubuntu 20.04/22.04 recommended)
- 2GB RAM minimum (4GB recommended)
- 20GB disk space minimum
- PostgreSQL 15 (included in Docker)

Quick Start:
-----------
1. Extract: tar -xzf ${PACKAGE_NAME}.tar.gz
2. Configure: cd ${PACKAGE_NAME} && cp env.example .env && nano .env
3. Install: ./install.sh
4. Access: http://your-server-ip

For detailed instructions, see DEPLOYMENT.md inside the package.

Security Considerations:
-----------------------
- Change all default passwords
- Generate new SECRET_KEY
- Generate new FIELD_ENCRYPTION_KEY
- Configure firewall appropriately
- Enable HTTPS for production
- Review and update .env file completely

Support:
--------
For issues, refer to documentation in the package:
- DEPLOYMENT.md - Full deployment guide
- README.md - Application overview
- MANIFEST.txt - Complete file listing

================================================================================
EOF

log_success "Release notes created: $RELEASE_NOTES"

# Clean up build directory (keep tarball and checksums)
log_info "Cleaning up temporary files..."
rm -rf "$BUILD_DIR"
log_success "Build directory cleaned"

# Final summary
echo ""
echo "================================================================================"
log_success "Build Complete!"
echo "================================================================================"
echo ""
echo "Package Information:"
echo "  Name:     ${PACKAGE_NAME}"
echo "  Version:  ${VERSION}"
echo "  File:     ${PACKAGE_FILE}"
echo "  Size:     ${PACKAGE_SIZE}"
echo ""
echo "Generated Files:"
echo "  - ${PACKAGE_FILE}"
if [ -f "$CHECKSUM_FILE" ]; then
    echo "  - ${CHECKSUM_FILE}"
fi
echo "  - ${RELEASE_NOTES}"
echo ""
echo "Next Steps:"
echo "  1. Test the package:"
echo "     tar -xzf ${PACKAGE_FILE}"
echo "     cd ${PACKAGE_NAME}"
echo "     ./install.sh"
echo ""
echo "  2. Verify checksum (on deployment server):"
if [ -f "$CHECKSUM_FILE" ]; then
    echo "     sha256sum -c ${PACKAGE_NAME}.tar.gz.sha256"
fi
echo ""
echo "  3. Review release notes:"
echo "     cat ${RELEASE_NOTES}"
echo ""
echo "================================================================================"
