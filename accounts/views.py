"""
Custom authentication views for Entra Application Proxy SSO integration.
"""
import logging

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)


@login_required
def sso_logout(request):
    """
    Custom logout view that handles both local and SSO sessions.

    When Entra SSO is enabled:
      - Clears the local Django session
      - Displays a "signed out" page (since simply redirecting to /login/
        would re-authenticate the user via the proxy immediately)

    When Entra SSO is disabled:
      - Standard logout redirect to the login page
    """
    username = request.user.get_full_name() or request.user.username
    logout(request)

    if getattr(settings, 'ENTRA_PROXY_AUTH_ENABLED', False):
        # With SSO active, show a signed-out page instead of redirecting
        # (a redirect to /login/ would instantly re-authenticate via the proxy)
        return render(request, 'sso_signed_out.html', {
            'username': username,
        })
    else:
        return redirect(settings.LOGOUT_REDIRECT_URL or '/login/')
