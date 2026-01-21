from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Read-only admin interface for audit logs.
    Only accessible by supervisors, admins, and auditors.
    """
    
    list_display = [
        'timestamp',
        'user',
        'action',
        'entity_type',
        'entity_id',
        'field_name',
        'get_summary'
    ]
    
    list_filter = [
        'action',
        'entity_type',
        'timestamp',
        'user',
    ]
    
    search_fields = [
        'entity_type',
        'entity_id',
        'field_name',
        'old_value',
        'new_value',
        'user__username',
        'user__first_name',
        'user__last_name',
    ]
    
    readonly_fields = [
        'user',
        'entity_type',
        'entity_id',
        'action',
        'field_name',
        'old_value',
        'new_value',
        'metadata',
        'timestamp',
    ]
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def get_summary(self, obj):
        """Get a summary of the change."""
        if obj.field_name:
            return f"{obj.field_name}: {obj.old_value} → {obj.new_value}"
        return obj.new_value or obj.old_value
    get_summary.short_description = 'Summary'
    
    def has_add_permission(self, request):
        """No one can manually add audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No one can edit audit logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs (for cleanup)."""
        return request.user.is_superuser
    
    def has_module_permission(self, request):
        """Only supervisors, admins, and auditors can view audit logs."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role'):
            return request.user.role in ['supervisor', 'admin', 'auditor']
        return False
    
    def has_view_permission(self, request, obj=None):
        """Only supervisors, admins, and auditors can view audit logs."""
        return self.has_module_permission(request)
