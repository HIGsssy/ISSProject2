"""
Middleware for Microsoft Entra Application Proxy header-based SSO authentication.

When Entra Application Proxy is configured with pre-authentication (Microsoft Entra ID),
it authenticates users externally and injects identity headers into requests forwarded
to the internal application:

  - X-MS-CLIENT-PRINCIPAL-NAME: User Principal Name (UPN), typically the user's email
  - X-MS-CLIENT-PRINCIPAL-ID: Azure AD Object ID (GUID)
  - X-MS-CLIENT-PRINCIPAL-IDP: Identity provider (e.g., 'aad')

This middleware reads those headers and authenticates the corresponding Django user.

SECURITY:
  - Only active when ENTRA_PROXY_AUTH_ENABLED=True in Django settings
  - When disabled, all Entra headers are completely ignored
  - Users must be pre-created in the database with matching email addresses
  - Unmatched authenticated users receive a 403 Access Denied response

MIDDLEWARE ORDER:
  Must be placed AFTER django.contrib.auth.middleware.AuthenticationMiddleware
  and BEFORE axes.middleware.AxesMiddleware in the MIDDLEWARE list.
"""
import logging

from django.conf import settings
from django.contrib.auth import login, get_user_model
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

User = get_user_model()


def is_entra_sso_request(request, credentials=None):
    """
    Check if this request came through Entra Application Proxy SSO.

    Used by Django Axes (via AXES_WHITELIST_CALLABLE) to skip brute-force
    lockout checks for SSO-authenticated requests.

    Called by Axes with signature (request, credentials).

    Returns True if SSO is enabled and the Entra principal header is present.
    """
    if not getattr(settings, 'ENTRA_PROXY_AUTH_ENABLED', False):
        return False
    header_name = getattr(
        settings,
        'ENTRA_PROXY_AUTH_HEADER',
        'HTTP_X_MS_CLIENT_PRINCIPAL_NAME',
    )
    return bool(request.META.get(header_name, '').strip())


class EntraProxyAuthMiddleware:
    """
    Authenticates users based on identity headers injected by
    Microsoft Entra Application Proxy.

    Flow:
      1. If SSO is disabled (ENTRA_PROXY_AUTH_ENABLED=False), pass through.
      2. If user is already authenticated (e.g., via session/fallback login), pass through.
      3. If the request is to the login or logout URL, pass through (allow fallback auth).
      4. Read the UPN from the configured header (default: X-MS-CLIENT-PRINCIPAL-NAME).
      5. If no header is present, pass through (direct access without proxy).
      6. Look up user by email (=UPN), then by sso_id (=Object ID).
      7. If found and active: log the user in, auto-populate sso_id if empty.
      8. If not found: return 403 with an access-denied page.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ENTRA_PROXY_AUTH_ENABLED', False)
        self.header_name = getattr(
            settings,
            'ENTRA_PROXY_AUTH_HEADER',
            'HTTP_X_MS_CLIENT_PRINCIPAL_NAME',
        )
        self.deny_template = getattr(
            settings,
            'ENTRA_PROXY_AUTH_DENY_TEMPLATE',
            'sso_access_denied.html',
        )

    def __call__(self, request):
        # Gate: only process when SSO is explicitly enabled
        if not self.enabled:
            return self.get_response(request)

        # Skip if user is already authenticated (session-based or fallback login)
        if hasattr(request, 'user') and request.user.is_authenticated:
            return self.get_response(request)

        # Allow fallback login/logout paths to work without SSO interference
        login_url = getattr(settings, 'LOGIN_URL', '/login/')
        logout_url = '/logout/'
        if request.path.rstrip('/') in [
            login_url.rstrip('/'),
            logout_url.rstrip('/'),
            '/admin/login',
        ]:
            return self.get_response(request)

        # Read the Entra principal name (UPN) from the proxy header
        principal_name = request.META.get(self.header_name, '').strip()
        principal_id = request.META.get('HTTP_X_MS_CLIENT_PRINCIPAL_ID', '').strip()

        # No header present — not coming through the proxy, pass through
        # (will redirect to login if @login_required)
        if not principal_name:
            return self.get_response(request)

        # Attempt to find a matching user
        user = self._find_user(principal_name, principal_id)

        if user is not None:
            # Successful match — log the user in and establish a session
            self._login_user(request, user, principal_name, principal_id)
            return self.get_response(request)
        else:
            # No matching user — deny access
            logger.warning(
                "Entra SSO: Access denied — no matching user for UPN '%s' "
                "(Object ID: %s). User must be pre-created by an administrator.",
                principal_name,
                principal_id or 'not provided',
            )
            return self._deny_access(request, principal_name)

    def _find_user(self, principal_name, principal_id):
        """
        Look up a Django user matching the Entra identity.

        Priority:
        1. Match by email address (case-insensitive) — email should equal the UPN
        2. Match by sso_id (Azure AD Object ID) — for cases where email was changed
        3. Match by username (case-insensitive) — fallback

        Only active users are returned.
        """
        user = None

        # Primary: match by email = UPN
        if principal_name:
            user = User.objects.filter(
                email__iexact=principal_name,
                is_active=True,
            ).first()

        # Secondary: match by sso_id = Azure AD Object ID
        if user is None and principal_id:
            user = User.objects.filter(
                sso_id=principal_id,
                is_active=True,
            ).first()

        # Tertiary: match by username = UPN (some setups use UPN as username)
        if user is None and principal_name:
            user = User.objects.filter(
                username__iexact=principal_name,
                is_active=True,
            ).first()

        return user

    def _login_user(self, request, user, principal_name, principal_id):
        """
        Log the user in and auto-populate sso_id if not already set.
        """
        # Auto-populate sso_id on first SSO login
        if principal_id and not user.sso_id:
            user.sso_id = principal_id
            user.save(update_fields=['sso_id'])
            logger.info(
                "Entra SSO: Auto-populated sso_id for user '%s' "
                "(Object ID: %s)",
                user.username,
                principal_id,
            )

        # Establish a Django session
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info(
            "Entra SSO: Authenticated user '%s' (%s) via UPN '%s'",
            user.username,
            user.get_role_display(),
            principal_name,
        )

    def _deny_access(self, request, principal_name):
        """
        Return a 403 response with a styled access-denied page.
        """
        try:
            html = render_to_string(self.deny_template, {
                'principal_name': principal_name,
                'theme_settings': None,
                'theme_css_variables': {},
            }, request=request)
            return HttpResponseForbidden(html)
        except Exception:
            # Fallback if template is missing
            logger.exception(
                "Entra SSO: Could not render deny template '%s'",
                self.deny_template,
            )
            return HttpResponseForbidden(
                '<h1>Access Denied</h1>'
                f'<p>Your Microsoft account ({principal_name}) was authenticated, '
                'but no matching ISS Portal account was found.</p>'
                '<p>Please contact your administrator to request access.</p>'
            )
