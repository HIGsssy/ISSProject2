from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


class UserCreationFormWithEmail(forms.ModelForm):
    """Custom user creation form that requires email (for Entra SSO matching)."""

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError(
                'Email is required. It must match the user\'s Entra UPN for SSO to work.'
            )
        return email


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin interface.
    Only administrators can access this interface.
    """
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'has_sso']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'sso_id']
    ordering = ['last_name', 'first_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Permissions', {
            'fields': ('role', 'phone'),
        }),
        ('Entra SSO Integration', {
            'fields': ('sso_id',),
            'description': (
                'For Entra Application Proxy SSO, the user\'s email address must '
                'match their Microsoft Entra User Principal Name (UPN). '
                'The Azure AD Object ID (sso_id) is auto-populated on first SSO login, '
                'or can be set manually here.'
            ),
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('first_name', 'last_name', 'email', 'role', 'phone'),
            'description': (
                'Email is required and must match the user\'s Microsoft Entra '
                'User Principal Name (UPN) for SSO authentication.'
            ),
        }),
    )

    @admin.display(boolean=True, description='SSO')
    def has_sso(self, obj):
        """Show whether the user has an SSO ID linked."""
        return bool(obj.sso_id)
    
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
