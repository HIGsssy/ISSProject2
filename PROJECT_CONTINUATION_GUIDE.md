# ISS Portal - Project Continuation Guide
**Last Updated:** February 5, 2026  
**Project Status:** Fully Operational - Phase 8 Child Record Redesign Complete

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Recent Major Changes](#recent-major-changes)
4. [Database Schema](#database-schema)
5. [Authentication & Authorization](#authentication--authorization)
6. [Key Features & Functionality](#key-features--functionality)
7. [File Structure & Key Components](#file-structure--key-components)
8. [Status System (Critical - Recently Refactored)](#status-system-critical---recently-refactored)
9. [Signal Handlers & Automation](#signal-handlers--automation)
10. [API Endpoints](#api-endpoints)
11. [Templates & UI](#templates--ui)
12. [Docker Configuration](#docker-configuration)
13. [Custom Theming System](#custom-theming-system)
14. [Centre Management](#centre-management)
15. [Staff-Scoped Reporting (Phase 7)](#staff-scoped-reporting-phase-7)
16. [Child Record Hub & Visit Management (Phase 8)](#child-record-hub--visit-management-phase-8)
17. [Recent Bug Fixes](#recent-bug-fixes)
18. [Testing Checklist](#testing-checklist)
19. [Known Considerations](#known-considerations)
20. [Development Commands](#development-commands)

---

## Project Overview

**ISS Portal** is a Django-based case management system for child welfare services. It manages children's records, staff caseloads, visits, referrals, community partnerships, centre information, and provides customizable theming for multi-tenant deployments.

### Primary Use Cases:
- Child record management with encrypted PII
- Staff caseload assignment and tracking
- Visit logging and reporting (child visits & site visits)
- Referral management to community partners
- Centre management with CSV bulk import
- Custom branding and theming per-instance
- Comprehensive audit logging
- CSV bulk import capabilities (children and centres)
- Role-based access control

---

## Architecture & Technology Stack

### Backend:
- **Django 4.2.9** - Web framework
- **PostgreSQL 15-alpine** - Database with encryption
- **Django REST Framework** - API layer
- **django-encrypted-model-fields** - PII encryption
- **django-colorfield** - Color picker widgets for admin
- **Gunicorn** - WSGI server (4 workers)

### Frontend:
- **Django Templates** - Server-side rendering
- **Tailwind CSS 3.4** - Production-compiled, utility-first styling (38KB minified)
- **Vanilla JavaScript** - Form handling, tab switching, API calls
- **Custom theme system** - Branded colors, logos, and site title

### Infrastructure:
- **Docker & Docker Compose** - Containerization with multi-stage CSS build
- **Node.js 18-alpine** - Tailwind CSS compilation during Docker build
- **Nginx** - Reverse proxy and static file serving
- **Python 3.11-slim** - Base image

### Deployment:
- Multi-stage Docker build: CSS compilation → Python application
- Multi-container setup: web (Django), db (PostgreSQL), nginx
- Environment-based configuration via .env file
- Static files served by Nginx with gzip compression
- Media files stored in persistent volumes

---

## Recent Major Changes

### 1. Child Record Hub & Visit Management System (February 5, 2026)

**Redesigned Child Detail Page as Information Hub:**
- Transformed from traditional single-column detail view to scalable multi-section hub
- **2-Column Header Layout** (60% child info / 40% referral & caseload):
  - Child demographics (name, DOB, age, centre, guardian contact)
  - Referral reasons (badge display)
  - Compact caseload summary with manage button
  - Status badges (overall, caseload, on-hold flags)
  
- **Responsive Tabs Section** (below header):
  - Active "Visits" tab: Shows last 20 visits with link to full history
  - Placeholder "Case Notes" tab: Future feature (disabled, grayed)
  - Placeholder "Support Plans" tab: Future feature (disabled, grayed)
  - JavaScript-based tab switching (ready for future tabs)
  
- **Preserved Full Intake Details** (supervisor/admin only):
  - All existing detailed information maintained below tabs
  - Keeps sensitive data access restricted
  - Address, guardians, referral source, program attendance, consent status

**New Child Visits Page** (`/children/<pk>/visits/`):
- Comprehensive paginated visit history (25 per page)
- Shows all visits for a specific child
- Visit table: Date, Staff, Centre, Type, Duration (with 7+ hr warning), Actions
- Edit/View links for each visit
- Back navigation to child detail
- "Log New Visit" button for quick access

**Visit Management Enhancements:**
- Split visit forms into dedicated child/site visit forms
- Dedicated pages: `/visits/add/` (child), `/visits/add-site/` (site)
- Prominent 2-column form switcher (blue active, gray inactive)
- Centre field restored to child visits with auto-population from child's centre
- Centre field editable for override capability

**Bug Fixes (Phase 8):**
- ✅ Fixed site visit serialization (centre not passed in VisitCreateSerializer)
- ✅ Fixed audit signal to handle both child visits and site visits
- ✅ Fixed template syntax errors (unmatched endif tags)
- ✅ Fixed JSON parsing errors in visit form submission

**Files Created:**
- `templates/core/child_visits.html` - Paginated visit history page

**Files Modified:**
- `core/views.py`:
  - Added `child_visits()` view with Paginator (25 per page)
  - Updated `child_detail()` to calculate and pass `total_visits_count`
  - Queries optimized with `select_related()` for efficiency
  
- `core/urls.py`:
  - Added route: `path('children/<int:pk>/visits/', views.child_visits, name='child_visits')`
  
- `templates/core/child_detail.html`:
  - Complete redesign with 2-column responsive header
  - Tabbed interface below header
  - Tab switching JavaScript
  - Responsive grid layout (2-column desktop, 1-column mobile)
  
- `core/serializers.py`:
  - Added `centre` field to `VisitCreateSerializer`
  - Conditional auto-population from child's centre
  - Allows manual override for site visits
  
- `audit/signals.py`:
  - Updated `audit_visit_changes()` signal to handle both visit types
  - Conditional messaging: Shows child name for child visits, centre name for site visits
  
- `templates/core/add_visit.html`:
  - Simplified to child visits only
  - Removed site visit toggle
  
- `templates/core/add_site_visit.html`:
  - New dedicated site visit form (matching child form UX)
  
- `templates/core/dashboard.html`:
  - Fixed visit display to handle both child and site visits
  - Conditional child link rendering
  - Added "View all visits" link

**Database Queries Optimized:**
- `child_visits()`: `visits.select_related('staff', 'centre', 'visit_type')`
- `child_detail()`: `child.select_related('centre', 'created_by', 'updated_by')`
- Reduces N+1 query problems

**Testing Verified:**
- ✅ Docker build successful (Tailwind compilation clean)
- ✅ Container starts without errors
- ✅ Child detail page loads with new layout (HTTP 200)
- ✅ Child visits page paginates correctly
- ✅ Tab switching works (JavaScript functional)
- ✅ Responsive design works (2-column → 1-column on mobile)
- ✅ Site visit logging works (separate form)
- ✅ Audit trail captures both visit types correctly
- ✅ All links functional (edit, view, manage caseload)

**Design Philosophy:**
- Hub-based architecture allows future expansion
- Case Notes tab ready for implementation
- Support Plans tab ready for implementation
- Full intake details preserved for data-intensive users
- Mobile-first responsive design
- Maintains existing permissions and access control

### 2. Production Tailwind CSS & Theming System (February 4, 2026)**Migrations:**
- `0009_themesetting.py` - ThemeSetting model
- `0010_alter_themesetting_*.py` - ColorField conversion
- `0011_themesetting_header_bg_color.py` - Header background

### 2. Centre Management & CSV Import (February 4, 2026)

**Centre Model:**
- Fields: name, address_line1, address_line2, city, province, postal_code, phone, contact_name, contact_email, status, notes
- All encrypted for PII protection
- Status choices: active, inactive

**CSV Import Utility:**
- `CentreCSVImporter` class in core/utils/csv_import.py (200 lines)
- Required fields: name, address_line1, city, province, postal_code, phone
- Optional fields: address_line2, contact_name, contact_email, status, notes
- Validation: Email format, status choices, required fields
- Template generation with 3 example rows

**Views & Templates:**
- `import_centres()` - Upload and validate CSV
- `import_centres_preview()` - Preview valid/invalid rows
- `download_centres_template()` - Download example CSV
- `centre_list()` - View all centres (all users)
- Templates: import_centres.html, import_centres_preview.html, centre_list.html

**Navigation:**
- Added "Centres" link to main navigation (desktop and mobile)
- Removed "Community Partners" link
- All users can view centre contact information
- Import button visible only to superusers/admins

**Permissions:**
- Centre list: viewable by all authenticated users
- Import functionality: superuser or role == 'admin' only

### 3. Status System Restructuring (Completed January 23, 2026)

**Previous System:** Single `status` field with values: active, on_hold, discharged, non_caseload

**New System:** Three separate fields:
1. **overall_status**: `active` or `discharged`
2. **caseload_status**: `caseload`, `non_caseload`, or `awaiting_assignment`
3. **on_hold**: Boolean flag for temporarily paused children

**Why This Change:**
- Clearer separation of concerns
- Better tracking of assignment status
- On-hold can apply to both active and caseload children
- CSV imports now default to "awaiting_assignment"
- Auto-updates when staff assignments change

**Files Modified:**
- `core/models.py` - Added 3 new fields, removed old status field
- `core/migrations/0006_restructure_child_status.py` - Data migration
- `core/views.py` - All views updated (15+ views)
- `core/serializers.py` - API serializers updated
- `core/viewsets.py` - ViewSet filters updated
- `core/admin.py` - Admin interface updated
- `core/utils/csv_import.py` - CSV import logic updated
- `static/css/custom.css` - New badge styles
- All 8 templates in `templates/core/` updated

### 4. CSV Bulk Import Feature (Completed)
- Upload CSV files to bulk create child records
- Preview before import with validation
- Error reporting for invalid data
- Defaults: overall_status='active', caseload_status='awaiting_assignment'

### 3. Visit Logging Bug Fix (Completed)
- Fixed issue where staff could see ALL children in visit dropdown
- Now staff only see their active caseload children
- Supervisors/admins see all active children

### 4. Discharge Permissions Update (Completed)
- Staff members can now discharge children (previously supervisors/admins only)
- Discharge sets: overall_status='discharged', caseload_status='non_caseload', on_hold=False

### 5. CSS Badge Styling Fix (Completed January 23, 2026)
- Fixed issue where status badges showed as black text on white background
- Root cause: Tailwind CSS overriding custom badge colors
- Solution: Added `!important` flags to all badge CSS classes
- All status badges now display with correct colors

### 6. Visit Centre Pre-selection (Completed January 23, 2026)
- When logging a visit from a child's page, the centre field now defaults to the child's assigned centre
- Improves user experience and reduces data entry errors
- Changes in `core/views.py` (add_visit) and `templates/core/add_visit.html`

---

## Database Schema

### Core Models

#### Child (core/models.py)
```python
# Primary Fields
first_name = EncryptedCharField(max_length=100)
last_name = EncryptedCharField(max_length=100)
date_of_birth = EncryptedDateField()

# Status Fields (NEW - 3-field system)
overall_status = CharField(choices=[('active', 'Active'), ('discharged', 'Discharged')], default='active')
caseload_status = CharField(choices=[('caseload', 'Caseload'), ('non_caseload', 'Non-Caseload'), ('awaiting_assignment', 'Awaiting Assignment')], default='awaiting_assignment')
on_hold = BooleanField(default=False)

# Encrypted PII Fields
address_line1 = EncryptedCharField(max_length=200, blank=True)
city = EncryptedCharField(max_length=100, blank=True)
postal_code = EncryptedCharField(max_length=10, blank=True)
guardian1_name = EncryptedCharField(max_length=200, blank=True)
guardian1_phone = EncryptedCharField(max_length=20, blank=True)
guardian1_email = EncryptedEmailField(blank=True)
guardian2_name = EncryptedCharField(max_length=200, blank=True)
guardian2_phone = EncryptedCharField(max_length=20, blank=True)
guardian2_email = EncryptedEmailField(blank=True)

# Other Fields
centre = ForeignKey(Centre, on_delete=SET_NULL, null=True, blank=True)
start_date = DateField()
end_date = DateField(null=True, blank=True)
discharge_reason = TextField(blank=True)
notes = TextField(blank=True)

# Helper Properties
@property
def is_active(self) -> bool: return self.overall_status == 'active'
@property
def is_discharged(self) -> bool: return self.overall_status == 'discharged'
@property
def is_in_caseload(self) -> bool: return self.caseload_status == 'caseload'
@property
def is_non_caseload(self) -> bool: return self.caseload_status == 'non_caseload'
@property
def is_awaiting_assignment(self) -> bool: return self.caseload_status == 'awaiting_assignment'

# Indexes (for performance)
indexes = [
    Index(fields=['overall_status']),
    Index(fields=['caseload_status']),
    Index(fields=['on_hold']),
    Index(fields=['last_name', 'first_name']),
]
```

#### CaseloadAssignment
```python
child = ForeignKey(Child, on_delete=CASCADE, related_name='caseload_assignments')
staff = ForeignKey(User, on_delete=CASCADE, related_name='caseload_assignments')
is_primary = BooleanField(default=True)
assigned_at = DateTimeField(auto_now_add=True)
unassigned_at = DateTimeField(null=True, blank=True)
notes = TextField(blank=True)
```

#### Visit
```python
child = ForeignKey(Child, on_delete=CASCADE, related_name='visits')
staff = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='visits')
centre = ForeignKey(Centre, on_delete=SET_NULL, null=True, blank=True)
visit_date = DateField()
start_time = TimeField(null=True, blank=True)
end_time = TimeField(null=True, blank=True)
visit_type = ForeignKey(VisitType, on_delete=SET_NULL, null=True)
location = CharField(max_length=200, blank=True)
notes = TextField(blank=True)
created_at = DateTimeField(auto_now_add=True)
updated_at = DateTimeField(auto_now=True)
```

#### Referral
```python
child = ForeignKey(Child, on_delete=CASCADE, related_name='referrals')
community_partner = ForeignKey(CommunityPartner, on_delete=SET_NULL, null=True)
referred_by = ForeignKey(User, on_delete=SET_NULL, null=True)
referral_date = DateField()
status = CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined'), ('completed', 'Completed')], default='pending')
reason = TextField()
outcome = TextField(blank=True)
outcome_date = DateField(null=True, blank=True)
```

#### AuditLog (audit/models.py)
```python
user = ForeignKey(User, on_delete=SET_NULL, null=True)
action = CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete'), ('view', 'View')])
model_name = CharField(max_length=100)
object_id = IntegerField()
object_repr = CharField(max_length=200)
changes = JSONField(default=dict)
ip_address = GenericIPAddressField(null=True, blank=True)
user_agent = TextField(blank=True)
timestamp = DateTimeField(auto_now_add=True)
```

---

## Authentication & Authorization

### User Roles (accounts/models.py)
```python
ROLE_CHOICES = [
    ('staff', 'Staff'),
    ('supervisor', 'Supervisor'),
    ('admin', 'Admin'),
]
```

### Permissions Matrix

| Action | Staff | Supervisor | Admin |
|--------|-------|------------|-------|
| View own caseload | ✅ | ✅ | ✅ |
| View all children | ❌ | ✅ | ✅ |
| Add child | ✅ | ✅ | ✅ |
| Edit child | ✅ (assigned) | ✅ (all) | ✅ (all) |
| Discharge child | ✅ | ✅ | ✅ |
| Change caseload_status | ❌ | ✅ | ✅ |
| Manage assignments | ❌ | ✅ | ✅ |
| Log visit (own caseload) | ✅ | ✅ | ✅ |
| Log visit (any child) | ❌ | ✅ | ✅ |
| Edit own visits | ✅ | ✅ | ✅ |
| Edit any visit | ❌ | ✅ | ✅ |
| View reports | ✅ (limited) | ✅ (all) | ✅ (all) |
| CSV import | ❌ | ✅ | ✅ |

### Default Credentials
- Username: `admin`
- Password: `admin123`
- Role: Admin (superuser)

---

## Key Features & Functionality

### 1. Child Management
- **Create:** Form-based or CSV bulk import
- **Update:** Edit personal info, address, guardians
- **Status Management:** Three-field system (overall, caseload, on_hold)
- **Discharge:** Set end date, reason, auto-update all status fields
- **Encryption:** All PII encrypted at rest using django-encrypted-model-fields

### 2. Caseload Management
- **Assignment:** Primary and secondary staff assignments
- **Auto-Status Update:** Signals automatically update caseload_status when assignments change
- **Filters:** View by primary/secondary caseload
- **Bulk Operations:** Manage multiple assignments via admin interface

### 3. Visit Logging
- **Quick Access:** "Log Visit" buttons throughout UI
- **Role-Based Filtering:** Staff see only their caseload, supervisors see all
- **Fields:** Date, time range, type, location, notes
- **Visit Types:** Assessment, Regular Visit, Other (configurable)

### 4. Referral Management
- **Community Partners:** Organizations receiving referrals
- **Status Tracking:** Pending, Accepted, Declined, Completed
- **Outcome Recording:** Notes and completion dates
- **Filtering:** By child or status

### 5. CSV Import
- **Location:** Dashboard → "Import Children" button (supervisors/admins only)
- **Process:** Upload → Preview with validation → Confirm import
- **Required Fields:** first_name, last_name, date_of_birth
- **Optional Fields:** All address/guardian fields, notes, on_hold

### 6. Reporting System (Phase 5 - Completed February 2, 2026)
- **Access:** Supervisors, Admins, and Auditors only
- **Location:** Dashboard → "Reports" section with 8 report cards
- **Reports Available:**
  1. **Children Served** - Status and centre breakdowns
  2. **Visits** - Visit statistics and trends
  3. **Staff Summary** - Caseload and visit counts per staff
  4. **Caseload** - Assignment statistics by status type
  5. **Age Out** - Children 13+ with monthly aging-out breakdown
  6. **Month Added** - Intake volume by month
  7. **Staff Site Visits** - Site visit tracking by staff
  8. **Site Visit Summary** - Aggregate site visit statistics
- **Features:** All reports include CSV export, filters, and visual indicators
- **Key Functions:**
  - `age_out_report()`: Calculates when each child turned 13, groups by month
  - `month_added_report()`: Tracks intake trends using start_date
  - `staff_site_visits_report()`: Groups site visits (child__isnull=True) by staff
  - Permission checks via `can_access_reports()` decorator
- **Defaults:** overall_status='active', caseload_status='awaiting_assignment'
- **Template Download:** System generates CSV template

### 6. Audit Logging
- **Automatic:** All Create/Update/Delete operations logged via signals
- **Captures:** User, timestamp, IP, changes (before/after)
- **Middleware:** Tracks current user and IP for all requests

---

## File Structure & Key Components

```
ISSProject2/
├── accounts/                    # User authentication & roles
│   ├── models.py               # Custom User model with role field
│   ├── admin.py                # User admin interface
│   └── migrations/
│
├── audit/                       # Audit logging system
│   ├── models.py               # AuditLog model
│   ├── middleware.py           # Request context tracking
│   ├── signals.py              # Auto-logging signals
│   └── admin.py                # Audit log viewer
│
├── core/                        # Main application logic
│   ├── models.py               # Child, Visit, Referral, Centre, etc.
│   ├── views.py                # All view functions (15+ views)
│   ├── serializers.py          # DRF serializers for API
│   ├── viewsets.py             # DRF viewsets for API
│   ├── permissions.py          # Custom DRF permissions
│   ├── signals.py              # Auto-update caseload_status
│   ├── admin.py                # Admin interface customizations
│   ├── urls.py                 # URL routing
│   ├── api_urls.py             # API URL routing
│   ├── utils/
│   │   └── csv_import.py       # CSV import logic
│   └── migrations/
│       └── 0006_restructure_child_status.py  # Critical migration
│
├── iss_portal/                  # Project settings
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   └── wsgi.py                 # WSGI application
│
├── reports/                     # Reporting module
│   ├── views.py                # Report generation
│   └── templates/reports/      # Report templates
│
├── templates/                   # HTML templates
│   ├── base.html               # Base template with navigation
│   ├── login.html              # Login page
│   └── core/
│       ├── dashboard.html      # Main dashboard
│       ├── all_children.html   # Filterable children list
│       ├── child_detail.html   # Child detail view
│       ├── edit_child.html     # Edit child form
│       ├── add_child.html      # Add child form
│       ├── my_caseload.html    # Staff caseload view
│       ├── add_visit.html      # Visit logging form
│       ├── edit_visit.html     # Edit visit form
│       ├── discharge_child.html # Discharge workflow
│       ├── non_caseload_children.html
│       ├── manage_caseload.html
│       ├── import_children.html
│       └── import_children_preview.html
│
├── static/
│   └── css/
│       └── custom.css          # Custom styles (status badges)
│
├── docker-compose.yml           # Multi-container orchestration
├── Dockerfile                   # Django app container
├── requirements.txt             # Python dependencies
├── manage.py                    # Django management script
├── .env                         # Environment variables
└── nginx/
    └── nginx.conf              # Nginx configuration
```

---

## Status System (Critical - Recently Refactored)

### Three-Field Status System

#### 1. Overall Status (`overall_status`)
**Purpose:** Indicates if child is actively receiving services

**Values:**
- `active` - Child is currently receiving services
- `discharged` - Child has been discharged from services

**UI Display:** Green badge (Active) or Gray badge (Discharged)

**Business Rules:**
- Only active children appear in caseloads
- Discharged children cannot have new visits logged
- Discharge process sets this to 'discharged'

#### 2. Caseload Status (`caseload_status`)
**Purpose:** Indicates assignment status to staff caseloads

**Values:**
- `caseload` - Child is assigned to staff member(s)
- `non_caseload` - Child receives services but no caseload assignment
- `awaiting_assignment` - Child created but not yet assigned

**UI Display:** 
- Blue badge (Caseload)
- Purple badge (Non-Caseload)
- Orange badge (Awaiting Assignment)

**Business Rules:**
- **Auto-updated by signals** when assignments change
- CSV imports default to 'awaiting_assignment'
- Supervisors/admins can manually override
- Discharge process sets this to 'non_caseload'

#### 3. On Hold Flag (`on_hold`)
**Purpose:** Temporarily pause a child's record while keeping them active

**Values:** Boolean (True/False)

**UI Display:** Yellow badge with border (only if True)

**Business Rules:**
- Can be set by any user with edit permissions
- Can apply to both active and discharged children
- Does not affect caseload_status
- Useful for temporary service interruptions

### Status Badge CSS Classes

```css
/* Overall Status */
.overall-status-active { background: #10b981; color: white; }
.overall-status-discharged { background: #6b7280; color: white; }

/* Caseload Status */
.caseload-status-caseload { background: #3b82f6; color: white; }
.caseload-status-non_caseload { background: #8b5cf6; color: white; }
.caseload-status-awaiting_assignment { background: #f59e0b; color: white; }

/* On Hold */
.on-hold-badge { background: #fef3c7; color: #92400e; border: 2px solid #fbbf24; }
```

### Template Display Pattern

```django
<!-- All three badges displayed horizontally -->
<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full overall-status-{{ child.overall_status }}">
    {{ child.get_overall_status_display }}
</span>
<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full caseload-status-{{ child.caseload_status }}">
    {{ child.get_caseload_status_display }}
</span>
{% if child.on_hold %}
<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full on-hold-badge">
    On Hold
</span>
{% endif %}
```

---

## Signal Handlers & Automation

### Location: core/signals.py (end of file) and core/models.py (end of file)

### 1. Caseload Status Auto-Update

**Trigger:** When CaseloadAssignment is saved or deleted

**Logic:**
```python
@receiver(post_save, sender=CaseloadAssignment)
def update_child_caseload_status_on_assign(sender, instance, created, **kwargs):
    """When a staff is assigned, update child to 'caseload' status"""
    if instance.unassigned_at is None:
        child = instance.child
        if child.caseload_status != 'caseload':
            child.caseload_status = 'caseload'
            child.save(update_fields=['caseload_status'])

@receiver(post_save, sender=CaseloadAssignment)
def update_child_caseload_status_on_unassign(sender, instance, **kwargs):
    """When last assignment is removed, update to 'awaiting_assignment'"""
    if instance.unassigned_at is not None:
        child = instance.child
        active_assignments = child.caseload_assignments.filter(unassigned_at__isnull=True).exists()
        if not active_assignments and child.caseload_status == 'caseload':
            child.caseload_status = 'awaiting_assignment'
            child.save(update_fields=['caseload_status'])

@receiver(post_delete, sender=CaseloadAssignment)
def update_child_caseload_status_on_delete(sender, instance, **kwargs):
    """When assignment is deleted, check if child should be awaiting_assignment"""
    child = instance.child
    active_assignments = child.caseload_assignments.filter(unassigned_at__isnull=True).exists()
    if not active_assignments and child.caseload_status == 'caseload':
        child.caseload_status = 'awaiting_assignment'
        child.save(update_fields=['caseload_status'])
```

### 2. Audit Logging Signals (audit/signals.py)

**Trigger:** post_save and post_delete on all models

**Captures:**
- User who made the change
- Action type (create, update, delete)
- Before/after values for updates
- Timestamp and IP address

---

## API Endpoints

### Base URL: `/api/`

### Children Endpoints
- `GET /api/children/` - List all children (filtered by role)
- `POST /api/children/` - Create new child
- `GET /api/children/{id}/` - Child detail
- `PUT /api/children/{id}/` - Update child
- `PATCH /api/children/{id}/` - Partial update
- `DELETE /api/children/{id}/` - Delete child
- `GET /api/children/my_caseload/` - Current user's caseload
- `GET /api/children/non_caseload/` - Non-caseload children

**Filters:** `?overall_status=active&caseload_status=caseload&on_hold=false&centre=1`

### Visits Endpoints
- `GET /api/visits/` - List visits
- `POST /api/visits/` - Create visit
- `GET /api/visits/{id}/` - Visit detail
- `PUT /api/visits/{id}/` - Update visit
- `DELETE /api/visits/{id}/` - Delete visit

### Referrals Endpoints
- `GET /api/referrals/` - List referrals
- `POST /api/referrals/` - Create referral
- `GET /api/referrals/{id}/` - Referral detail
- `PUT /api/referrals/{id}/` - Update referral
- `PATCH /api/referrals/{id}/` - Partial update

### Centres Endpoints
- `GET /api/centres/` - List centres
- `GET /api/centres/{id}/` - Centre detail

### API Authentication
- Session-based (uses Django sessions)
- CSRF token required for POST/PUT/PATCH/DELETE
- Returns 403 Forbidden if unauthorized

---

## Templates & UI

### Navigation Structure (base.html)

**All Users:**
- Dashboard
- My Caseload (staff) / All Children (supervisors/admins)
- Add Child

**Supervisors/Admins Only:**
- All Children
- Community Partners
- Referrals Management
- Import Children
- Reports

### Dashboard Views

**Staff Dashboard:**
- Primary Caseload count (card)
- Secondary Caseload count (card)
- Recent Visits count (card)
- Recent visits list with child names

**Supervisor/Admin Dashboard:**
- Total Active Children count (card)
- Visits Last 30 Days count (card)
- Quick links to: All Children, Reports, Log Visit

### Filter Patterns

**all_children.html:**
- Search by name/guardian
- Overall Status dropdown (All, Active, Discharged)
- Caseload Status dropdown (All, Caseload, Non-Caseload, Awaiting Assignment)
- On Hold dropdown (All, On Hold, Active)

**my_caseload.html:**
- Toggle buttons: Primary / Secondary / All Non-Caseload / All Children
- Displays counts for each category

### Form Patterns

**Add Child:**
- Basic info: Name, DOB, Centre
- Guardian info: Name, phone, email (2 guardians)
- Start date
- Notes
- **No status fields** - defaults to active/awaiting_assignment

**Edit Child:**
- Same fields as Add Child, plus:
- Caseload Status dropdown (supervisors/admins only)
- On Hold checkbox (all users)
- Cannot change overall_status here (use Discharge button)

**Discharge Child:**
- Displays current status (all three badges)
- End Date field (required)
- Discharge Reason textarea (required)
- Confirmation warning
- Sets: overall_status='discharged', caseload_status='non_caseload', on_hold=False

---

## Custom Theming System

### ThemeSetting Model
Located in `core/models.py`. Singleton pattern (pk=1, prevents deletion).

**Fields:**
- `primary_color` (ColorField) - Primary brand color
- `secondary_color` (ColorField) - Secondary accent color  
- `accent_color` (ColorField) - Accent color for highlights
- `success_color` (ColorField) - Success status color
- `warning_color` (ColorField) - Warning status color
- `danger_color` (ColorField) - Error/danger color
- `header_bg_color` (ColorField) - Navigation bar background
- `logo_image` (ImageField) - Logo upload (recommended: 200x100 or 350x200px)
- `favicon` (ImageField) - Browser tab icon
- `background_image` (ImageField) - Page background
- `site_title` (CharField) - Custom site name in navbar
- `created_at`, `updated_at` (DateTimeField) - Timestamps

**Key Methods:**
- `get_theme()` - Static method returning singleton instance
- `save()` - Enforces pk=1, prevents duplicates
- `delete()` - Overridden to prevent deletion

### Admin Interface
- Native color picker via django-colorfield
- Image uploads with preview
- Organized fieldsets by function
- Single-instance editing pattern

### Template Integration
- Logo display in navbar
- Site title customization
- Dynamic CSS variable injection
- Header background color

### Migration History
- `0009_themesetting.py` - Initial model
- `0010_alter_themesetting_*.py` - ColorField conversion
- `0011_themesetting_header_bg_color.py` - Header customization

---

## Centre Management

### Centre Model
Located in `core/models.py`

**Fields:**
- `name` - Centre name
- `address_line1`, `address_line2` - Street addresses (encrypted)
- `city`, `province`, `postal_code` - Location (encrypted)
- `phone`, `contact_name`, `contact_email` - Contact info (encrypted)
- `status` - 'active' or 'inactive'
- `notes` - Additional information (encrypted)

### CSV Import Utility (CentreCSVImporter)
Located in `core/utils/csv_import.py`

**Required Fields:** name, address_line1, city, province, postal_code, phone
**Optional Fields:** address_line2, contact_name, contact_email, status, notes

**Validation:**
- Email format verification
- Status choice validation (active/inactive)
- Whitespace trimming
- Returns summary with error messages

**Methods:**
- `parse()` - Read and validate CSV
- `import_rows()` - Create Centre records
- `get_import_template()` - Generate example CSV

### Views
- `centre_list()` - View all centres (all users)
- `import_centres()` - Upload CSV (admin/supervisor)
- `import_centres_preview()` - Preview before import
- `download_centres_template()` - Get example CSV

### Templates
- `core/centre_list.html` - Centre listing table
- `core/import_centres.html` - Import form with instructions
- `core/import_centres_preview.html` - Preview and confirmation

### Navigation Changes
- Added "Centres" link (all authenticated users)
- Removed "Community Partners" link
- Import button visible only to admin/supervisor

### Permissions
- List: All authenticated users can view
- Import: superuser or role == 'admin' only

---

## Staff-Scoped Reporting (Phase 7)

### Overview
Staff (front-line workers) now have secure access to view their own visit data through the Reports system, with automatic filtering and restricted access to sensitive organizational reports.

### Permission System

**Two-Layer Architecture (Critical):**

1. **View-Level Permission** (`reports/views.py`):
   ```python
   def can_access_reports(user):
       return user.is_superuser or user.role in ['staff', 'supervisor', 'admin', 'auditor']
   ```
   - Controls access to report views via `@user_passes_test` decorator
   - Added `'staff'` role to allow staff access

2. **Template-Level Permission** (`accounts/models.py`):
   ```python
   @property
   def can_access_reports(self):
       return self.is_superuser or self.role in ['staff', 'supervisor', 'admin', 'auditor']
   ```
   - Controls "Reports" link visibility in navigation
   - Must be synchronized with view-level check to prevent login loops

**Important:** Both checks MUST include identical role lists. Mismatched permissions cause redirect loops.

### Staff Detection Pattern
Used consistently across views and templates:
```python
user_is_staff = hasattr(request.user, 'role') and request.user.role == 'staff'
```

### Visits Report Filtering

**Modified `visits_report()` View Behavior:**

**For Staff Users:**
- Auto-filters: `Visit.objects.filter(staff=request.user)`
- Sees only their own visits (cannot change via URL parameter)
- Can filter by: date range, child, centre, visit type
- Cannot export to CSV (button hidden, backend validation)
- Sees info box explaining restrictions
- Staff column hidden from table (redundant)
- Staff filter dropdown hidden

**For Supervisors/Admins:**
- Sees all visits (unchanged behavior)
- Can filter by any staff member
- Can export to CSV
- Can see staff column in table
- All controls visible and functional

**Implementation Details:**
```python
# In visits_report() view
user_is_staff = hasattr(request.user, 'role') and request.user.role == 'staff'

# Force staff ID for staff users (URL parameter silently ignored)
if user_is_staff:
    staff_id = request.user.id

# Disable CSV export for staff
if export_format == 'csv' and not user_is_staff:
    # Generate CSV
else:
    # Continue to HTML view

# Pass to template
context = {
    'user_is_staff': user_is_staff,
    'current_staff_name': request.user.get_full_name(),
}
```

### Dashboard Report Filtering

**Staff Dashboard:**
- Shows ONLY "Visits Report" card
- Other 8 report cards completely hidden via `{% if not user_is_staff %}` conditionals
- Prevents staff from discovering sensitive reports
- Page subtitle changes: "View your visit records and hours"

**Supervisor/Admin Dashboard:**
- Shows all 9 report cards (unchanged):
  1. Children Served Report
  2. Visits Report
  3. Staff Summary Report
  4. Caseload Report
  5. Age Out Report
  6. Month Added Report
  7. Staff Site Visits Report
  8. Site Visit Summary Report
- Page subtitle: "Generate and view various reports for the ISS Portal"

**Hidden Reports for Staff:**
- Cannot be accessed directly (404 with permission check)
- Cannot be discovered via dashboard
- Cannot be guessed via URL patterns

### Template Changes

**visits_report.html:**
- Blue info box explaining staff restrictions (conditional)
- Staff filter dropdown hidden for staff (conditional)
- Staff column hidden from visit table for staff (conditional)
- CSV export button replaced with permission message for staff (conditional)
- Dynamic table colspan: 6 for staff, 7 for others

**dashboard.html:**
- Page subtitle changes based on user role
- All non-visits reports wrapped in `{% if not user_is_staff %}...{% endif %}`
- Each report card conditionally rendered

### Files Modified
1. `accounts/models.py` - Added `'staff'` to can_access_reports property
2. `reports/views.py` - Added `'staff'` to can_access_reports() function, staff detection and filtering logic
3. `templates/reports/visits_report.html` - Staff-specific UI adjustments
4. `templates/reports/dashboard.html` - Conditional report rendering

### Security Architecture

**Multi-Layer Defense:**
1. **View-Level:** Permission decorator blocks unauthorized access
2. **Query-Level:** Django ORM filters by staff user ID
3. **URL-Level:** Parameters silently ignored for staff (no error page leakage)
4. **Template-Level:** UI elements hidden to prevent discovery
5. **Permission-Level:** CSV export disabled at both template and view level

**What Staff Cannot Access:**
- Other staff member's visits
- Staff summary reports
- Caseload metrics
- Age out projections
- Organization-wide analytics
- CSV exports
- Bulk download capabilities

### Navigation Changes
- "Reports" link now visible to staff users (was previously hidden)
- Points to Reports Dashboard
- Only shows "Visits Report" card after navigation

### Testing Verification
- ✅ Staff can access Reports without login loop
- ✅ Staff dashboard shows only Visits Report
- ✅ Visits report auto-filters to staff member's visits
- ✅ Staff cannot override filters via URL parameters
- ✅ CSV export hidden and blocked for staff
- ✅ Supervisor/Admin sees all reports unchanged
- ✅ All conditional templates render correctly

---

## Docker Configuration

### Services

#### 1. PostgreSQL Database (`db`)
```yaml
image: postgres:15-alpine
environment:
  POSTGRES_DB: iss_portal
  POSTGRES_USER: iss_user
  POSTGRES_PASSWORD: (from .env)
volumes:
  - postgres_data:/var/lib/postgresql/data
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U iss_user -d iss_portal"]
  interval: 5s
  timeout: 5s
  retries: 5
```

#### 2. Django Web App (`web`)
```yaml
build: .
command: /app/docker-entrypoint.sh
environment:
  - DATABASE_URL=postgresql://iss_user:${POSTGRES_PASSWORD}@db:5432/iss_portal
  - SECRET_KEY=${SECRET_KEY}
  - FIELD_ENCRYPTION_KEY=${FIELD_ENCRYPTION_KEY}
  - DEBUG=False
  - ALLOWED_HOSTS=localhost,127.0.0.1
volumes:
  - ./staticfiles:/app/staticfiles
  - ./media:/app/media
depends_on:
  db:
    condition: service_healthy
```

**Entrypoint Script (docker-entrypoint.sh):**
1. Wait for database
2. Run migrations
3. Collect static files
4. Create initial data (visit types, admin user)
5. Start Gunicorn (4 workers)

#### 3. Nginx (`nginx`)
```yaml
image: nginx:alpine
ports:
  - "80:80"
volumes:
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  - ./staticfiles:/app/staticfiles:ro
  - ./media:/app/media:ro
depends_on:
  - web
```

### Environment Variables (.env)

```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here

# Django
SECRET_KEY=your_secret_key_here
FIELD_ENCRYPTION_KEY=your_encryption_key_here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Optional
DATABASE_URL=postgresql://iss_user:${POSTGRES_PASSWORD}@db:5432/iss_portal
```

**Generate Keys:**
```python
# SECRET_KEY
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())

# FIELD_ENCRYPTION_KEY
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Volumes
- `postgres_data` - Database persistence
- `./staticfiles` - Shared static files
- `./media` - Shared media files

---

## Recent Bug Fixes

### 1. Visit Dropdown Empty Parentheses (Fixed Jan 23, 2026)
**Issue:** Child dropdown showed "John Doe ()" instead of status

**Root Cause:** Template still referenced `child.get_status_display` which no longer exists

**Fix:** Updated `templates/core/add_visit.html` line 25:
```django
<!-- OLD -->
{{ child.full_name }} ({{ child.get_status_display }})

<!-- NEW -->
{{ child.full_name }} ({{ child.get_caseload_status_display }})
```

**Location:** `templates/core/add_visit.html`

### 2. CSV Import 'raw_data' Error (Fixed Earlier)
**Issue:** CSV import validation errors crashed with KeyError: 'raw_data'

**Root Cause:** Early validation returns didn't include 'raw_data' key in error response

**Fix:** Updated `core/utils/csv_import.py` to always include 'raw_data' in return dictionary

### 3. Visit Logging Permission Issue (Fixed Earlier)
**Issue:** Staff could see ALL children in visit logging dropdown, not just their caseload

**Root Cause:** Missing role-based filtering in add_visit view

**Fix:** Updated `core/views.py` add_visit function:
```python
if is_supervisor_or_admin:
    children = Child.objects.filter(overall_status='active').order_by('last_name', 'first_name')
else:
    # Staff only see their caseload
    children = Child.objects.filter(
        caseload_assignments__staff=user,
        caseload_assignments__unassigned_at__isnull=True,
        overall_status='active',
        caseload_status='caseload'
    ).distinct().order_by('last_name', 'first_name')
```

### 4. Migration Index Name Mismatch (Fixed During Status Refactoring)
**Issue:** Migration 0006 failed with "No index named core_child_status_31a95a_idx"

**Root Cause:** Index name hash was different than expected

**Fix:** Checked actual index name in 0001_initial.py migration and updated 0006 to use correct name: `core_child_status_f8bbac_idx`

### 5. CSS Badge Styling Not Working (Fixed Jan 23, 2026)
**Issue:** Status badges displayed as black text on white background instead of colored badges

**Root Cause:** Tailwind CSS (loaded via CDN) was overriding custom CSS colors with higher specificity

**Fix:** Added `!important` flags to all badge color styles in `static/css/custom.css`:
```css
.overall-status-active {
    background-color: #10b981 !important;
    color: white !important;
}
/* ... similar for all badge classes */
```

**Additional Steps:**
- Manually copied updated CSS to container's staticfiles directory
- Restarted nginx to serve updated CSS
- Hard refresh browser (Ctrl+F5) to clear cached CSS

**Location:** `static/css/custom.css`

---

## Testing Checklist

### After Status System Changes

**1. Child Creation:**
- [ ] Create child via form - defaults to active/awaiting_assignment
- [ ] Create child via API - defaults applied correctly
- [ ] Create child via CSV import - defaults to active/awaiting_assignment

**2. Status Display:**
- [ ] All Children page shows three badges
- [ ] Child Detail page shows three badges
- [ ] My Caseload shows three badges
- [ ] Non-Caseload Children shows three badges
- [ ] Dashboard displays correct counts

**3. Filters:**
- [ ] Filter by Overall Status (All/Active/Discharged)
- [ ] Filter by Caseload Status (All/Caseload/Non-Caseload/Awaiting Assignment)
- [ ] Filter by On Hold (All/On Hold/Active)
- [ ] Combine multiple filters

**4. Status Updates:**
- [ ] Assign staff to child → caseload_status changes to 'caseload'
- [ ] Unassign all staff from child → caseload_status changes to 'awaiting_assignment'
- [ ] Toggle on_hold checkbox → saves correctly
- [ ] Discharge child → all three fields update correctly

**5. Permissions:**
- [ ] Staff can edit on_hold for their caseload
- [ ] Staff cannot edit caseload_status
- [ ] Supervisors can edit caseload_status
- [ ] Staff can discharge children
- [ ] Staff only see their caseload in visit dropdown

**6. Visit Logging:**
- [ ] Staff see only their active caseload children
- [ ] Supervisors see all active children
- [ ] Dropdown shows "Name (Caseload Status)"
- [ ] Cannot log visit for discharged child

**7. CSV Import:**
- [ ] Upload valid CSV - children created with awaiting_assignment
- [ ] Upload CSV with on_hold=true - flag set correctly
- [ ] Download template - no status column
- [ ] Preview shows correct default statuses

**8. API Endpoints:**
- [ ] GET /api/children/ returns all three status fields
- [ ] POST /api/children/ applies defaults
- [ ] Filter by ?overall_status=active
- [ ] Filter by ?caseload_status=caseload
- [ ] Filter by ?on_hold=false

---

## Known Considerations

### 1. Encryption Performance
- PII fields encrypted at rest, decrypted on read
- Large queries may have performance overhead
- Consider indexing encrypted fields if needed

### 2. Signal Recursion Prevention
- Signals use `update_fields` parameter to avoid infinite loops
- Example: `child.save(update_fields=['caseload_status'])`

### 3. Django Admin vs. Frontend
- Admin interface may not always reflect latest frontend changes
- Test changes in both admin and main UI
- Admin shows raw field values, frontend uses helper properties

### 4. Migration Dependencies
- Migration 0006_restructure_child_status MUST run after 0001_initial
- Contains data migration - do not skip
- Backup database before running in production

### 5. Static Files Collection
- Run `python manage.py collectstatic` after CSS changes
- Docker entrypoint automatically runs this on startup
- Nginx serves static files from `/app/staticfiles`

### 6. Audit Log Growth
- Audit logs are never automatically deleted
- Consider implementing retention policy for production
- Can filter by date range in admin interface

### 7. CSV Import Large Files
- Current implementation loads entire file into memory
- For files >1000 rows, consider chunked processing
- Preview shows all rows - may be slow for large imports

---

## Development Commands

### Docker Operations

```powershell
# Start all containers
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# Stop all containers
docker-compose down

# Stop and remove volumes (CAUTION: deletes database)
docker-compose down -v

# View logs
docker-compose logs web
docker-compose logs web --tail 50 --follow

# Execute command in container
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Database backup
docker-compose exec db pg_dump -U iss_user iss_portal > backup.sql

# Database restore
docker-compose exec -T db psql -U iss_user iss_portal < backup.sql
```

### Django Management Commands

```powershell
# Run migrations
docker-compose exec web python manage.py migrate

# Create migration
docker-compose exec web python manage.py makemigrations

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Django shell
docker-compose exec web python manage.py shell

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Check for issues
docker-compose exec web python manage.py check

# View SQL for migration
docker-compose exec web python manage.py sqlmigrate core 0006
```

### Useful Shell Commands

```python
# In Django shell (docker-compose exec web python manage.py shell)

from core.models import Child, CaseloadAssignment
from accounts.models import User

# Check all children with status
for child in Child.objects.all():
    print(f"{child.full_name}: {child.overall_status} / {child.caseload_status} / on_hold={child.on_hold}")

# Find awaiting assignment children
awaiting = Child.objects.filter(caseload_status='awaiting_assignment')
print(f"Children awaiting assignment: {awaiting.count()}")

# Check signal handlers are registered
from django.db.models.signals import post_save
print(post_save.receivers)

# Manually trigger status update
child = Child.objects.first()
child.caseload_status = 'awaiting_assignment'
child.save(update_fields=['caseload_status'])
```

---

## Next Steps / Potential Enhancements

### Immediate Priorities
1. ✅ Status system refactoring - COMPLETE
2. ✅ CSV import feature - COMPLETE
3. ✅ Permission fixes - COMPLETE
4. ✅ Template updates - COMPLETE

### Future Enhancements
1. **Reporting Dashboard:**
   - Caseload size distribution
   - Visit frequency analytics
   - Discharge reason trends

2. **Notifications:**
   - Email notifications for referral status changes
   - Reminders for overdue visits
   - Assignment notifications for staff

3. **Advanced Search:**
   - Full-text search across all child fields
   - Search by age range
   - Search by assignment date range

4. **Document Management:**
   - Attach files to child records
   - Secure document storage
   - Document versioning

5. **API Improvements:**
   - Token-based authentication
   - Rate limiting
   - API documentation (Swagger/OpenAPI)

6. **Mobile Optimization:**
   - Progressive Web App (PWA)
   - Offline visit logging
   - Mobile-first forms

7. **Data Export:**
   - Export search results to CSV
   - Bulk export for reporting
   - Excel format support

---

## Quick Reference

### Access URLs
- **Application:** http://localhost
- **Admin Interface:** http://localhost/admin
- **API Root:** http://localhost/api/
- **API Documentation:** http://localhost/api/ (browsable API)

### Key File Locations
- **Models:** `core/models.py`
- **Views:** `core/views.py`
- **Signals:** `core/signals.py` and `core/models.py` (end of file)
- **Templates:** `templates/core/`
- **CSS:** `static/css/custom.css`
- **Migration:** `core/migrations/0006_restructure_child_status.py`
- **CSV Import:** `core/utils/csv_import.py`

### Status Field Names
```python
child.overall_status        # 'active' or 'discharged'
child.caseload_status      # 'caseload', 'non_caseload', or 'awaiting_assignment'
child.on_hold              # True or False
```

### Common Queries
```python
# Active children in caseload
Child.objects.filter(overall_status='active', caseload_status='caseload')

# Children awaiting assignment
Child.objects.filter(caseload_status='awaiting_assignment')

# Discharged children
Child.objects.filter(overall_status='discharged')

# On hold children
Child.objects.filter(on_hold=True)

# Staff's primary caseload
Child.objects.filter(
    caseload_assignments__staff=user,
    caseload_assignments__is_primary=True,
    caseload_assignments__unassigned_at__isnull=True
)
```

---

## Troubleshooting

### Container Won't Start
```powershell
# Check logs
docker-compose logs web

# Common issues:
# - Database not ready: Wait for db healthcheck
# - Migration errors: Check migration files
# - Port in use: Change port in docker-compose.yml
```

### Database Connection Error
```powershell
# Check database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Recreate database (CAUTION: loses data)
docker-compose down -v
docker-compose up -d
```

### Static Files Not Loading
```powershell
# Recollect static files
docker-compose exec web python manage.py collectstatic --noinput

# Restart nginx
docker-compose restart nginx
```

### Migration Issues
```powershell
# Check migration status
docker-compose exec web python manage.py showmigrations

# Roll back one migration
docker-compose exec web python manage.py migrate core 0005

# Fake a migration (if already applied manually)
docker-compose exec web python manage.py migrate core 0006 --fake
```

---

## Summary

This ISS Portal project is a fully functional child welfare case management system with:
- ✅ Three-field status system (overall_status, caseload_status, on_hold)
- ✅ Role-based access control (staff, supervisor, admin)
- ✅ PII encryption at rest
- ✅ Comprehensive audit logging
- ✅ CSV bulk import with validation
- ✅ Automated caseload status updates via signals
- ✅ RESTful API with Django REST Framework
- ✅ Docker containerization for easy deployment
- ✅ 8 fully updated templates reflecting new status system
- ✅ CSS badge styling with !important flags for proper color display
- ✅ Visit centre pre-selection based on child's assigned centre

**Current Status:** Production-ready after recent status refactoring (Jan 23, 2026)

**Recent Work (Jan 23, 2026):** 
1. Complete status system restructure from single field to three fields
2. Updated all backend code (models, views, serializers, viewsets, admin)
3. Updated all 8 templates to display three-field status system
4. Fixed CSS badge styling issues with !important flags
5. Fixed visit dropdown empty parentheses bug
6. Added centre pre-selection when logging visits from child pages

**Latest Enhancements:**
- CSS badge styling now properly overrides Tailwind CSS defaults
- Visit form automatically selects child's assigned centre when accessed via "Log Visit" button
- All status badges display with correct colors (green, gray, blue, purple, orange, yellow)

**Next Session:** Can proceed with enhancements, reporting features, or additional functionality as needed.

---

**Document Version:** 1.1  
**Last Verified:** January 23, 2026  
**Container Status:** Running (web, db, nginx)  
**Migration Status:** 0006_restructure_child_status applied successfully
