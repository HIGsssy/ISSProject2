# ISS Portal — Code Review Recommendations

> **Review Date:** February 26, 2026  
> **Scope:** Full codebase review — security, performance, code quality, architecture, and deployment  
> **Status:** No code changes made. This document is a planning artifact only.

---

## Table of Contents

1. [🔴 Critical Security Risks](#-critical-security-risks)
2. [🟠 High Priority — Security Hardening](#-high-priority--security-hardening)
3. [🟡 Medium Priority — Performance & Scalability](#-medium-priority--performance--scalability)
4. [🔵 Code Quality & Maintainability](#-code-quality--maintainability)
5. [⚙️ Architecture Improvements](#-architecture-improvements)
6. [📦 Dependency Updates](#-dependency-updates)
7. [🚀 Deployment & Operations](#-deployment--operations)

---

## 🔴 Critical Security Risks

### SEC-01 — No Rate Limiting on Login Endpoint
- **File:** `iss_portal/urls.py`, `iss_portal/settings.py`
- **Risk:** The `/login/` endpoint has no brute-force protection. An attacker can attempt unlimited password guesses.
- **Task:** Install and configure `django-axes` (account lockout) or `django-ratelimit`. Set a lockout policy of 5 failed attempts per 15-minute window.

### SEC-02 — No Multi-Factor Authentication (MFA)
- **Risk:** This application stores sensitive, personally identifiable information (PII) about children including names, dates of birth, addresses, guardian contact details, and referral reasons. Access is protected only by username/password.
- **Task:** Implement TOTP-based MFA using `django-otp` or `django-two-factor-auth` as a mandatory option for all roles, especially `admin`, `supervisor`, and `auditor`.

### SEC-03 — Audit Log Stores Decrypted Field Values as Plaintext
- **File:** `audit/signals.py` — `track_field_changes()`
- **Risk:** When tracking changes on encrypted model fields (`EncryptedCharField`, `EncryptedTextField`, etc.), the signal reads `old_value` and `new_value` via `getattr()`, which returns the **decrypted** value. These plaintext values are then stored in `AuditLog.old_value` and `AuditLog.new_value` (unencrypted `TextField`). This nullifies field-level encryption for all changed data.
- **Task:** Detect encrypted fields explicitly and store a redacted placeholder (e.g., `"[ENCRYPTED — value changed]"`) rather than the decrypted content. Only store actual values for non-sensitive fields.

### SEC-04 — Missing HSTS Header in Production Settings
- **File:** `iss_portal/settings.py` (lines 162–170)
- **Risk:** `SECURE_HSTS_SECONDS` is not set in the `if not DEBUG` block. Without HSTS, browsers do not enforce HTTPS, leaving sessions vulnerable to downgrade attacks.
- **Task:** Add `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, and `SECURE_HSTS_PRELOAD = True` to the production security settings block.

### SEC-05 — HTTP → HTTPS Redirect Commented Out in Nginx
- **File:** `nginx/conf.d/default.conf` (line 17)
- **Risk:** The `return 301 https://$server_name$request_uri;` redirect is commented out. In production, all HTTP traffic is served over plaintext. Sensitive session cookies and CSRF tokens are transmitted unencrypted if HTTPS is not enforced at the nginx layer.
- **Task:** Uncomment and activate the HTTPS redirect block. Ensure the HTTPS server block is enabled and SSL certificates are provisioned before going live.

### SEC-06 — Database Port Exposed to Host in Development Compose
- **File:** `docker-compose.yml` (line 14: `ports: - "5432:5432"`)
- **Risk:** The development compose file exposes PostgreSQL directly on the host. If run on any non-localhost machine (CI pipeline, cloud VM, staging), the database is accessible from the network without additional firewall rules.
- **Task:** Remove the `ports` mapping from `docker-compose.yml` and rely on the internal Docker network. Access the database via `docker exec` when needed. The production compose (`docker-compose.prod.yml`) correctly sets `ports: []`.

---

## 🟠 High Priority — Security Hardening

### SEC-07 — No Content Security Policy (CSP) Header
- **File:** `iss_portal/settings.py`, `nginx/conf.d/default.conf`
- **Risk:** No CSP header is set anywhere. This increases the impact of any XSS vulnerability by allowing arbitrary script execution.
- **Task:** Install `django-csp` and configure a strict policy that whitelists only known script/style sources. Add the header in nginx as well for defense in depth.

### SEC-08 — Hardcoded Fallback Database Password in docker-compose
- **File:** `docker-compose.yml` (line 8: `POSTGRES_PASSWORD:-change-this-password`)
- **Risk:** If `.env` is absent or incomplete, Docker Compose falls back to the insecure literal `change-this-password`.
- **Task:** Remove the default fallback value for `POSTGRES_PASSWORD`. The compose file should fail loudly rather than silently use a weak password. Document the required `.env` values in `INSTALLATION.md`.

### SEC-09 — No Session Timeout Configured
- **File:** `iss_portal/settings.py`
- **Risk:** `SESSION_COOKIE_AGE` is not set, defaulting to Django's 2-week session lifetime. For a PII-sensitive healthcare-adjacent application, sessions should expire after a period of inactivity.
- **Task:** Set `SESSION_COOKIE_AGE = 28800` (8 hours) and `SESSION_SAVE_EVERY_REQUEST = True` to implement a sliding session expiry. Consider also enabling `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`.

### SEC-10 — Permission Inconsistency: `edit_child` View vs. API
- **File:** `core/views.py` — `edit_child()` function (around line 630)
- **Risk:** The Django `edit_child` view allows any `staff`, `supervisor`, or `admin` to modify child records. However, the API viewset (`core/viewsets.py`, `ChildViewSet.get_permissions()`) restricts `update`/`partial_update` to `IsSupervisorOrAdmin` only. This means staff can bypass the API permission model by submitting the HTML form directly.
- **Task:** Align `edit_child` view permissions with the API — restrict to `supervisor` and `admin` roles only, or deliberately document and enforce that staff edits are permissible and why.

### SEC-11 — Broad Exception Handling Suppresses Errors Silently
- **File:** `core/views.py` — multiple views (`edit_child`, `add_community_partner`, `add_referral`, `discharge_child`, etc.)
- **Risk:** Widespread use of `except Exception as e: messages.error(request, f'Error: {str(e)}')` swallows stack traces and may expose internal error details to end users. It also makes debugging in production very difficult.
- **Task:** Replace broad `except Exception` blocks with specific exceptions (e.g., `ValidationError`, `IntegrityError`). Log unexpected exceptions with `logger.exception()` (using Python's `logging` module) and show a generic error message to users.

### SEC-12 — CSV File Upload Has No Size or Type Validation
- **File:** `core/utils/csv_import.py` — `ChildCSVImporter.parse()`
- **Risk:** The CSV import does not validate file size or MIME type before reading the entire file into memory with `.read().decode('utf-8')`. A malicious user could upload a large file to exhaust server memory.
- **Task:** Add file size limit validation (e.g., reject files over 5 MB). Validate that the uploaded file has a `.csv` extension and `text/csv` content type before processing.

### SEC-13 — `CORS_ALLOWED_ORIGINS` Is Hardcoded
- **File:** `iss_portal/settings.py` (lines 152–155)
- **Risk:** CORS origins (`http://localhost:3000`, `http://127.0.0.1:3000`) are hardcoded instead of being sourced from the environment via `config()`. For a production deployment with a real domain, this setting is silently wrong.
- **Task:** Change to `CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')` and document the required production value.

---

## 🟡 Medium Priority — Performance & Scalability

### PERF-01 — Full Table Scan for Search on Encrypted Fields
- **File:** `core/views.py` — `all_children()` (around line 154–160)
- **Impact:** `all_children = list(children)` loads **every matching child record** into Python memory before applying the name search filter, because encrypted fields cannot be queried at the database level. For large datasets (1000+ children), this will be slow and memory-intensive.
- **Task:** Add non-encrypted, one-way hashed search fields (e.g., `first_name_search_hash` and `last_name_search_hash`) for lookup purposes. Store a HMAC of the lowercased name on save using a dedicated search key, and query those hash columns instead of loading all records.

### PERF-02 — Python-Level Duration Aggregation in Reports
- **File:** `reports/views.py` — `visits_report()` (around line 74)
- **Impact:** `total_hours = sum([v.calculate_duration() or 0 for v in visits])` iterates over all returned `Visit` objects in Python. If a report spans thousands of visits, this loads every record fully into memory.
- **Task:** Move the duration calculation to the database using `annotate()` and `Sum()` with a database expression, or precompute and store `duration_minutes` as an indexed integer field on the `Visit` model and aggregate with `Sum('duration_minutes')`.

### PERF-03 — Duplicate DB Query on Every Model Save (Audit)
- **File:** `audit/signals.py` — `track_field_changes()` (line 20)
- **Impact:** Every time a tracked model (`Child`, `Centre`, `Visit`, etc.) is saved, the signal fetches the old version from the database with `instance.__class__.objects.get(pk=instance.pk)`. Combined with Django's own `save()` query, this doubles the number of DB queries for every update.
- **Task:** Use Django's `update_fields` mechanism or pass the original state via a pre-save snapshot stored on the instance (`instance._original_state`) to avoid the extra DB round-trip.

### PERF-04 — No Caching Layer
- **File:** `iss_portal/settings.py`
- **Impact:** Heavily repeated queries (visit types, active centres, staff lists) are executed fresh on every request with no caching.
- **Task:** Add Redis as a cache backend (`django-redis`) in the Docker stack. Apply `cache_page` or low-level `cache.get/set` for stable lookup data like `VisitType` lists and active `Centre` lists.

### PERF-05 — Gunicorn Worker Count Is Hardcoded
- **File:** `Dockerfile` CMD, `docker-compose.yml`, `docker-compose.prod.yml`
- **Impact:** Worker count is fixed at `--workers 4` regardless of the host machine's CPU count. Under-provisioned or over-provisioned workers degrade throughput or waste memory.
- **Task:** Use the formula `(2 × CPU_cores) + 1` dynamically: `--workers $(( 2 * $(nproc) + 1 ))` in the entrypoint, or read from an environment variable `GUNICORN_WORKERS` with a sensible default.

### PERF-06 — No Background Task Queue for Long-Running Operations
- **File:** `core/utils/csv_import.py`, `reports/views.py`
- **Impact:** CSV bulk imports and large report exports run synchronously within the HTTP request/response cycle. This can block web workers for extended periods and cause request timeouts.
- **Task:** Introduce Celery with a Redis broker for async task execution. Move CSV imports and large report generation to background tasks. Provide a job status polling endpoint.

---

## 🔵 Code Quality & Maintainability

### CODE-01 — Duplicate `@login_required` Decorator on `visit_detail`
- **File:** `core/views.py` — `visit_detail()` (around line 530)
- **Issue:** The `@login_required` decorator is applied **twice** to the `visit_detail` view. This is a harmless but confusing bug.
- **Task:** Remove the duplicate decorator.

### CODE-02 — Role Checks Duplicated Inline Throughout Views
- **File:** `core/views.py` — many views use `hasattr(user, 'role') and user.role in ['supervisor', 'admin']`
- **Issue:** This pattern is repeated 20+ times across `views.py` and `reports/views.py`. The `User` model already has helper properties (`is_supervisor`, `is_admin_user`, etc.) that should be used instead.
- **Task:** Replace inline role checks with the existing model properties (`user.is_admin_user`, `user.can_manage_caseloads`, etc.) or create a reusable `require_supervisor_or_admin()` helper decorator to keep views DRY.

### CODE-03 — `edit_child` Uses Manual `request.POST` Parsing Without a Django Form
- **File:** `core/views.py` — `edit_child()` (around line 618)
- **Issue:** The view manually processes every field with `request.POST.get(...)` instead of using a `ModelForm` or at minimum a simple `Form` class. This bypasses Django's validation pipeline, makes the code fragile, and is harder to maintain.
- **Task:** Create a `ChildEditForm` (or reuse the serializer's validation logic) and process it through `form.is_valid()` / `form.save()`.

### CODE-04 — `views.py` and `reports/views.py` Are Excessively Large
- **File:** `core/views.py` (1,230 lines), `reports/views.py` (1,050 lines)
- **Issue:** Both files are monolithic. This makes navigation, testing, and code review difficult.
- **Task:** Split `core/views.py` into logical sub-modules (e.g., `views_children.py`, `views_visits.py`, `views_caseload.py`, `views_community.py`) and import them via the app's `views.py`. Do the same for reports.

### CODE-05 — Duplicate Import in `dashboard` View
- **File:** `core/views.py` — `dashboard()` (lines 26–27)
- **Issue:** `from datetime import timedelta` and `from django.utils import timezone` are imported both at the module level and again inside the `dashboard` function body.
- **Task:** Remove the redundant inline imports.

### CODE-06 — EarlyON Centre Filter Is Fragile Name Heuristic
- **File:** `core/views.py` — `add_child()` (around line 680)
- **Issue:** `earlyon_centres = centres.filter(name__icontains='early')` relies on the string "early" appearing in a centre's name to decide if it is an EarlyON centre. This will silently fail if centres are named differently.
- **Task:** Add an explicit `centre_type` field to the `Centre` model (e.g., `childcare`, `earlyon`, `other`) and filter by type instead.

### CODE-07 — No Automated Test Suite
- **Issue:** No test files (`test_*.py` or `tests/`) were found anywhere in the project. For an application storing sensitive PII of children, untested permission boundaries and business logic are a serious maintainability and safety risk.
- **Task:** Create a baseline test suite covering: (1) permission boundary tests for all role combinations on key views, (2) model validation tests (`Child`, `Visit`, caseload logic), (3) audit signal tests to verify logs are created. Aim for at least 60% coverage as an initial milestone.

### CODE-08 — `psycopg2-binary` Should Not Be Used in Production
- **File:** `requirements.txt`
- **Issue:** `psycopg2-binary==2.9.9` bundles a pre-compiled binary that is explicitly not recommended for production use by the psycopg2 maintainers due to potential compatibility and security issues.
- **Task:** Switch to the source distribution `psycopg2==2.9.x` in production. The Dockerfile already installs `libpq-dev` and `gcc`, so compilation will succeed.

### CODE-09 — Two Excel Export Libraries Are Included
- **File:** `requirements.txt` (`openpyxl==3.1.2` and `xlsxwriter==3.1.9`)
- **Issue:** Both `openpyxl` and `xlsxwriter` are listed as dependencies for what appears to be the same Excel export functionality. This adds unnecessary dependency weight and potential security surface.
- **Task:** Audit which library is actually used at runtime and remove the unused one.

---

## ⚙️ Architecture Improvements

### ARCH-01 — No API Versioning
- **File:** `core/api_urls.py`, `iss_portal/urls.py` (`path('api/', ...)`)
- **Issue:** The REST API has no version prefix (e.g., `/api/v1/`). Any breaking API change would require a coordinated cutover with all consumers.
- **Task:** Namespace the API under `/api/v1/`. Use DRF's versioning support (`URLPathVersioning`) so future `/api/v2/` endpoints can coexist.

### ARCH-02 — Encrypted Field Search Is an Architectural Constraint That Should Be Documented and Planned
- **File:** `core/views.py`, `core/models.py`
- **Issue:** Because first/last names, guardian names, and addresses are stored as encrypted fields, no database-level full-text or `LIKE` query is possible. The current workaround (load all records, filter in Python) is not scalable.
- **Task:** Document this constraint explicitly. Evaluate and plan an implementation of deterministic HMACs stored as companion search-key columns (using a separate search HMAC key from the encryption key), allowing indexed equality lookups without exposing plaintext in the database.

### ARCH-03 — No Dedicated Health Check Endpoint
- **File:** `docker-compose.yml` (health check uses `/admin/login/`)
- **Issue:** The Docker health check calls `/admin/login/`, which triggers Django's full middleware stack, template rendering, and a database query on every 30-second interval per container. Using `admin/login/` as a health probe is fragile; a temporary DB hiccup will mark the container unhealthy.
- **Task:** Create a lightweight `/health/` view that returns `HTTP 200 {"status": "ok"}` and checks only that: (1) the application is running, and (2) a single cheap DB ping succeeds. Use this endpoint for health checks in all compose files.

### ARCH-04 — Thread-Local User Storage Is Incompatible with Async Django
- **File:** `audit/middleware.py`
- **Issue:** `AuditUserMiddleware` uses `threading.local()` to pass the current user to signals. This is a well-known pattern in synchronous Django but will silently break if async views are ever introduced (e.g., Django Channels, or `async def` views), since async code may run in the same thread for different requests.
- **Task:** Add a note in the middleware documenting this limitation. For future-proofing, investigate `contextvars.ContextVar` as a thread-and-async-safe alternative.

### ARCH-05 — SSO/M365 Azure AD Integration Is Incomplete
- **File:** `accounts/models.py` (`sso_id` field), `iss_portal/settings.py` (commented SSO settings), `requirements.txt` (commented `django-allauth`)
- **Issue:** The `sso_id` field, commented-out Azure AD settings, and commented-out `django-allauth`/`social-auth` packages indicate SSO is planned but not implemented. Staff onboarding, deprovisioning, and provisioning workflows are manual as a result.
- **Task:** Create a project task/milestone to implement Azure AD SSO via `django-allauth` with the Microsoft provider. Define a mapping strategy between Azure AD roles/groups and the application's `role` field. This is especially important for deprovisioning when staff leave.

---

## 📦 Dependency Updates

### DEP-01 — `django-encrypted-model-fields` Is Outdated (v0.6.5, 2021)
- **File:** `requirements.txt`
- **Risk:** Version 0.6.5 is several years old. Review the changelog for any security fixes in later versions. If this package is unmaintained, evaluate alternatives such as `django-fernet-fields` or moving encryption to Postgres-level with `pgcrypto`.
- **Task:** Test compatibility with the latest `django-encrypted-model-fields` version and upgrade. File a fallback plan if the library is abandoned.

### DEP-02 — `cryptography==41.0.7` Should Be Updated
- **File:** `requirements.txt`
- **Risk:** `cryptography` 41.x has had CVEs addressed in subsequent patch releases. Current stable is 42.x+.
- **Task:** Run `pip-audit` (install with `pip install pip-audit`) against the full `requirements.txt` to identify all known CVEs. Update `cryptography` and any other flagged packages. Add `pip-audit` as a CI check.

### DEP-03 — Pin Django to Latest 4.2 LTS Patch
- **File:** `requirements.txt` (`Django==4.2.9`)
- **Task:** Update to the latest Django 4.2.x LTS release. Run `pip-audit` to confirm no outstanding CVEs in the current pinned version.

### DEP-04 — Add `pip-audit` or Dependabot to CI Pipeline
- **Task:** Integrate automated dependency vulnerability scanning. Either add `pip-audit` as a pre-deploy check in CI, or configure GitHub Dependabot alerts on the repository. This ensures new CVEs in pinned dependencies are caught promptly.

---

## 🚀 Deployment & Operations

### OPS-01 — No Automated SSL Certificate Renewal
- **File:** `docker-compose.yml`, `nginx/conf.d/default.conf`
- **Issue:** The Certbot service and Let's Encrypt configuration are fully commented out. SSL certificate renewal is entirely manual. An expired certificate will take the application offline without warning.
- **Task:** Uncomment and configure the Certbot container in `docker-compose.prod.yml` with automatic renewal. Test the renewal process in staging before going to production.

### OPS-02 — No Application Monitoring or Error Tracking
- **Issue:** There is no Sentry, Prometheus, or other error/performance monitoring. Production errors are only visible in container JSON logs, which require manual inspection.
- **Task:** Integrate `sentry-sdk` with Django (`sentry-sdk[django]`). Configure Sentry DSN via environment variable. At minimum, this provides automatic error reporting for unhandled exceptions. Add Prometheus metrics via `django-prometheus` if infrastructure monitoring is needed.

### OPS-03 — Docker Entrypoint Runs Migrations Automatically on Startup
- **File:** `docker-entrypoint.sh`
- **Risk:** Running `migrate --noinput` automatically on every container start is convenient for development but risky in production. In a multi-replica/rolling deployment, two containers could attempt migrations simultaneously, or a bad migration could leave the database in a partially migrated state during a production deploy.
- **Task:** Move `migrate` out of the entrypoint for production. Run migrations as a separate init container or a one-off task in the deployment pipeline before the application containers start.

### OPS-04 — Backup Recovery Is Not Tested in Automation
- **File:** `backup.sh`, `restore.sh`, `BACKUP_RECOVERY.md`
- **Issue:** Backup scripts exist and are documented, but there is no automated test of the restore process. An untested backup is not a backup.
- **Task:** Add a monthly automated restore test job (e.g., a cron job or CI pipeline step) that restores the latest backup to a temporary database, runs a check query, and alerts on failure.

### OPS-05 — No Centralised Logging
- **Issue:** Application logs go to container stdout/stderr and are rotated by Docker's `json-file` driver. There is no central log aggregation, making it impossible to search or correlate logs across incidents.
- **Task:** Configure a log shipper (e.g., Loki + Grafana, ELK Stack, or a managed service like Logtail/Papertrail) to centralize and index application logs. Ensure audit log entries also appear in the centralized log for compliance purposes.

### OPS-06 — `setup_wizard.py` Has No Access Control
- **File:** `setup_wizard.py`
- **Issue:** The setup wizard script appears to run interactively and produces initial application configuration. If it can be triggered post-deployment, it could be used to overwrite production settings or create unauthorized admin accounts.
- **Task:** Add a guard that prevents the wizard from running if it detects an existing database with users, or if an `ALLOW_SETUP_WIZARD=true` environment variable is not explicitly set. Document that it should only be run on fresh installations.

---

## Priority Summary

| Priority | Count | Category |
|----------|-------|----------|
| 🔴 Critical | 6 | SEC-01 to SEC-06 |
| 🟠 High | 7 | SEC-07 to SEC-13 |
| 🟡 Medium | 6 | PERF-01 to PERF-06 |
| 🔵 Code Quality | 9 | CODE-01 to CODE-09 |
| ⚙️ Architecture | 5 | ARCH-01 to ARCH-05 |
| 📦 Dependencies | 4 | DEP-01 to DEP-04 |
| 🚀 Operations | 6 | OPS-01 to OPS-06 |
| **Total** | **43** | |

---

## Recommended Immediate Actions (Before Next Production Deploy)

1. **SEC-05** — Enable HTTPS redirect in nginx
2. **SEC-04** — Add `SECURE_HSTS_SECONDS` to production settings
3. **SEC-01** — Install `django-axes` for login rate limiting
4. **SEC-03** — Fix audit signal to not store decrypted PII in plaintext
5. **SEC-06** — Remove database port exposure from `docker-compose.yml`
6. **DEP-02** — Run `pip-audit` and apply security patches

---

*Generated by code review — no changes were made to the codebase.*
