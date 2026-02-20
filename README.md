# Inclusion Support Services Portal

A containerized Django application for managing children's inclusion support services across Child Care Centres.

## Features

- **Role-Based Access Control**: Staff, Supervisor, Admin, and Auditor roles
- **Child Management**: Track children with optional centre associations and non-caseload support
- **Visit Tracking**: Mobile-friendly visit logging with time validation and 7-hour flagging
- **Caseload Management**: Primary and secondary staff assignments with full history
- **Case Notes**: Date-stamped, author-attributed case notes per child; editable by author or supervisor/admin; soft-deleted by supervisor/admin with full audit trail; sortable and searchable
- **Child Record Hub**: Tabbed child detail page with Visits, Case Notes, Intake Details, and Support Plans (coming soon) tabs — accessible to all staff roles
- **Reporting**: Comprehensive reports with role-based access (Staff view own visits, Supervisors/Admins see all reports with CSV export)
  - Children Served by Age Group
  - Monthly Intake Trends
  - Staff Productivity & Caseloads
  - Age Out Reports (13+)
  - **Age Progressions Report** (Phase 9): Track monthly transitions through age categories (Infant→Toddler, etc.) with CSV export
- **Audit Logging**: Complete change tracking for all key entities including case note creation, edits, and soft-deletions
- **Centre Management**: View centre contact information, bulk import via CSV (admin/supervisor only)
- **Custom Theming**: Customizable logo, colors, site title, and header styling via admin interface
- **Production CSS**: Tailwind CSS compiled in production Docker build with full utility classes
- **Containerized Deployment**: Docker and Docker Compose with nginx reverse proxy, self-configuring setup

## Technology Stack

- **Backend**: Python 3.11, Django 4.2, Django REST Framework
- **Database**: PostgreSQL 15
- **Frontend**: Django Templates with Tailwind CSS 3.4 (production-compiled)
- **Styling**: Tailwind CSS with custom color picker interface (django-colorfield)
- **Image Processing**: Pillow for logo and media upload handling
- **Deployment**: Docker, Docker Compose, Nginx, Gunicorn
- **Future**: SSO integration ready (M365/Azure AD)

---

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git (for version control)

### Initial Setup

1. **Clone or navigate to the project directory**:
   ```bash
   cd c:\ISSProject2
   ```

2. **Create environment file**:
   ```bash
   copy .env.example .env
   ```

3. **Edit `.env` file** with your configuration:
   ```
   SECRET_KEY=your-generated-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   POSTGRES_DB=iss_portal_db
   POSTGRES_USER=iss_user
   POSTGRES_PASSWORD=your-secure-password
   DATABASE_URL=postgresql://iss_user:your-secure-password@db:5432/iss_portal_db
   ```

4. **Generate a SECRET_KEY**:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

5. **Build and start containers**:
   ```bash
   docker-compose up -d --build
   ```

6. **The application will**:
   - Wait for PostgreSQL to be ready
   - Run database migrations automatically
   - Collect static files
   - Create initial visit types
   - Prompt for admin user creation (if needed)

7. **Access the application**:
   - Web Interface: http://localhost
   - Django Admin: http://localhost/admin
   - API: http://localhost/api

---

## Development Setup (Without Docker)

For local development without Docker:

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file** for local development:
   ```
   SECRET_KEY=your-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   DATABASE_URL=sqlite:///db.sqlite3
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create initial data**:
   ```bash
   python manage.py create_initial_data
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
   ```

---

## User Roles and Permissions

### Staff (Front-Line Workers)
- View all children
- Maintain "My Caseload" list (primary assignments + visited children)
- Create and edit own visit records
- Add and edit own case notes on any child record
- View intake details for any child (address, guardians, referral source, program attendance)
- View own visits in Reports dashboard (filtered automatically)
- Cannot manage users or reassign caseloads
- Cannot access other reports or override visit filters
- Cannot delete case notes

### Supervisor
- Full read/write access to children, centres, visits
- Add and edit case notes on any child record
- Soft-delete case notes (any user's notes)
- Manage caseload assignments
- Bulk reassign caseloads
- Generate and export reports
- Cannot manage users or SSO settings

### Administrator
- All supervisor permissions
- Manage users and roles
- Access audit logs
- Configure system settings
- Future: Configure SSO settings

### Auditor
- Read-only access to reports and audit logs
- No create, edit, or delete permissions

---

## Key Features

### Child Management

Children can have the following statuses:
- **Active**: Receiving regular services
- **On Hold**: Temporarily not receiving services
- **Discharged**: No longer receiving services
- **Non-Caseload**: Receiving services without formal caseload assignment

Non-caseload children:
- May have no caseload assignments
- May have no centre association
- Can still have visits recorded
- Identified with special badge in UI

### Visit Tracking

Visits include:
- Child, staff member, date, start/end times
- Optional centre (captured as historical snapshot)
- Visit type (Assessment, Regular Visit, Other)
- Location description for non-centre visits
- Notes (including co-visitors)

**Important**: Visits over 7 hours are automatically flagged for review.

### Caseload Management

- Children can have one primary staff member and multiple secondary staff
- Full history preserved (assigned_at, unassigned_at)
- Bulk reassignment capability for supervisors
- "My Caseload" includes primary assignments + visited children

### Audit Logging

All changes are automatically logged:
- Who made the change
- What entity was changed
- When the change occurred
- Field-level old/new values
- Special tracking for visit edits and bulk operations

---

## API Endpoints

### Authentication
All API endpoints require authentication via Django session.

### Core Endpoints

- `GET /api/centres/` - List all centres
- `GET /api/centres/active/` - Active centres only
- `GET /api/children/` - List all children
- `GET /api/children/my-caseload/` - Current user's caseload
- `GET /api/children/non-caseload/` - Non-caseload children
- `GET /api/visit-types/` - Available visit types
- `GET /api/visits/` - List visits
- `POST /api/visits/` - Create visit
- `GET /api/visits/my-visits/` - Current user's visits
- `GET /api/visits/flagged/` - Visits flagged for review
- `GET /api/caseloads/` - Caseload assignments
- `POST /api/caseloads/bulk-reassign/` - Bulk reassign (supervisor+)
- `GET /api/children/<id>/case-notes/` - List case notes for a child
- `POST /api/children/<id>/case-notes/` - Create case note for a child
- `PATCH /api/children/<id>/case-notes/<note_id>/` - Edit a case note
- `DELETE /api/children/<id>/case-notes/<note_id>/` - Soft-delete a case note (supervisor/admin only)

### Reports (Supervisor/Admin/Auditor only)

- `/reports/` - Reports dashboard
- `/reports/visits/` - Visits report with filters and CSV export
- `/reports/staff-summary/` - Staff productivity report
- `/reports/caseload/` - Caseload vs non-caseload breakdown

---

## Docker Commands

### Start services:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f
docker-compose logs -f web  # Web service only
```

### Stop services:
```bash
docker-compose down
```

### Rebuild after code changes:
```bash
docker-compose up -d --build
```

### Run Django management commands:
```bash
docker-compose exec web python manage.py <command>
```

### Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

### Access database:
```bash
docker-compose exec db psql -U iss_user -d iss_portal_db
```

---

## Scaling

### Horizontal Scaling (Multiple Web Workers)

1. **Scale web service**:
   ```bash
   docker-compose up -d --scale web=3
   ```

2. **Nginx will automatically load balance** across all web containers.

### External Database

For production with managed PostgreSQL:

1. Update `.env` with external database URL:
   ```
   DATABASE_URL=postgresql://user:password@external-host:5432/dbname
   ```

2. Remove or comment out the `db` service in `docker-compose.yml`

3. Remove `depends_on: db` from web service

---

## SSL/HTTPS Configuration

### Development (Self-Signed Certificate)

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/cert.key \
  -out nginx/ssl/cert.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

Then uncomment the HTTPS server block in `nginx/conf.d/default.conf`.

### Production (Let's Encrypt)

1. **Update domain** in `nginx/conf.d/default.conf`

2. **Uncomment certbot service** in `docker-compose.yml`

3. **Obtain certificate**:
   ```bash
   docker-compose run --rm certbot certonly --webroot \
     --webroot-path=/var/www/certbot \
     -d your-domain.com \
     --email your-email@example.com \
     --agree-tos
   ```

4. **Restart nginx**:
   ```bash
   docker-compose restart nginx
   ```

Certificates auto-renew every 12 hours via certbot container.

---

## Backup and Restore

See **[BACKUP_RECOVERY.md](BACKUP_RECOVERY.md)** for the full guide.

| Task | Command |
|---|---|
| Manual backup | `./backup.sh` |
| Schedule daily backups (once, after deploy) | `sudo ./setup-cron.sh` |
| Interactive restore | `./restore.sh` |

The backup set includes a compressed PostgreSQL dump, the `.env` file (which contains the encryption key), and any uploaded media files. Backups are retained for 30 days and stored in `backups/`.

---

## Future SSO Integration (M365/Azure AD)

The system is prepared for SSO integration:

1. User model includes `sso_id` field for Azure AD Object ID
2. Install required packages (commented in requirements.txt):
   ```bash
   pip install django-allauth social-auth-app-django
   ```

3. Configure Azure AD application in Azure Portal

4. Update settings with Azure AD credentials

5. Configure authentication backend and URLs

6. Map `sso_id` to Azure AD user during authentication

Detailed SSO setup guide will be provided when implementing this feature.

---

## Troubleshooting

### Database Connection Issues

```bash
docker-compose exec web python manage.py dbshell
```

If this fails, check:
- PostgreSQL container is running: `docker-compose ps`
- Database credentials in `.env`
- Database URL format

### Static Files Not Loading

```bash
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

### Permission Denied Errors

Ensure `docker-entrypoint.sh` is executable:
```bash
chmod +x docker-entrypoint.sh
```

### View Container Logs

```bash
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f nginx
```

---

## Project Structure

```
ISSProject2/
├── iss_portal/           # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/             # Custom user model with roles
│   ├── models.py
│   └── admin.py
├── core/                 # Core business logic
│   ├── models.py        # Child, Centre, Visit, CaseloadAssignment
│   ├── views.py         # Web views
│   ├── viewsets.py      # DRF API viewsets
│   ├── serializers.py   # DRF serializers
│   ├── permissions.py   # Custom permissions
│   ├── admin.py         # Django admin configuration
│   └── management/      # Management commands
├── audit/               # Audit logging system
│   ├── models.py        # AuditLog model
│   ├── middleware.py    # User context middleware
│   └── signals.py       # Automatic change tracking
├── reports/             # Reporting system
│   ├── views.py         # Report views and CSV export
│   └── urls.py
├── templates/           # Django templates with Tailwind CSS
│   ├── base.html
│   ├── login.html
│   └── core/
├── static/              # Static files
│   └── css/
├── nginx/               # Nginx configuration
│   ├── nginx.conf
│   ├── conf.d/
│   └── ssl/
├── Dockerfile           # Django app container
├── docker-compose.yml   # Multi-container orchestration
├── docker-entrypoint.sh # Container startup script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md           # This file
```

---

## Support and Maintenance

### Logs Location

- Application logs: `docker-compose logs web`
- Nginx access/error logs: `docker-compose logs nginx`
- Database logs: `docker-compose logs db`

### Performance Monitoring

Monitor container resource usage:
```bash
docker stats
```

### Database Maintenance

Run VACUUM (PostgreSQL optimization):
```bash
docker-compose exec db psql -U iss_user -d iss_portal_db -c "VACUUM ANALYZE;"
```

---

## Security Considerations

### Production Checklist

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Enable HTTPS with valid certificates
- [ ] Set up database backups (`sudo ./setup-cron.sh` — see [BACKUP_RECOVERY.md](BACKUP_RECOVERY.md))
- [ ] Configure firewall rules
- [ ] Review audit logs regularly
- [ ] Implement password policy
- [ ] Keep dependencies updated

---

## License

Internal use only - Inclusion Support Services.

---

## Contact

For support or questions, contact your system administrator.
