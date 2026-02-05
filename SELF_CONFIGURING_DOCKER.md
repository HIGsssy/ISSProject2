# Self-Configuring Docker Deployment

## Overview
The ISS Portal Docker image now includes a self-configuring setup system that runs automatically on first launch. This eliminates the need for manual `.env` file creation and key generation when using the Docker Hub distribution method.

## How It Works

### Architecture

1. **Interactive Setup Command** (`core/management/commands/interactive_setup.py`)
   - Django management command that handles first-time configuration
   - Prompts user for necessary settings
   - Automatically generates security keys
   - Creates and saves `.env` file

2. **Smart Entry Point** (`docker-entrypoint.sh`)
   - Detects if application is configured (checks for `.env` with `FIELD_ENCRYPTION_KEY`)
   - Runs interactive setup on first launch if not configured
   - Skips setup on subsequent runs if already configured
   - Proceeds with normal startup (migrations, static files, initial data)

3. **Docker Compose Configuration** (`docker-compose.hub.yml`)
   - Includes `stdin_open: true` and `tty: true` for interactive prompts
   - Mounts `.env` file as volume for persistence across container restarts
   - Pulls pre-built image from Docker Hub

## User Experience

### First Run
```bash
# User downloads docker-compose.hub.yml
docker-compose -f docker-compose.hub.yml up

# Container starts and displays:
"""
╔════════════════════════════════════════════════════════════════╗
║           ISS Portal - First Time Setup                       ║
╚════════════════════════════════════════════════════════════════╝

This wizard will help you configure your ISS Portal installation.

Enter allowed hosts (default: localhost): my-domain.com
Enter database name (default: iss_portal_db): 
Enter database username (default: iss_user): 
Enter database password: *************
Confirm database password: *************
Enter time zone (default: America/Toronto): 

✓ Generating SECRET_KEY...
✓ Generating FIELD_ENCRYPTION_KEY...
✓ Configuration saved to /app/.env

╔════════════════════════════════════════════════════════════════╗
║           Configuration Complete!                             ║
╚════════════════════════════════════════════════════════════════╝

Summary:
- Allowed Hosts: my-domain.com
- Database: iss_portal_db
- Database User: iss_user
- Time Zone: America/Toronto

⚠️  IMPORTANT SECURITY NOTES:
1. Default admin credentials: admin / admin123
2. Change admin password immediately after first login
3. Keep your .env file secure and backed up

Setup completed at 2026-02-02 15:30:42
"""

# Then continues with normal startup:
# - Waits for PostgreSQL
# - Runs migrations
# - Collects static files
# - Creates initial admin user
# - Starts Gunicorn server
```

### Subsequent Runs
```bash
docker-compose -f docker-compose.hub.yml up -d

# Container detects existing configuration and skips setup
# Application starts directly
```

## Deployment Comparison

### Git Package Distribution
**Target Audience:** Developers, customizable deployments
**Process:**
1. Extract package: `tar -xzf iss-portal-v1.0.0.tar.gz`
2. Run installer: `./install.sh` (interactive configuration)
3. Deploy: `docker-compose up -d`

**Features:**
- Full source code access
- Can modify before deploying
- Interactive configuration via `install.sh`
- Automatic key generation

### Docker Hub Distribution
**Target Audience:** End users, quick deployments
**Process:**
1. Download: `curl -O <docker-compose.hub.yml URL>`
2. Deploy: `docker-compose -f docker-compose.hub.yml up`
3. Configure: Answer interactive prompts

**Features:**
- No package extraction needed
- Pre-built optimized images
- Self-configuring on first run
- One-command deployment

## Technical Implementation

### Interactive Setup Command
**File:** `core/management/commands/interactive_setup.py`

**Key Features:**
- Checks if `.env` exists and contains `FIELD_ENCRYPTION_KEY`
- Uses `input()` for user prompts with defaults
- Uses `getpass.getpass()` for password (hidden input with confirmation)
- Generates `SECRET_KEY` with `secrets.token_urlsafe(50)`
- Generates `FIELD_ENCRYPTION_KEY` with `Fernet.generate_key()`
- Creates `.env` file at `/app/.env` with permissions `0o600`
- Displays configuration summary

**Configuration Prompts:**
```python
allowed_hosts = input('Enter allowed hosts (default: localhost): ').strip() or 'localhost'
db_name = input('Enter database name (default: iss_portal_db): ').strip() or 'iss_portal_db'
db_user = input('Enter database username (default: iss_user): ').strip() or 'iss_user'
db_password = getpass.getpass('Enter database password: ')
confirm_password = getpass.getpass('Confirm database password: ')
tz_value = input('Enter time zone (default: America/Toronto): ').strip() or 'America/Toronto'
```

**Generated Keys:**
```python
secret_key = secrets.token_urlsafe(50)
fernet_key = Fernet.generate_key().decode()
```

**Output File:** `/app/.env`
```
SECRET_KEY=<generated>
DEBUG=False
ALLOWED_HOSTS=<user-provided>
POSTGRES_DB=<user-provided>
POSTGRES_USER=<user-provided>
POSTGRES_PASSWORD=<user-provided>
DATABASE_URL=postgresql://<user>:<password>@db:5432/<dbname>
FIELD_ENCRYPTION_KEY=<generated>
TIME_ZONE=<user-provided>
```

### Entry Point Script
**File:** `docker-entrypoint.sh`

**First Run Detection:**
```bash
# Check if .env is missing, empty, or doesn't have encryption key
if [ ! -f "/app/.env" ] || [ ! -s "/app/.env" ] || ! grep -q "FIELD_ENCRYPTION_KEY=" /app/.env; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           ISS Portal - First Time Setup                       ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    python manage.py interactive_setup
    
    echo ""
    echo "✓ Setup complete! Starting application..."
    echo ""
fi
```

**Then continues with normal startup:**
```bash
# Wait for PostgreSQL
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

# Run migrations, collect static files, create initial data
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py create_initial_data

# Execute the main command (typically gunicorn)
exec "$@"
```

## Security Considerations

1. **Password Masking:** Uses `getpass` for hidden password input
2. **Password Confirmation:** Requires matching passwords
3. **File Permissions:** `.env` file set to `0o600` (owner read/write only)
4. **Key Generation:** Cryptographically secure random key generation
5. **Default Credentials:** User warned to change admin password
6. **Volume Mounting:** `.env` persists across container restarts via volume

## Testing

### Test Self-Configuring Deployment
```bash
# Create clean test directory
mkdir iss-portal-test
cd iss-portal-test

# Download docker-compose.hub.yml
curl -O https://raw.githubusercontent.com/your-org/iss-portal/main/docker-compose.hub.yml

# Pull images (optional - will auto-pull on up)
docker pull hgisssy/iss-portal:latest
docker pull postgres:15-alpine
docker pull nginx:alpine

# Start and configure
docker-compose -f docker-compose.hub.yml up

# Follow prompts:
# - Hosts: localhost (or your domain)
# - DB Name: iss_portal_db
# - DB User: iss_user
# - DB Password: (enter secure password)
# - Timezone: America/Toronto (or your timezone)

# After setup completes, access:
# http://localhost
# Login: admin / admin123
```

### Test Subsequent Run
```bash
# Stop containers
docker-compose -f docker-compose.hub.yml down

# Start again - should skip setup
docker-compose -f docker-compose.hub.yml up -d

# Verify .env file was preserved
docker exec iss_portal_web cat /app/.env
```

### Test Manual Configuration
```bash
# Create .env file manually
cat > .env << 'EOF'
SECRET_KEY=manually-set-key
DEBUG=False
ALLOWED_HOSTS=localhost
POSTGRES_DB=iss_portal_db
POSTGRES_USER=iss_user
POSTGRES_PASSWORD=test123
DATABASE_URL=postgresql://iss_user:test123@db:5432/iss_portal_db
FIELD_ENCRYPTION_KEY=manually-set-encryption-key
TIME_ZONE=America/Toronto
EOF

# Start with existing .env
docker-compose -f docker-compose.hub.yml up -d

# Should skip interactive setup and use existing .env
```

## Maintenance

### Update Docker Image
```bash
# Pull latest image
docker-compose -f docker-compose.hub.yml pull web

# Restart with new image
docker-compose -f docker-compose.hub.yml up -d
```

### View Configuration
```bash
# View current .env settings
docker exec iss_portal_web cat /app/.env
```

### Backup Configuration
```bash
# Backup .env file
docker cp iss_portal_web:/app/.env ./env.backup

# Or backup from mounted volume
cp .env .env.backup
```

### Regenerate Keys
```bash
# Stop containers
docker-compose -f docker-compose.hub.yml down

# Remove .env to trigger setup again
rm .env

# Start and reconfigure
docker-compose -f docker-compose.hub.yml up
```

## Version Information

- **Docker Image:** hgisssy/iss-portal:latest
- **Version Tag:** hgisssy/iss-portal:1.0.1
- **Feature:** Self-configuring setup system
- **Added:** February 2, 2026
- **Image Size:** ~405 MB

## Documentation Links

- [Docker Hub Deployment Guide](DOCKERHUB_DEPLOYMENT.md) - Complete deployment instructions
- [Distribution Guide](DISTRIBUTION_GUIDE.md) - Maintainer guide for releases
- [Package README](PACKAGE_README.md) - Git package installation guide
- [Deployment Guide](DEPLOYMENT.md) - Comprehensive deployment documentation
