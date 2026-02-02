# ISS Portal - Docker Hub Deployment Guide

This guide covers deploying ISS Portal using pre-built images from Docker Hub.

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- Internet access to pull images

### Installation Steps

1. **Download deployment files:**
   ```bash
   # Download the minimal deployment package
   curl -L https://github.com/your-org/iss-portal/releases/download/v2026.02.02/deployment-files.tar.gz | tar -xz
   cd iss-portal-deployment
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   nano .env
   
   # Update these required settings:
   SECRET_KEY=<generate-new-key>
   FIELD_ENCRYPTION_KEY=<generate-new-key>
   POSTGRES_PASSWORD=<strong-password>
   ALLOWED_HOSTS=your-domain.com
   ```

3. **Deploy with Docker Hub images:**
   ```bash
   # Pull and start services
   docker-compose -f docker-compose.hub.yml up -d
   
   # Check status
   docker-compose -f docker-compose.hub.yml ps
   
   # View logs
   docker-compose -f docker-compose.hub.yml logs -f
   ```

4. **Access the application:**
   - URL: http://your-server-ip
   - Default credentials: admin / admin123
   - **Change password immediately!**

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
