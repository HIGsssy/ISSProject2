"""
URL configuration for iss_portal project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from accounts.views import sso_logout


def debug_headers(request):
    """TEMPORARY - Remove after debugging SSO"""
    headers = {k: v for k, v in request.META.items()
               if k.startswith(('HTTP_X_MS', 'HTTP_X_FORWARDED', 'HTTP_HOST'))}
    return JsonResponse({
        'all_x_ms_headers': headers,
        'principal_name': request.META.get('HTTP_X_MS_CLIENT_PRINCIPAL_NAME', 'NOT PRESENT'),
        'principal_id': request.META.get('HTTP_X_MS_CLIENT_PRINCIPAL_ID', 'NOT PRESENT'),
        'http_host': request.META.get('HTTP_HOST', 'NOT PRESENT'),
    })


urlpatterns = [
    path('debug-headers/', debug_headers),  # TEMPORARY - REMOVE AFTER SSO DEBUGGING
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('api/', include('core.api_urls')),
    path('reports/', include('reports.urls')),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', sso_logout, name='logout'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = 'Inclusion Support Services Portal'
admin.site.site_title = 'ISS Portal Admin'
admin.site.index_title = 'Administration'
