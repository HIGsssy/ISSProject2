# ISS Portal - Docker Hub Deployment Guide

This guide covers deploying ISS Portal using pre-built images from Docker Hub.

## Quick Start (Self-Configuring - Recommended)

The ISS Portal Docker image is now **completely self-configuring**! On first run, it will interactively prompt you for all configuration settings and automatically generate security keys.

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- Internet access to pull images

### Simple Installation Steps

1. **Download docker-compose.hub.yml:**
   ```bash
   curl -O https://raw.githubusercontent.com/your-org/iss-portal/main/docker-compose.hub.yml
   ```

2. **Start the application:**
   ```bash
   docker-compose -f docker-compose.hub.yml up
   ```

3. **Follow interactive setup prompts:**
   The container will ask for:
   - **Allowed Hosts** (default: localhost)
   - **Database Name** (default: iss_portal_db)
   - **Database Username** (default: iss_user)
   - **Database Password** (you must provide this - use a strong password!)
   - **Time Zone** (default: America/Toronto)

   The system automatically generates:
   - `SECRET_KEY` for Django security
   - `FIELD_ENCRYPTION_KEY` for PII encryption

4. **Access the application:**
   - URL: http://localhost or http://your-server-ip
   - Default credentials: **admin / admin123**
   - **IMPORTANT: Change the default password immediately!**

### Subsequent Runs
After initial setup, simply use:
```bash
docker-compose -f docker-compose.hub.yml up -d
```
The setup will be skipped and the application starts directly.

## Manual Configuration (Optional)

If you prefer to configure manually before starting, create a `.env` file:
```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database Settings
POSTGRES_DB=iss_portal_db
POSTGRES_USER=iss_user
POSTGRES_PASSWORD=secure_password_here

# Encryption
FIELD_ENCRYPTION_KEY=your-encryption-key-here

# Time Zone
TIME_ZONE=America/Toronto
```

Then start with:
```bash
docker-compose -f docker-compose.hub.yml up -d
```

## Docker Hub Images

**Image Repository:** `hgisssy/iss-portal`

**Available Tags:**
- `latest` - Most recent stable version
- `2026.02.02` - Specific version tag

**Pull manually:**
```bash
docker pull hgisssy/iss-portal:latest
docker pull hgisssy/iss-portal:2026.02.02
```

## Management Commands

```bash
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
```

## Updating to New Version

```bash
# Pull new image
docker pull hgisssy/iss-portal:latest

# Backup database
docker-compose -f docker-compose.hub.yml exec db pg_dump -U iss_user iss_portal_db > backup.sql

# Restart with new image
docker-compose -f docker-compose.hub.yml up -d
```

## Production Deployment

For production, use the production configuration:

```bash
docker-compose -f docker-compose.hub.yml -f docker-compose.prod.yml up -d
```

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

**Image:** hgisssy/iss-portal:2026.02.02  
**Published:** 2026-02-02  
**Registry:** Docker Hub
