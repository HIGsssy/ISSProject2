# ISS Portal - Deployment Guide

## Production Deployment Checklist

### Pre-Deployment

- [ ] **Review Security Settings**
  - Generate strong SECRET_KEY
  - Set DEBUG=False
  - Configure ALLOWED_HOSTS with actual domain
  - Review password policies
  
- [ ] **Database Configuration**
  - Set up managed PostgreSQL instance (optional)
  - Configure backups and retention
  - Test database connection
  
- [ ] **SSL/TLS Certificates**
  - Obtain valid SSL certificate (Let's Encrypt recommended)
  - Configure nginx for HTTPS
  - Test certificate renewal
  
- [ ] **Environment Variables**
  - All sensitive data in .env file
  - .env file not in version control
  - Backup .env securely

### Deployment Steps

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. Application Setup

```bash
# Clone/copy application to server
cd /opt
sudo mkdir iss_portal
sudo chown $USER:$USER iss_portal
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
