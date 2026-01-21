# ISS Portal - Deployment Guide

This guide covers installation, configuration, auto-start setup, monitoring, and upgrades for the ISS Portal application.

## Table of Contents
1. [Server Requirements](#server-requirements)
2. [Initial Installation](#initial-installation)
3. [Configuration](#configuration)
4. [Auto-Start on Boot](#auto-start-on-boot)
5. [Management Commands](#management-commands)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Upgrades](#upgrades)
8. [Backup & Restore](#backup--restore)
9. [Troubleshooting](#troubleshooting)

---

## Server Requirements

### Minimum Requirements
- **OS:** Linux (Ubuntu 22.04 LTS, Debian 11+, RHEL 8+, or similar)
- **CPU:** 2 cores
- **RAM:** 2GB (4GB recommended)
- **Storage:** 20GB minimum (50GB recommended)
- **Network:** Internet access for initial setup
- **Ports:** 80 (HTTP), 443 (HTTPS)

### Software Requirements
- Docker 24.0 or higher
- Docker Compose 2.20 or higher

### Expected Storage Growth
- **Small organization** (500 children): ~100 MB/year
- **Medium organization** (2000 children): ~500 MB/year
- **Large organization** (5000+ children): ~1-2 GB/year

---

## Initial Installation

### Step 1: Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
docker --version
docker compose version
```

### Step 2: Extract Application

```bash
# Create installation directory
sudo mkdir -p /opt/iss-portal
cd /opt/iss-portal

# Extract package (replace with actual version)
sudo tar -xzf iss-portal-v1.0.0.tar.gz -C /opt/iss-portal --strip-components=1

# Set permissions
sudo chown -R $USER:$USER /opt/iss-portal
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Generate encryption key (temporary container method)
docker run --rm -v $(pwd):/app -w /app python:3.11-slim bash -c \
  "pip install -q cryptography && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""

# Edit configuration
nano .env
```

**Required .env variables:**
```bash
# Django Settings
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -base64 50
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
POSTGRES_DB=iss_portal_db
POSTGRES_USER=iss_user
POSTGRES_PASSWORD=strong-password-here

# Encryption (CRITICAL - generated above)
FIELD_ENCRYPTION_KEY=your-encryption-key-here

# Timezone
TZ=America/Toronto  # Adjust to your timezone
```

### Step 4: Deploy Application

```bash
# Make scripts executable
chmod +x deploy.sh upgrade.sh backup.sh start.sh stop.sh status.sh

# Run deployment
./deploy.sh
```

The deployment script will:
- ✓ Build Docker images
- ✓ Start database
- ✓ Run migrations
- ✓ Collect static files
- ✓ Start all services

### Step 5: Create Admin User

```bash
# Create superuser account
docker-compose exec web python manage.py createsuperuser

# Follow prompts to set:
# - Username
# - Email
# - Password
```

### Step 6: Access Application

- **URL:** `http://your-server-ip` or `http://localhost`
- **Login:** Use the superuser credentials created above

---

## Auto-Start on Boot

Choose one of these methods to ensure ISS Portal starts automatically after server reboots.

### Method 1: Systemd Service (Recommended)

This provides the most control and integration with system management.

**Step 1: Install service file**
```bash
sudo cp /opt/iss-portal/iss-portal.service /etc/systemd/system/
```

**Step 2: Enable and start service**
```bash
sudo systemctl daemon-reload
sudo systemctl enable iss-portal.service
sudo systemctl start iss-portal.service
```

**Step 3: Verify service**
```bash
sudo systemctl status iss-portal
```

**Service management commands:**
```bash
# Start
sudo systemctl start iss-portal

# Stop
sudo systemctl stop iss-portal

# Restart
sudo systemctl restart iss-portal

# View logs
sudo journalctl -u iss-portal -f

# Disable auto-start
sudo systemctl disable iss-portal
```

### Method 2: Docker Restart Policies (Simpler)

The application is already configured with `restart: unless-stopped` in docker-compose.yml.

**Just ensure Docker starts on boot:**
```bash
sudo systemctl enable docker
```

**Start application once:**
```bash
cd /opt/iss-portal
docker-compose up -d
```

Containers will automatically restart after server reboots until you explicitly stop them with `docker-compose down`.

### Verify Auto-Start

Test by rebooting the server:
```bash
sudo reboot
```

After reboot, check status:
```bash
cd /opt/iss-portal
./status.sh
# or
docker-compose ps
```

All services should show "Up" status.

---

## Management Commands

### Quick Scripts

```bash
# Start application
./start.sh

# Stop application
./stop.sh

# Check status
./status.sh

# Backup database
./backup.sh

# Upgrade to new version
./upgrade.sh
```

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services (keeps data)
docker-compose stop

# Restart specific service
docker-compose restart web

# View logs
docker-compose logs -f web        # Follow web logs
docker-compose logs --tail=50 web # Last 50 lines

# Check container status
docker-compose ps

# Execute command in container
docker-compose exec web python manage.py <command>
docker-compose exec db psql -U iss_user -d iss_portal_db

# Complete shutdown (keeps volumes/data)
docker-compose down
```

### Application Management

```bash
# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Django shell
docker-compose exec web python manage.py shell

# Database shell
docker-compose exec db psql -U iss_user -d iss_portal_db
```

---

## Monitoring & Maintenance

### Check Database Size

```bash
# Total database size
docker-compose exec db psql -U iss_user -d iss_portal_db -c \
  "SELECT pg_size_pretty(pg_database_size('iss_portal_db'));"

# Size by table
docker-compose exec db psql -U iss_user -d iss_portal_db -c "
SELECT 
  tablename,
  pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC
LIMIT 10;"
```

### Check Host Disk Space

```bash
# Overall disk usage
df -h

# Docker volumes usage
sudo du -sh /var/lib/docker/volumes/iss_postgres_data

# Application directory usage
du -sh /opt/iss-portal
```

### Monitor Logs

```bash
# Real-time application logs
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100 web

# All services
docker-compose logs -f

# Filter by time
docker-compose logs --since 2h web  # Last 2 hours
docker-compose logs --since "2026-01-21T10:00:00"
```

### Health Checks

```bash
# Container health
docker-compose ps

# Database connectivity
docker-compose exec db pg_isready -U iss_user

# Web application response
curl -I http://localhost/admin/login/

# Check all services
./status.sh
```

### Storage Management

**Database grows automatically** - Docker volumes expand dynamically up to host disk limits.

**No manual expansion needed** - Just monitor host disk space.

**If host runs low on space:**
1. Add more disk to host system, OR
2. Migrate to larger server (see Backup & Restore section)

**Set up disk alerts (optional):**
```bash
# Simple disk space check script
cat > /opt/iss-portal/check-disk.sh << 'EOF'
#!/bin/bash
USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $USAGE -gt 85 ]; then
    echo "WARNING: Disk usage at ${USAGE}%"
    # Send email, log to system, etc.
fi
EOF

chmod +x /opt/iss-portal/check-disk.sh

# Add to crontab (run hourly)
(crontab -l 2>/dev/null; echo "0 * * * * /opt/iss-portal/check-disk.sh") | crontab -
```

### Performance Monitoring

```bash
# Container resource usage
docker stats

# Database connections
docker-compose exec db psql -U iss_user -d iss_portal_db -c \
  "SELECT count(*) FROM pg_stat_activity;"

# Database query performance
docker-compose exec db psql -U iss_user -d iss_portal_db -c \
  "SELECT pid, now() - query_start as duration, query 
   FROM pg_stat_activity 
   WHERE state = 'active' 
   ORDER BY duration DESC;"
```

---

## Upgrades

### Safe Upgrade Process

The upgrade script handles the entire process safely:

```bash
# 1. Navigate to new version directory
cd /opt/iss-portal-v1.1.0

# 2. Copy .env from previous version
cp /opt/iss-portal-v1.0.0/.env .

# 3. Run upgrade script
./upgrade.sh
```

**The script automatically:**
1. Creates backup (database + configuration)
2. Stops application services (keeps database running)
3. Builds new version
4. Runs database migrations
5. Collects new static files
6. Restarts with new version

### Manual Upgrade Steps

If you prefer manual control:

```bash
# 1. Backup
cd /opt/iss-portal
./backup.sh

# 2. Extract new version
cd /opt
sudo tar -xzf iss-portal-v1.1.0.tar.gz
cd iss-portal-v1.1.0

# 3. Copy configuration
cp /opt/iss-portal/.env .

# 4. Stop old version
cd /opt/iss-portal
docker-compose stop

# 5. Build and migrate new version
cd /opt/iss-portal-v1.1.0
docker-compose build
docker-compose run --rm web python manage.py migrate
docker-compose run --rm web python manage.py collectstatic --noinput

# 6. Start new version
docker-compose up -d

# 7. Verify
./status.sh
```

### Migration Safety

Django migrations are **designed for zero-downtime upgrades:**
- Additive changes (new fields, tables) are automatically safe
- Migrations run **before** new code deploys
- Database remains compatible with old version during migration
- Old data is never lost

### Rollback Procedure

If upgrade fails:

```bash
# 1. Stop new version
cd /opt/iss-portal-v1.1.0
docker-compose down

# 2. Restore database from backup
cd /opt/iss-portal
gunzip -c backups/db_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T db psql -U iss_user -d iss_portal_db

# 3. Restart old version
docker-compose up -d
```

---

## Backup & Restore

### Automated Backups

```bash
# Manual backup
./backup.sh

# Schedule automated backups (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/iss-portal && ./backup.sh >> /var/log/iss-portal-backup.log 2>&1") | crontab -
```

**Backup includes:**
- PostgreSQL database dump (compressed)
- .env configuration file
- Media files (if any uploaded)
- Backup manifest with restore instructions

**Retention:** 30 days by default (configurable in backup.sh)

**Storage location:** `/opt/iss-portal/backups/`

### Restore from Backup

```bash
# 1. Ensure database is running
docker-compose up -d db

# 2. Restore database
gunzip -c backups/db_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T db psql -U iss_user -d iss_portal_db

# 3. Restore .env (if needed)
cp backups/.env_YYYYMMDD_HHMMSS .env

# 4. Restore media files (if backup exists)
tar -xzf backups/media_YYYYMMDD_HHMMSS.tar.gz

# 5. Start application
docker-compose up -d
```

### Off-Site Backup Strategy

**Critical:** Store backups in secure, off-site location

**Options:**
```bash
# 1. Copy to remote server via rsync
rsync -avz backups/ user@backup-server:/backups/iss-portal/

# 2. Upload to cloud storage (example with AWS S3)
aws s3 sync backups/ s3://your-bucket/iss-portal-backups/

# 3. Copy to mounted network drive
cp -r backups/* /mnt/backup-drive/iss-portal/
```

**Automated off-site backup:**
```bash
# Add to backup.sh or create separate script
cat > /opt/iss-portal/offsite-backup.sh << 'EOF'
#!/bin/bash
cd /opt/iss-portal
./backup.sh
rsync -avz --delete backups/ user@backup-server:/backups/iss-portal/
EOF

chmod +x /opt/iss-portal/offsite-backup.sh

# Schedule (daily at 3 AM, after local backup)
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/iss-portal/offsite-backup.sh") | crontab -
```

### Encryption Key Backup

**CRITICAL:** The encryption key in .env MUST be backed up securely.

- Without the key, **encrypted data cannot be recovered**
- Store key separately from database backups
- Use password manager or secure vault
- Never commit to version control

---

## Troubleshooting

### Containers Won't Start

```bash
# Check Docker service
sudo systemctl status docker

# Check logs
docker-compose logs

# Check disk space
df -h

# Restart Docker
sudo systemctl restart docker
docker-compose up -d
```

### Database Connection Errors

```bash
# Check database container
docker-compose ps db

# Check database logs
docker-compose logs db

# Test database connection
docker-compose exec db psql -U iss_user -d iss_portal_db -c "SELECT 1;"

# Restart database
docker-compose restart db
```

### Application Errors

```bash
# Check application logs
docker-compose logs --tail=100 web

# Check migrations status
docker-compose exec web python manage.py showmigrations

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Restart application
docker-compose restart web
```

### Encryption Key Issues

**Error:** "FIELD_ENCRYPTION_KEY is not set"

**Solution:**
```bash
# Check .env file
cat .env | grep FIELD_ENCRYPTION_KEY

# If missing, add encryption key (use backup key!)
echo "FIELD_ENCRYPTION_KEY=your-backed-up-key-here" >> .env

# Restart
docker-compose restart web
```

### Port Conflicts

**Error:** "Port 80 is already in use"

**Solution:**
```bash
# Find what's using the port
sudo lsof -i :80

# Stop conflicting service
sudo systemctl stop apache2  # or nginx, etc.

# Or change port in docker-compose.yml
# ports:
#   - "8080:80"  # Use port 8080 instead
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Check database performance
docker-compose exec db psql -U iss_user -d iss_portal_db -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Increase worker processes (edit docker-compose.yml)
# command: gunicorn --workers 8 ...

# Restart with new config
docker-compose up -d
```

### Getting Help

1. Check logs: `docker-compose logs -f web`
2. Check status: `./status.sh`
3. Review this documentation
4. Check Docker and Docker Compose versions
5. Verify .env configuration
6. Ensure adequate disk space and resources

---

## Production Security Checklist

Before going live:

- [ ] Set `DEBUG=False` in .env
- [ ] Configure proper `ALLOWED_HOSTS` in .env
- [ ] Set strong `SECRET_KEY` (50+ random characters)
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Backup encryption key securely
- [ ] Configure SSL/HTTPS (see nginx configuration)
- [ ] Set up automated backups
- [ ] Configure off-site backup storage
- [ ] Test backup restore procedure
- [ ] Set up monitoring/alerts for disk space
- [ ] Document admin credentials securely
- [ ] Review user access permissions
- [ ] Enable firewall (allow only 22, 80, 443)
- [ ] Keep system updated (`apt update && apt upgrade`)

---

## Quick Reference

### Essential Files
- `.env` - Environment configuration (NEVER commit to git)
- `docker-compose.yml` - Container orchestration
- `deploy.sh` - Initial deployment script
- `upgrade.sh` - Upgrade script
- `backup.sh` - Backup script
- `iss-portal.service` - Systemd service file

### Essential Commands
```bash
# Start
./start.sh

# Stop
./stop.sh

# Status
./status.sh

# Backup
./backup.sh

# Logs
docker-compose logs -f web

# Django shell
docker-compose exec web python manage.py shell
```

### Important Locations
- Application: `/opt/iss-portal/`
- Backups: `/opt/iss-portal/backups/`
- Database volume: `/var/lib/docker/volumes/iss_postgres_data/`
- Logs: `docker-compose logs`

---

## Support & Documentation

For additional help:
- Review application logs: `docker-compose logs -f web`
- Check container status: `docker-compose ps`
- Review PROJECT_STATUS.md for development context (if available)
cd iss_portal

# Copy application files
# (Use git clone, rsync, or scp)

# Create .env file
cp .env.example .env
nano .env
```

#### 3. Environment Configuration

Edit `.env` with production values:

```env
# Django Settings
SECRET_KEY=<generate-strong-key>
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
POSTGRES_DB=iss_portal_prod
POSTGRES_USER=iss_prod_user
POSTGRES_PASSWORD=<strong-password>
DATABASE_URL=postgresql://iss_prod_user:<strong-password>@db:5432/iss_portal_prod

# Timezone
TZ=America/New_York
```

#### 4. SSL Certificate Setup

**Option A: Let's Encrypt (Recommended)**

```bash
# Uncomment certbot service in docker-compose.yml

# Update nginx config with your domain
nano nginx/conf.d/default.conf

# Start services
docker-compose up -d

# Obtain certificate
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d your-domain.com \
  -d www.your-domain.com \
  --email admin@your-domain.com \
  --agree-tos \
  --no-eff-email

# Restart nginx
docker-compose restart nginx
```

**Option B: Self-Signed Certificate**

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/cert.key \
  -out nginx/ssl/cert.crt \
  -subj "/C=CA/ST=Ontario/L=Toronto/O=ISS/CN=your-domain.com"
```

#### 5. Initial Deployment

```bash
# Build and start services
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Verify services are running
docker-compose ps

# Create initial data and admin user
docker-compose exec web python manage.py create_initial_data
```

#### 6. Verify Deployment

- [ ] Access https://your-domain.com
- [ ] Login to admin panel
- [ ] Test user creation
- [ ] Test visit logging
- [ ] Verify reports generation
- [ ] Check audit logs

### Post-Deployment

#### Set Up Backups

**Database Backup Script** (`/opt/iss_portal/backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="/opt/iss_portal/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T db pg_dump -U iss_prod_user iss_portal_prod > \
  $BACKUP_DIR/db_backup_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz media/

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Add to crontab** (`crontab -e`):

```cron
# Daily backup at 2 AM
0 2 * * * /opt/iss_portal/backup.sh >> /var/log/iss_backup.log 2>&1
```

#### Monitoring

**Health Check Script** (`/opt/iss_portal/healthcheck.sh`):

```bash
#!/bin/bash

# Check if services are running
if ! docker-compose ps | grep -q "web.*Up"; then
    echo "Web service is down!" | mail -s "ISS Portal Alert" admin@example.com
    docker-compose restart web
fi

if ! docker-compose ps | grep -q "db.*Up"; then
    echo "Database service is down!" | mail -s "ISS Portal Alert" admin@example.com
    docker-compose restart db
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Disk usage is at ${DISK_USAGE}%" | mail -s "ISS Portal Disk Alert" admin@example.com
fi
```

**Add to crontab**:

```cron
# Health check every 15 minutes
*/15 * * * * /opt/iss_portal/healthcheck.sh
```

### Scaling for Production

#### Horizontal Scaling

```bash
# Scale web workers
docker-compose up -d --scale web=3

# Nginx automatically load balances
```

#### External Database

Update `.env`:

```env
DATABASE_URL=postgresql://user:pass@external-db-host:5432/dbname
```

Update `docker-compose.yml`:

```yaml
services:
  web:
    # ... existing config
    # Remove: depends_on: db
    
  # Comment out or remove db service
```

### Maintenance

#### Update Application

```bash
cd /opt/iss_portal

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

#### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f nginx
docker-compose logs -f db

# Last 100 lines
docker-compose logs --tail=100 web
```

#### Database Maintenance

```bash
# Access database shell
docker-compose exec db psql -U iss_prod_user -d iss_portal_prod

# Run VACUUM
docker-compose exec db psql -U iss_prod_user -d iss_portal_prod -c "VACUUM ANALYZE;"

# Check database size
docker-compose exec db psql -U iss_prod_user -d iss_portal_prod -c "\l+"
```

#### Restore from Backup

```bash
# Stop web service
docker-compose stop web

# Restore database
docker-compose exec -T db psql -U iss_prod_user -d iss_portal_prod < backups/db_backup_20260119_020000.sql

# Restore media files
tar -xzf backups/media_backup_20260119_020000.tar.gz

# Restart services
docker-compose start web
```

### Troubleshooting

#### Service Won't Start

```bash
# Check logs
docker-compose logs web

# Check config
docker-compose config

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

#### Database Connection Issues

```bash
# Test connection
docker-compose exec web python manage.py dbshell

# Check environment variables
docker-compose exec web env | grep DATABASE

# Restart database
docker-compose restart db
```

#### Nginx 502 Bad Gateway

```bash
# Check web service is running
docker-compose ps web

# Check web service logs
docker-compose logs web

# Test nginx config
docker-compose exec nginx nginx -t

# Restart nginx
docker-compose restart nginx
```

#### Certificate Renewal Issues

```bash
# Manual renewal
docker-compose run --rm certbot renew

# Check renewal logs
docker-compose logs certbot

# Force renewal (if needed)
docker-compose run --rm certbot renew --force-renewal
```

### Security Hardening

#### Firewall Configuration

```bash
# Enable UFW
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

#### Limit Database Access

In `docker-compose.yml`, remove database port exposure:

```yaml
db:
  # Remove or comment out:
  # ports:
  #   - "5432:5432"
```

#### Regular Updates

```bash
# Update Docker images
docker-compose pull

# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
docker-compose exec web pip install --upgrade -r requirements.txt
```

### Performance Optimization

#### Gunicorn Workers

In `docker-compose.yml`, adjust workers:

```yaml
web:
  command: gunicorn --bind 0.0.0.0:8000 --workers 8 --threads 2 ...
```

Formula: `(2 x CPU_cores) + 1`

#### PostgreSQL Tuning

Create `postgresql.conf` and mount it:

```ini
# Basic tuning for 4GB RAM server
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Support and Monitoring

#### Log Aggregation

Consider setting up:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana + Prometheus
- CloudWatch (if on AWS)

#### Alerting

Set up alerts for:
- Service downtime
- High disk usage (>80%)
- High memory usage (>90%)
- Failed backup jobs
- Certificate expiration (30 days before)

### Compliance

#### Audit Log Review

```bash
# Access audit logs via admin panel
https://your-domain.com/admin/audit/auditlog/

# Export audit logs
docker-compose exec web python manage.py dumpdata audit.AuditLog > audit_export.json
```

#### Data Retention

Configure data retention policies based on organizational requirements.

---

## Production Environment Variables

Complete `.env` template for production:

```env
# Django Core
SECRET_KEY=<64-char-random-string>
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-ip-address

# Database
POSTGRES_DB=iss_portal_prod
POSTGRES_USER=iss_prod_user
POSTGRES_PASSWORD=<strong-password-here>
DATABASE_URL=postgresql://iss_prod_user:<strong-password-here>@db:5432/iss_portal_prod

# Timezone
TZ=America/New_York

# Email (for future notifications)
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_HOST_USER=noreply@your-domain.com
# EMAIL_HOST_PASSWORD=<email-password>
# EMAIL_USE_TLS=True
# DEFAULT_FROM_EMAIL=ISS Portal <noreply@your-domain.com>

# Future SSO
# AZURE_AD_CLIENT_ID=
# AZURE_AD_CLIENT_SECRET=
# AZURE_AD_TENANT_ID=
```

---

For additional support, consult the main README.md or contact your system administrator.
