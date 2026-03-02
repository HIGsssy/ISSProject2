"""
Tests for the Entra Application Proxy SSO middleware.
"""
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http import HttpResponse

from accounts.middleware import EntraProxyAuthMiddleware, is_entra_sso_request

User = get_user_model()


def get_response(request):
    """Dummy view for middleware testing."""
    return HttpResponse('OK')


def _add_session_and_auth(request):
    """Attach session and auth middleware to a raw RequestFactory request."""
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()

    auth = AuthenticationMiddleware(lambda req: None)
    auth.process_request(request)

    # Message middleware needed for login()
    setattr(request, '_messages', FallbackStorage(request))


class EntraMiddlewareDisabledTests(TestCase):
    """Tests when ENTRA_PROXY_AUTH_ENABLED = False (default)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test.user@contoso.com',
            password='testpass123',
            role='staff',
        )

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=False)
    def test_headers_ignored_when_disabled(self):
        """Entra headers should be completely ignored when SSO is disabled."""
        request = self.factory.get('/', HTTP_X_MS_CLIENT_PRINCIPAL_NAME='test.user@contoso.com')
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        # User should NOT be authenticated (headers were ignored)
        self.assertFalse(request.user.is_authenticated)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=False)
    def test_is_entra_sso_request_false_when_disabled(self):
        """is_entra_sso_request should return False when SSO is disabled."""
        request = self.factory.get(
            '/', HTTP_X_MS_CLIENT_PRINCIPAL_NAME='test.user@contoso.com'
        )
        self.assertFalse(is_entra_sso_request(request, credentials=None))


class EntraMiddlewareEnabledTests(TestCase):
    """Tests when ENTRA_PROXY_AUTH_ENABLED = True."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(
            username='jdoe',
            email='john.doe@contoso.com',
            password='testpass123',
            role='staff',
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@contoso.com',
            password='testpass123',
            role='admin',
        )

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_valid_upn_authenticates_user(self):
        """A valid UPN matching user email should authenticate the user."""
        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='john.doe@contoso.com',
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.pk, self.staff_user.pk)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_case_insensitive_email_match(self):
        """UPN matching should be case-insensitive."""
        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='John.Doe@Contoso.com',
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.pk, self.staff_user.pk)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_unmatched_upn_returns_403(self):
        """An unknown UPN should return 403 Access Denied."""
        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='unknown.user@contoso.com',
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(request.user.is_authenticated)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_empty_header_passes_through(self):
        """No Entra header should pass through (for direct access / fallback login)."""
        request = self.factory.get('/')
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(request.user.is_authenticated)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_login_url_bypassed(self):
        """Requests to the login URL should not trigger SSO authentication."""
        request = self.factory.get(
            '/login/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='john.doe@contoso.com',
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        # User should NOT be authenticated (login path is excluded)
        self.assertFalse(request.user.is_authenticated)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_sso_id_auto_populated(self):
        """sso_id should be auto-populated on first SSO login."""
        self.assertIsNone(self.staff_user.sso_id)

        object_id = 'abc-123-def-456'
        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='john.doe@contoso.com',
            HTTP_X_MS_CLIENT_PRINCIPAL_ID=object_id,
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        middleware(request)

        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.sso_id, object_id)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_sso_id_not_overwritten(self):
        """If sso_id is already set, it should not be overwritten."""
        existing_id = 'existing-id-789'
        self.staff_user.sso_id = existing_id
        self.staff_user.save()

        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='john.doe@contoso.com',
            HTTP_X_MS_CLIENT_PRINCIPAL_ID='new-id-999',
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        middleware(request)

        self.staff_user.refresh_from_db()
        self.assertEqual(self.staff_user.sso_id, existing_id)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_match_by_sso_id_when_email_differs(self):
        """Match by sso_id when email has changed but sso_id is set."""
        object_id = 'known-object-id'
        self.staff_user.sso_id = object_id
        self.staff_user.save()

        # Use a different email than what's stored
        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='new.email@contoso.com',
            HTTP_X_MS_CLIENT_PRINCIPAL_ID=object_id,
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(request.user.is_authenticated)
        self.assertEqual(request.user.pk, self.staff_user.pk)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_inactive_user_denied(self):
        """Inactive users should not be authenticated even if email matches."""
        self.staff_user.is_active = False
        self.staff_user.save()

        request = self.factory.get(
            '/',
            HTTP_X_MS_CLIENT_PRINCIPAL_NAME='john.doe@contoso.com',
        )
        _add_session_and_auth(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 403)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_already_authenticated_passes_through(self):
        """If user is already authenticated (session), middleware should not re-process."""
        request = self.factory.get('/')
        _add_session_and_auth(request)

        # Simulate an already-authenticated session
        from django.contrib.auth import login
        request.user = self.admin_user
        login(request, self.admin_user, backend='django.contrib.auth.backends.ModelBackend')
        request.session.save()

        # Re-attach the authenticated user
        auth_mw = AuthenticationMiddleware(lambda req: None)
        auth_mw.process_request(request)

        middleware = EntraProxyAuthMiddleware(get_response)
        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        # Should still be the admin user, not re-matched
        self.assertEqual(request.user.pk, self.admin_user.pk)

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_is_entra_sso_request_true(self):
        """is_entra_sso_request should return True with SSO enabled and header present."""
        request = self.factory.get(
            '/', HTTP_X_MS_CLIENT_PRINCIPAL_NAME='john.doe@contoso.com'
        )
        self.assertTrue(is_entra_sso_request(request, credentials=None))

    @override_settings(ENTRA_PROXY_AUTH_ENABLED=True)
    def test_is_entra_sso_request_false_no_header(self):
        """is_entra_sso_request should return False with SSO enabled but no header."""
        request = self.factory.get('/')
        self.assertFalse(is_entra_sso_request(request, credentials=None))
