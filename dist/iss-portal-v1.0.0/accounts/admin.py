from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin interface.
    Only administrators can access this interface.
    """
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['last_name', 'first_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Permissions', {
            'fields': ('role', 'phone'),
        }),
        ('SSO Integration (Future)', {
            'fields': ('sso_id',),
            'classes': ('collapse',),
            'description': 'Azure AD Object ID for Single Sign-On integration'
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('first_name', 'last_name', 'email', 'role', 'phone'),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make SSO ID readonly until SSO is implemented."""
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.append('sso_id')
        return readonly
    
    def has_module_permission(self, request):
        """Only admins can access user management."""
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')
    
    def has_view_permission(self, request, obj=None):
        """Only admins can view users."""
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')
    
    def has_change_permission(self, request, obj=None):
        """Only admins can change users."""
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')
    
    def has_add_permission(self, request):
        """Only admins can add users."""
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')
    
    def has_delete_permission(self, request, obj=None):
        """Only admins can delete users."""
        return request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == 'admin')
