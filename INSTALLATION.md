# ISS Portal - Installation Guide

**Quick Start:** Get the ISS Portal running in under 5 minutes using Docker.

---

## Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
- **Docker Compose** (included with Docker Desktop)
- **Git** (optional, for cloning)

---

## Installation Steps

### 1. Get the Code

```bash
git clone <your-repository-url>
cd ISSProject2
```

Or extract the project files to a directory.

### 2. Create Environment File

Copy the example environment file:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### 3. Configure Environment Variables

Edit the `.env` file with your settings:

```ini
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip

# Database
POSTGRES_DB=iss_portal_db
POSTGRES_USER=iss_user
POSTGRES_PASSWORD=change-this-secure-password
DATABASE_URL=postgresql://iss_user:change-this-secure-password@db:5432/iss_portal_db

# Timezone
TZ=America/New_York

# Field Encryption (CRITICAL - See below)
FIELD_ENCRYPTION_KEY=your-generated-encryption-key
```

**Generate Keys:**

```bash
# SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# FIELD_ENCRYPTION_KEY (after first container start)
docker-compose exec web python manage.py generate_encryption_key
```

### 4. Start the Application

```bash
docker-compose up -d --build
```

This will:
- Build the Docker images
- Start PostgreSQL database
- Start Django web application
- Start Nginx reverse proxy
- Run database migrations
- Create initial data (visit types)

### 5. Create Admin User

```bash
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to create your admin account.

### 6. Access the Application

- **Main Application:** http://localhost
- **Admin Interface:** http://localhost/admin
- **API Browser:** http://localhost/api

**Default Credentials** (if using create_initial_data):
- Username: `admin`
- Password: `admin123`

**⚠️ IMPORTANT:** Change the default password immediately in production!

---

## Verification

Check that all containers are running:

```bash
docker-compose ps
```

You should see:
- `iss_portal_db` - Status: Up (healthy)
- `iss_portal_web` - Status: Up (healthy)
- `iss_portal_nginx` - Status: Up

View logs if needed:

```bash
docker-compose logs web
docker-compose logs db
```

---

## Stopping the Application

```bash
# Stop containers (preserves data)
docker-compose down

# Stop and remove all data (CAUTION!)
docker-compose down -v
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs web --tail 50

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Issues

```bash
# Verify database is healthy
docker-compose ps db

# Check database logs
docker-compose logs db
```

### Port Already in Use

If port 80 or 5432 is already in use, edit `docker-compose.yml`:

```yaml
ports:
  - "8080:80"  # Change host port to 8080
```

### Static Files Not Loading

```bash
# Recollect static files
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

### Migration Errors

```bash
# Check migration status
docker-compose exec web python manage.py showmigrations

# Apply migrations manually
docker-compose exec web python manage.py migrate
```

---

## Production Deployment

For production deployments:

1. **Set DEBUG=False** in `.env`
2. **Use strong passwords** for database and admin users
3. **Generate new SECRET_KEY** and **FIELD_ENCRYPTION_KEY**
4. **Configure proper ALLOWED_HOSTS** with your domain
5. **Set up SSL/HTTPS** (configure nginx with SSL certificates)
6. **Backup encryption key** - Store FIELD_ENCRYPTION_KEY securely!
7. **Regular database backups:**

```bash
# Backup
docker-compose exec db pg_dump -U iss_user iss_portal_db > backup.sql

# Restore
docker-compose exec -T db psql -U iss_user iss_portal_db < backup.sql
```

---

## Encryption Key Management

**⚠️ CRITICAL:** The `FIELD_ENCRYPTION_KEY` encrypts all PII data (names, addresses, guardian info, etc.)

- **Never lose this key** - Lost key = unrecoverable data
- **Backup securely** - Store in password manager or secrets vault
- **Don't commit to git** - Already in `.gitignore`
- **Production:** Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)

---

## Quick Reference

### Useful Commands

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f web

# Access Django shell
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic

# Access database
docker-compose exec db psql -U iss_user iss_portal_db

# Restart specific service
docker-compose restart web
```

### Container Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Rebuild specific service
docker-compose build web
docker-compose up -d web

# View resource usage
docker stats
```

---

## System Requirements

**Minimum:**
- 2 GB RAM
- 2 CPU cores
- 10 GB disk space

**Recommended:**
- 4 GB RAM
- 4 CPU cores
- 20 GB disk space
- SSD storage

---

## Development Setup - Tailwind CSS Building

The application now uses production-grade Tailwind CSS with Node.js for CSS compilation. This is handled automatically in Docker, but for development, you can set up local CSS building.

### Local CSS Development Setup (Optional)

If developing locally outside Docker:

**Prerequisites:**
- Node.js 18.0 or higher ([download](https://nodejs.org/))
- npm (included with Node.js)

**Setup:**

1. Install Node.js dependencies:
```bash
npm install
```

2. Build CSS (one-time):
```bash
npm run build:css
```

CSS will be generated to `staticfiles/css/style.css`

3. Watch for changes (during development):
```bash
npm run watch:css
```

The watcher will rebuild CSS whenever you modify `static/css/input.css` or theme colors.

### Using the Theme Rebuild Command

To rebuild CSS after changing theme colors in the admin panel:

```bash
python manage.py rebuild_theme_css
```

Or to watch for changes:

```bash
python manage.py rebuild_theme_css --watch
```

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs web`
2. Review [PROJECT_STATUS.md](PROJECT_STATUS.md) for known issues
3. See [PROJECT_CONTINUATION_GUIDE.md](PROJECT_CONTINUATION_GUIDE.md) for detailed documentation

---

**Version:** 1.1  
**Last Updated:** February 4, 2026  
**Status:** Production Ready - Tailwind CSS Production Build Implemented
