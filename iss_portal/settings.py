"""
Django settings for iss_portal project.
"""

import os
from datetime import timedelta
from pathlib import Path
import dj_database_url
from decouple import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'corsheaders',
    'colorfield',
    'axes',
    
    # Local apps
    'accounts',
    'core',
    'audit',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.EntraProxyAuthMiddleware',  # Entra Application Proxy SSO
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditUserMiddleware',  # Custom middleware for audit logging
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'iss_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.theme_settings',  # Theme customization context
                'core.context_processors.entra_sso_settings',  # Entra SSO status
            ],
        },
    },
]

WSGI_APPLICATION = 'iss_portal.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TZ', default='America/New_York')
USE_I18N = True
USE_TZ = True

# Field-level encryption
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')

if not FIELD_ENCRYPTION_KEY and not DEBUG:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'FIELD_ENCRYPTION_KEY must be set in production. '
        'Generate one with: python manage.py generate_encryption_key'
    )

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}

# CORS settings (adjust for production)
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# =============================================================================
# Microsoft Entra Application Proxy / SSO Configuration
# =============================================================================

# Trust the reverse proxy's forwarded protocol header.
# Entra App Proxy terminates TLS externally and forwards HTTP internally.
# This tells Django the request is HTTPS when the proxy says so.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Use the forwarded host/port from the proxy so Django generates correct URLs
# matching the external hostname (e.g. https://iss-portal.msappproxy.net).
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CSRF trusted origins — MUST include the external Entra Application Proxy URL.
# Without this, all POST requests through the proxy will fail with 403.
# Example: CSRF_TRUSTED_ORIGINS=https://iss-portal-contoso.msappproxy.net
_csrf_origins = config('CSRF_TRUSTED_ORIGINS', default='')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()] if _csrf_origins else []

# Session and CSRF cookie settings for proxy compatibility
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Entra Application Proxy SSO — header-based authentication
# Set ENTRA_PROXY_AUTH_ENABLED=True in .env to activate SSO
ENTRA_PROXY_AUTH_ENABLED = config('ENTRA_PROXY_AUTH_ENABLED', default=False, cast=bool)
ENTRA_PROXY_AUTH_HEADER = config('ENTRA_PROXY_AUTH_HEADER', default='HTTP_X_MS_CLIENT_PRINCIPAL_NAME')
ENTRA_PROXY_AUTH_DENY_TEMPLATE = 'sso_access_denied.html'

# Azure AD tenant ID (used for Entra sign-out redirect URL)
AZURE_AD_TENANT_ID = config('AZURE_AD_TENANT_ID', default='')

# Django Axes — brute-force login protection
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'account_locked.html'
# Skip Axes lockout checks for Entra SSO-authenticated requests
AXES_WHITELIST_CALLABLE = 'accounts.middleware.is_entra_sso_request'

# Security settings for production
if not DEBUG:
    # SECURE_SSL_REDIRECT must be False when behind Entra Application Proxy:
    # the proxy terminates TLS externally and forwards HTTP to this server.
    # Enabling this would cause an infinite redirect loop.
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # SAMEORIGIN allows Entra My Apps portal to embed if needed
    X_FRAME_OPTIONS = 'SAMEORIGIN'
