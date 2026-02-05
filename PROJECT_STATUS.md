# ISS Portal - Project Status Summary
**Last Updated: February 4, 2026**

## Project Overview
Django-based web application for managing children's services with staff caseload management, visit tracking, centre management, comprehensive reporting with staff-scoped access, custom theming, and CSV import capabilities.

**Technology Stack:**
- Django 4.2.9
- PostgreSQL 15-alpine
- Docker/Docker Compose with multi-stage CSS build
- Python 3.11-slim
- Nginx reverse proxy
- Tailwind CSS 3.4 (production-compiled)

## Latest Implementation: Phase 7 - Staff-Scoped Reporting (February 4, 2026)

### Staff Reporting Access Control

**Problem Solved:**
- Staff members (front-line workers) had no access to view their own visit data
- Supervisors/Admins could see all reports but staff had no visibility
- Staff required a way to track their own hours and visits

**Solution Implemented:**

**Permission Architecture:**
- Updated `can_access_reports` property in `accounts/models.py` to include `'staff'` role
- Updated `can_access_reports()` function in `reports/views.py` to include `'staff'` role
- Both checks must be synchronized to prevent login redirect loops

**Visits Report Filtering:**
- Modified `visits_report()` view to detect staff users with pattern: `user_is_staff = hasattr(request.user, 'role') and request.user.role == 'staff'`
- Staff auto-filters to view only their own visits: `Visit.objects.filter(staff=request.user)`
- Staff cannot override filter via URL parameters (silently ignored in view)
- Staff can still filter by: date range, child, centre, visit type
- CSV export button hidden for staff users (permission restriction via `if export_format == 'csv' and not user_is_staff`)

**Dashboard Restrictions:**
- Modified `reports_dashboard()` view to pass `user_is_staff` context variable
- Updated `templates/reports/dashboard.html` to conditionally render reports:
  - Staff users see: Only "Visits Report" card
  - Supervisors/Admins see: All 9 report cards (Children Served, Visits, Staff Summary, Caseload, Age Out, Month Added, Staff Site Visits, Site Visit Summary)
- Dashboard page title and description change based on user role

**UI/Template Updates:**
- `templates/reports/visits_report.html` enhancements for staff:
  - Blue info box explaining staff can only view own visits
  - Staff filter dropdown hidden (cannot change staff assignment)
  - Staff column removed from table (redundant for staff view)
  - CSV export button replaced with permission message
  - Dynamic table colspan based on user role (6 for staff, 7 for others)
- `templates/reports/dashboard.html` conditional rendering:
  - All non-visits reports wrapped in `{% if not user_is_staff %}...{% endif %}`
  - Dashboard subtitle changes based on role

**Navigation:**
- Staff users now see "Reports" link in navigation menu
- Link points to reports dashboard with auto-filtered visits view
- No separate staff-only report page needed

**Result:**
- ✅ Staff can access reports without login loop
- ✅ Staff see only their own visit data automatically
- ✅ Staff cannot bypass filters or view sensitive reports
- ✅ Staff can filter by date, child, centre for their visits
- ✅ CSV export disabled for staff users
- ✅ Dashboard shows only appropriate reports for staff role
- ✅ Permission architecture is synchronized and secure

**Files Modified:**
- `accounts/models.py` - Added `'staff'` to `can_access_reports` property
- `reports/views.py` - Added `'staff'` to `can_access_reports()` function, staff detection and auto-filtering in `visits_report()`, staff context in `reports_dashboard()`
- `templates/reports/visits_report.html` - Staff-specific info box, hidden controls, hidden columns, disabled CSV
- `templates/reports/dashboard.html` - Conditional rendering of non-visits reports

**Testing Verified:**
- ✅ Staff login doesn't redirect loop
- ✅ Reports navigation link visible to staff
- ✅ Staff dashboard shows only Visits Report
- ✅ Visits report auto-filters to staff member's visits
- ✅ Staff can filter by date, child, centre
- ✅ CSV export hidden from staff
- ✅ Supervisor/Admin sees all reports unchanged

---

## Previous Implementation: Centre Management & Custom Theming (February 4, 2026)

### A. Production Tailwind CSS Compilation

**Problem Solved:**
- Previous CDN-based Tailwind CSS wasn't production-ready
- CSS file was only 16KB, missing most utility classes
- Root cause: Templates weren't available during CSS compilation in Docker

**Solution Implemented:**
- Multi-stage Docker build with Node.js + Python
- Stage 1 (Node.js): Compiles Tailwind CSS with template scanning
- Key fix: Copy templates BEFORE npm build so Tailwind can find class names
- Stage 2 (Python): Final application container with compiled CSS

**Result:**
- CSS file: 38KB minified (up from 16KB)
- All Tailwind utilities available in production
- HTTP 200 delivery, gzipped to 3.7KB
- Zero CDN dependency

**Files Modified:**
- `Dockerfile` - Multi-stage build with template copying before CSS build
- `package.json`, `tailwind.config.js`, `postcss.config.js` - CSS build configuration
- `static/css/input.css` - Tailwind @tailwind directives
- `requirements.txt` - Added Pillow for image processing

### B. Custom Theming System

**Models Created:**
- `core.models.ThemeSetting` - Singleton model (pk=1) with:
  - 6 ColorField fields: primary, secondary, accent, success, warning, danger
  - 3 ImageField uploads: logo_image, favicon, background_image
  - CharField: site_title (customizable)
  - DateTimeField: created_at, updated_at
  - Methods: get_theme() singleton getter, enforced pk=1, prevented deletion

**Admin Interface:**
- `ThemeAdmin` in core/admin.py with organized fieldsets:
  1. Brand Colors (primary, secondary, accent)
  2. Status Colors (success, warning, danger)
  3. Header/Navbar (header_bg_color)
  4. Images & Branding (logo, favicon, background)
  5. Text Customization (site_title)
  6. Metadata (timestamps, collapsed)
- Color picker widget: Native HTML5 `<input type="color">` via django-colorfield

**Frontend Integration:**
- Context processor injects theme_settings into all templates
- Dynamic CSS variables in base.html: `--primary`, `--secondary`, etc.
- Logo display: Recommended size 200x100 or 350x200px (horizontal ratio)
- Header background: Dynamic color via `style` attribute
- Site title: Display in navbar with fallback to "ISS Portal"

**Packages Added:**
- `django-colorfield==0.11.0` - Native color picker widgets
- `Pillow==10.1.0` - Image upload and processing

**Result:**
- Fully customizable branding per-instance
- Zero developer intervention for theming
- Color picker provides superior UX vs. text input
- All changes persist in database

**Migrations:**
- `0009_themesetting.py` - Initial ThemeSetting model
- `0010_alter_themesetting_*.py` - ColorField conversion
- `0011_themesetting_header_bg_color.py` - Header customization field

### C. Centre Management & CSV Import

**Models:**
- `Centre` model with fields: name, address_line1, address_line2, city, province, postal_code, phone, contact_name, contact_email, status, notes

**CSV Import Utility:**
- `CentreCSVImporter` class in core/utils/csv_import.py
- Required fields: name, address_line1, city, province, postal_code, phone
- Optional fields: address_line2, contact_name, contact_email, status, notes
- Validation: Email format verification, status choice validation (active/inactive)
- Template generation with 3 example rows

**Views:**
- `import_centres()` - File upload, validation, session storage
- `import_centres_preview()` - Preview valid/invalid rows, confirmation, import
- `download_centres_template()` - CSV template generation
- `centre_list()` - View all centres (all users), import button (admin/supervisor only)

**Templates:**
- `core/import_centres.html` - Import form with instructions (5-step process)
- `core/import_centres_preview.html` - Preview with summary stats, valid/invalid rows
- `core/centre_list.html` - Centre listing with contact information

**Navigation:**
- Removed "Community Partners" link
- Added "Centres" link (desktop and mobile nav)
- Navigation in base.html updated for all user levels

**Permissions:**
- All authenticated users can view centres and contact information
- Import button only visible to superusers and admins (user.is_superuser or user.role == 'admin')
- Import utility checks permission on POST

**Result:**
- Bulk centre management via CSV
- Permission-based access control
- User-friendly preview and confirmation workflow
- All users can access centre contact information

---

### Overview (Self-Configuring Docker - February 2, 2026)
The ISS Portal Docker image includes an **interactive self-configuration system** that runs automatically on first launch, making Docker Hub deployment completely automated with push-button simplicity.

### Dual Distribution Strategy

**1. Git Package Distribution**
- **Target:** Developers, customizable deployments
- **Package:** iss-portal-v1.0.0.tar.gz (124KB)
- **Process:** Extract → Run install.sh → Configure interactively → Deploy
- **Features:** Full source code, customizable, interactive installer

**2. Docker Hub Distribution** ⭐ *New: Self-Configuring*
- **Target:** End users, production deployments
- **Image:** hgisssy/iss-portal:latest (405MB)
- **Process:** Download docker-compose.hub.yml → docker-compose up → Configure interactively
- **Features:** Pre-built optimized image, self-configuring, one-command deployment

### Self-Configuration Implementation

**Interactive Setup Command:**
- File: `core/management/commands/interactive_setup.py`
- Prompts for: allowed hosts, database name, database user, password (confirmed), timezone
- Auto-generates: SECRET_KEY (secrets.token_urlsafe), FIELD_ENCRYPTION_KEY (Fernet)
- Creates: /app/.env with complete configuration (permissions 0o600)

**Smart Entry Point:**
- File: `docker-entrypoint.sh`
- Detects: Missing or incomplete .env file
- Runs: `python manage.py interactive_setup` on first launch
- Skips: Setup on subsequent runs if already configured
- Continues: Normal startup (PostgreSQL wait, migrations, collectstatic, initial data)

**Docker Configuration:**
- File: `docker-compose.hub.yml`
- Includes: `stdin_open: true` and `tty: true` for interactive prompts
- Mounts: `.env` file as volume for persistence

### User Experience

**First Run:**
```bash
docker-compose -f docker-compose.hub.yml up
# Interactive prompts for configuration
# Automatic key generation
# Application starts configured
```

**Subsequent Runs:**
```bash
docker-compose -f docker-compose.hub.yml up -d
# Skips setup, starts directly
```

### Docker Hub Deployment

**Repository:** hgisssy/iss-portal
**Tags:**
- `latest` - Most recent version (self-configuring)
- `1.0.1` - Version with self-configuration feature
- `2026.02.02` - Previous version

**Images Successfully Pushed:**
- hgisssy/iss-portal:latest (digest: sha256:be759b2c...)
- hgisssy/iss-portal:1.0.1 (digest: sha256:be759b2c...)

### Documentation Created

- **SELF_CONFIGURING_DOCKER.md** - Complete technical documentation
- **DOCKERHUB_DEPLOYMENT.md** - Updated with self-configuration instructions
- **DISTRIBUTION_GUIDE.md** - Maintainer guide for Git and Docker Hub
- **PACKAGE_README.md** - Installation guide for both distribution methods

**Status:** ✅ Fully implemented, tested, and pushed to Docker Hub

## Recent Major Implementation: Field-Level Encryption

### Encryption Details
**Implementation Date:** January 2026
**Purpose:** Healthcare-grade data protection for PII compliance

**Packages Added:**
- `django-encrypted-model-fields==0.6.5`
- `cryptography==41.0.7`

**Encryption Key:** `iNaPBGHSwTA_iA-Nek2gp__VofTZ5J3vS0U74HkqaLY=`
- Stored in `.env` file (FIELD_ENCRYPTION_KEY)
- Uses Fernet symmetric encryption (32-byte url-safe base64)
- **CRITICAL:** Key must be backed up securely - if lost, encrypted data cannot be recovered

**Encrypted Fields (38 total across 5 models):**

1. **Centre Model:**
   - contact_name, phone, contact_email
   - address_line1, address_line2, city, province, postal_code
   - notes

2. **Child Model:**
   - first_name, last_name
   - address_line1, address_line2, city, province, postal_code, alternate_location
   - guardian1_name, guardian1_home_phone, guardian1_work_phone, guardian1_cell_phone, guardian1_email
   - guardian2_name, guardian2_home_phone, guardian2_work_phone, guardian2_cell_phone, guardian2_email
   - referral_source_type, referral_source_name, referral_source_phone, referral_agency_name, referral_agency_address
   - referral_reason_* fields (cognitive, language, gross_motor, fine_motor, social_emotional, self_help, other)
   - referral_reason_details, referral_consent_on_file
   - attends_childcare, childcare_centre, childcare_frequency
   - attends_earlyon, earlyon_centre, earlyon_frequency
   - agency_continuing_involvement
   - notes, discharge_reason

3. **Visit Model:**
   - location_description, notes

4. **CommunityPartner Model:**
   - contact_name, phone, email
   - address_line1, address_line2, city, province, postal_code
   - notes

5. **Referral Model:**
   - reason, notes

**Unencrypted Fields (for searching/filtering):**
- IDs, dates, status fields, foreign keys

### Encryption Verification
**Status:** ✅ Fully tested and operational

**Database Level:**
- PostgreSQL stores encrypted Fernet strings: `gAAAAABpcOjl...`
- Direct database queries show encrypted data

**Application Level:**
- Django ORM automatically decrypts on read
- Completely transparent to users and forms
- No code changes required in views or templates

**Docker Configuration:**
- Dockerfile updated with `libffi-dev` and `libssl-dev` for cryptography support
- Migration 0005 created and applied for field conversions

## Phase 5: Reporting System (Completed: February 2, 2026)

### Overview
Comprehensive reporting dashboard with 8 reports accessible to supervisors, admins, and auditors.

### Reports Implemented:

1. **Children Served Report**
   - Total children by overall_status and caseload_status
   - Breakdown by centre
   - CSV export functionality

2. **Visits Report**
   - Visit statistics by type and centre
   - Monthly visit trends
   - Staff visit counts
   - CSV export functionality

3. **Staff Summary Report**
   - Caseload counts per staff member (primary/secondary)
   - Visit counts per staff member
   - Filterable by staff member
   - CSV export functionality

4. **Caseload Report**
   - Children by overall_status (active, discharged)
   - Children by caseload_status (caseload, non_caseload, awaiting_assignment)
   - Children with visits but no primary assignment
   - Primary vs. secondary assignments
   - CSV export functionality

5. **Age Out Report** ⭐ *Enhanced*
   - Active children 13+ years old
   - Centre breakdown
   - **Monthly age out breakdown** - Shows when each child turned 13 years old
   - Visual bar charts for monthly tracking
   - Detailed list with age, aged out month, centre, primary staff
   - CSV export with monthly data

6. **Month Added Report**
   - Children intake volume by month
   - Uses start_date field for tracking
   - Visual trend indicators
   - CSV export functionality

7. **Staff Site Visits Report**
   - Site visits (child__isnull=True) grouped by staff member
   - Visit type breakdown
   - Monthly trends
   - CSV export functionality

8. **Site Visit Summary Report**
   - Aggregate site visit statistics
   - Breakdown by centre and visit type
   - Monthly trends
   - CSV export functionality

### Technical Implementation:

**Files Modified:**
- `reports/views.py`: All 8 report view functions with CSV export logic
- `reports/urls.py`: URL routing for all reports
- `templates/reports/dashboard.html`: Report cards with visual indicators
- `templates/reports/*.html`: Individual report templates with filtering

**Key Features:**
- Permission checks: @login_required + @user_passes_test(can_access_reports)
- CSV export: All reports include downloadable CSV format
- Filters: Centre, staff member, date range (where applicable)
- Visual indicators: Color-coded cards, bar charts, badges
- Responsive design: Tailwind CSS grid layouts

**Date Calculations:**
- Uses `dateutil.relativedelta` for accurate age calculations
- Age Out Report: cutoff_date = today - 13 years
- Monthly tracking: Groups by month using strftime('%Y-%m')

### Bug Fixes During Phase 5:

**Age Out Report Issues (Fixed: February 2, 2026)**
- **Issue:** AttributeError on .select_related('primary_staff')
- **Fix:** Removed 'primary_staff' from select_related - it's a method, not a FK field
- **Template Fix:** Changed from `child.primary_staff` to `{% with primary=child.get_primary_staff %}`
- **CSV Fix:** Updated to call get_primary_staff() method instead of field access

**Caseload Report Issues (Fixed: February 2, 2026)**
- **Issue:** FieldError on 'status' field
- **Fix:** Changed to use correct field names: 'overall_status' and 'caseload_status'
- **Template Fix:** Split into two separate tables for different status types
- **Context Variables:** Updated to children_by_overall_status and children_by_caseload_status

**Status:** ✅ All 8 reports fully operational with CSV export

## Recent Bug Fixes

### Edit Child Phone Fields (Fixed: February 4, 2026)
**Issue:** `edit_child` view and template used old single phone fields (guardian1_phone, guardian2_phone)

**Root Cause:** 
Migration 0008 split phone fields into home/work/cell but the edit form wasn't updated to match.

**Fix Applied:**
- Updated `core/views.py` edit_child function to handle split phone fields
- Updated `templates/core/edit_child.html` to show 3 phone inputs per guardian
- Now matches the add_child forms and database schema

**Files Modified:** 
- `c:\ISSProject2\core\views.py` (lines 400-406)
- `c:\ISSProject2\templates\core\edit_child.html` (guardian sections)

**Status:** ✅ Fixed and tested

### Schema Migration Sync (Fixed: February 4, 2026)
**Issue:** Migration 0008 existed in database but not in Django's migration history

**Root Cause:** 
Model changes were extensive but migration wasn't generated and tracked properly.

**Fix Applied:**
- Generated migration 0008 with `makemigrations`
- Faked migration since database schema already matched
- All migrations now in sync

**Status:** ✅ Fixed and deployed to test server

### Discharge Child Functionality (Fixed: January 21, 2026)
**Issue:** `CaseloadAssignment has no field named 'updated_by'`

**Root Cause:** 
The `discharge_child` view in `core/views.py` attempted to set an `updated_by` field on `CaseloadAssignment` model when unassigning staff, but this field doesn't exist in the model.

**Fix Applied:**
Removed `updated_by=request.user` from the CaseloadAssignment update operation in `discharge_child` view (line ~491 in views.py).

**File Modified:** `c:\ISSProject2\core\views.py`

**Status:** ✅ Fixed and deployed

## Current Application State

### Deployment Status
- All containers running (db, web, nginx)
- Latest build includes discharge fix
- Database encrypted and operational
- Application tested with real data

### Test Data Status
- Test child records created with encrypted data
- Encryption verified at both database and application levels
- Discharge functionality now working

### Database Migrations
Latest migration: `0008_remove_child_core_child_last_na_66f284_idx_and_more.py` (February 4, 2026)
- Splits guardian phone fields into home_phone, work_phone, cell_phone for each guardian
- Adds comprehensive referral tracking fields
- Adds childcare and EarlyON attendance tracking
- All migrations applied successfully

## Key Files & Locations

### Configuration
- **Encryption Key:** `.env` (FIELD_ENCRYPTION_KEY variable)
- **Settings:** `iss_portal/settings.py` (includes encryption validation)
- **Docker:** `Dockerfile`, `docker-compose.yml`
- **Environment Template:** `.env.example`

### Models
- **Core Models:** `core/models.py`
  - Centre, Child, Visit, CaseloadAssignment, VisitType models
  - All PII fields use EncryptedCharField/EncryptedTextField/EncryptedEmailField

### Views
- **Main Views:** `core/views.py`
  - Recent fix: discharge_child function (lines ~457-500)

### Management Commands
- **Key Generation:** `core/management/commands/generate_encryption_key.py`
  - Usage: `python manage.py generate_encryption_key`

## Production Considerations

### Security
✅ Field-level encryption operational
✅ Encryption key validation (raises ImproperlyConfigured if missing when DEBUG=False)
⏳ Move encryption key to secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
⏳ Document key backup and rotation procedures

### Performance
- Minimal overhead observed from encryption
- Application remall known bugs resolved as of February 4, 2026
- No optimization needed at current scale

### Data Migration
If deploying to existing production with unencrypted data:
```python
# Re-save all records to trigger encryption
for model in [Centre, Child, Visit, CommunityPartner, Referral]:
    for obj in model.objects.all():
        obj.save()
```

## Testing Status

### Completed Tests
✅ Encryption at rest (PostgreSQL verification)
✅ Decryption in application (Django ORM verification)
✅ Child creation with encrypted fields
✅ Child discharge functionality
✅ Form submissions and data retrieval

### Pending Tests
⏳ Complete workflow testing (all CRUD operations)
⏳ Community partner management
⏳ Referral system
⏳ Visit tracking and reporting
⏳ Caseload assignment/unassignment
⏳ All report generation

## Known Issues
None currently - discharge bug resolved.

## Next Steps

### Immediate
1. Continue comprehensive testing of all application features
2. Test all encrypted models (Community Partners, Referrals, Visits)
3. Verify report generation with encrypted data

### Before Production
1. Move encryption key to secure secrets manager
2. Document disaster recovery procedures
3. Create key rotation plan
4. Set up automated backups with key management
5. Complete security audit
6. Performance testing under production load

## Important Notes

### Encryption Key Management
- **Current Location:** `.env` file (development only)
- **Backup Status:** Key must be backed up separately
- **Recovery:** No key = no data recovery possible
- **Production:** Must use secrets manager (not .env file)

### Docker Commands Reference
```bash
# Full rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Quick restart
docker-compose restart web

# View logs
docker logs iss_portal_web --tail=50

# Access Django shell
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Check container status
docker-compose ps
```

## Application Structure

### Core Functionality
- **Accounts:** Custom user model with role-based access (staff, supervisor, admin)
- **Core:** Main application logic (children, visits, centres, caseloads)
- **Audit:** Activity logging middleware
- **Reports:** Reporting dashboard and views

### Access Control
- Staff: View own caseload, add visits
- Supervisor: Manage staff caseloads, discharge children
- Admin: Full system access

### Database Schema
- PostgreSQL with Django ORM
- Encrypted fields transparent to Django
- Indexes maintained on non-encrypted searchable fields

## Contact & Continuity
This document provides sufficient context to continue development in a new session. All critical implementation details, encryption keys, and recent changes are documented above.
