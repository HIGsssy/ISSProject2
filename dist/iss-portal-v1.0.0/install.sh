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
