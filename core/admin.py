"""
Django admin configuration for core models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Centre, Child, VisitType, Visit, CaseloadAssignment


@admin.register(Centre)
class CentreAdmin(admin.ModelAdmin):
    """Admin interface for managing centres."""
    
    list_display = ['name', 'city', 'status', 'phone', 'contact_name', 'active_children_count']
    list_filter = ['status', 'city', 'province']
    search_fields = ['name', 'address_line1', 'city', 'contact_name']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'status')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'province', 'postal_code')
        }),
        ('Contact Information', {
            'fields': ('phone', 'contact_name', 'contact_email')
        }),
        ('Additional Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def active_children_count(self, obj):
        """Count of active children at this centre."""
        count = obj.children.filter(status='active').count()
        return count
    active_children_count.short_description = 'Active Children'
    
    def has_delete_permission(self, request, obj=None):
        """Only supervisors and admins can delete centres."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role'):
            return request.user.role in ['supervisor', 'admin']
        return False


class CaseloadAssignmentInline(admin.TabularInline):
    """Inline display of caseload assignments for a child."""
    model = CaseloadAssignment
    extra = 0
    fields = ['staff', 'is_primary', 'assigned_at', 'unassigned_at', 'assigned_by']
    readonly_fields = ['assigned_at', 'assigned_by']
    
    def get_queryset(self, request):
        """Show only active assignments by default."""
        qs = super().get_queryset(request)
        return qs.select_related('staff', 'assigned_by')


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    """Admin interface for managing children."""
    
    list_display = [
        'last_name',
        'first_name',
        'age_display',
        'centre',
        'status_badge',
        'primary_staff_display',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'centre',
        'created_at',
    ]
    
    search_fields = [
        'first_name',
        'last_name',
        'guardian_name',
        'guardian_email',
        'guardian_phone'
    ]
    
    ordering = ['last_name', 'first_name']
    
    fieldsets = (
        ('Child Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'status')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'province', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Guardian Information', {
            'fields': (
                'guardian_name', 'guardian_phone', 'guardian_email',
                'guardian2_name', 'guardian2_phone', 'guardian2_email'
            )
        }),
        ('Service Information', {
            'fields': ('centre', 'start_date', 'end_date', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    inlines = [CaseloadAssignmentInline]
    
    def age_display(self, obj):
        """Display child's age."""
        return f"{obj.age} years"
    age_display.short_description = 'Age'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'active': '#28a745',
            'on_hold': '#ffc107',
            'discharged': '#6c757d',
            'non_caseload': '#17a2b8'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def primary_staff_display(self, obj):
        """Display primary staff member."""
        staff = obj.get_primary_staff()
        return staff.get_full_name() if staff else '-'
    primary_staff_display.short_description = 'Primary Staff'
    
    def save_model(self, request, obj, form, change):
        """Set created_by/updated_by fields."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VisitType)
class VisitTypeAdmin(admin.ModelAdmin):
    """Admin interface for managing visit types."""
    
    list_display = ['name', 'is_active', 'description']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    """Admin interface for managing visits."""
    
    list_display = [
        'visit_date',
        'child_link',
        'staff',
        'centre',
        'visit_type',
        'duration_display',
        'flagged_display',
        'created_at'
    ]
    
    list_filter = [
        'visit_date',
        'visit_type',
        'staff',
        'flagged_for_review',
        'created_at',
    ]
    
    search_fields = [
        'child__first_name',
        'child__last_name',
        'staff__first_name',
        'staff__last_name',
        'notes'
    ]
    
    date_hierarchy = 'visit_date'
    ordering = ['-visit_date', '-start_time']
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('child', 'staff', 'visit_type', 'visit_date')
        }),
        ('Time', {
            'fields': ('start_time', 'end_time', 'flagged_for_review')
        }),
        ('Location', {
            'fields': ('centre', 'location_description'),
            'description': 'Centre is captured as historical snapshot at time of visit creation.'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'flagged_for_review']
    
    def child_link(self, obj):
        """Link to child admin page."""
        url = reverse('admin:core_child_change', args=[obj.child.pk])
        return format_html('<a href="{}">{}</a>', url, obj.child.full_name)
    child_link.short_description = 'Child'
    
    def duration_display(self, obj):
        """Display visit duration."""
        duration = obj.calculate_duration()
        if duration:
            return format_html(
                '<span style="{}">{}</span>',
                'color: red; font-weight: bold;' if duration >= 7.0 else '',
                obj.duration_hours
            )
        return 'N/A'
    duration_display.short_description = 'Duration'
    
    def flagged_display(self, obj):
        """Display flag status."""
        if obj.flagged_for_review:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 3px;">⚠ REVIEW</span>'
            )
        return '-'
    flagged_display.short_description = 'Flag'
    
    def get_readonly_fields(self, request, obj=None):
        """Make centre readonly to preserve historical snapshot."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing visit
            readonly.append('centre')
        return readonly
    
    def has_change_permission(self, request, obj=None):
        """Staff can only edit their own visits, supervisors can edit all."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role'):
            if request.user.role in ['supervisor', 'admin']:
                return True
            if request.user.role == 'staff' and obj:
                return obj.staff == request.user
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only supervisors and admins can delete visits."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role'):
            return request.user.role in ['supervisor', 'admin']
        return False


@admin.register(CaseloadAssignment)
class CaseloadAssignmentAdmin(admin.ModelAdmin):
    """Admin interface for managing caseload assignments."""
    
    list_display = [
        'child',
        'staff',
        'is_primary',
        'assigned_at',
        'unassigned_at',
        'assigned_by',
        'status_display'
    ]
    
    list_filter = [
        'is_primary',
        'assigned_at',
        'unassigned_at',
        'staff',
    ]
    
    search_fields = [
        'child__first_name',
        'child__last_name',
        'staff__first_name',
        'staff__last_name'
    ]
    
    date_hierarchy = 'assigned_at'
    ordering = ['-assigned_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('child', 'staff', 'is_primary')
        }),
        ('Dates', {
            'fields': ('assigned_at', 'unassigned_at')
        }),
        ('Metadata', {
            'fields': ('assigned_by',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['assigned_at', 'assigned_by']
    
    actions = ['bulk_reassign_caseload']
    
    def status_display(self, obj):
        """Display whether assignment is active."""
        if obj.unassigned_at:
            return format_html(
                '<span style="color: #6c757d;">Ended {}</span>',
                obj.unassigned_at.date()
            )
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">Active</span>'
        )
    status_display.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Set assigned_by field."""
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)
    
    def bulk_reassign_caseload(self, request, queryset):
        """
        Bulk reassign selected caseload assignments to a new staff member.
        This will be enhanced with a custom admin action page.
        """
        # For now, just mark as selected for bulk operation
        # This would typically redirect to a custom admin page for selecting new staff
        selected = queryset.filter(unassigned_at__isnull=True).count()
        self.message_user(
            request,
            f"{selected} active assignments selected for bulk reassignment. "
            "Full bulk reassignment UI coming in next iteration."
        )
    bulk_reassign_caseload.short_description = "Bulk reassign selected caseloads"
    
    def has_module_permission(self, request):
        """Only supervisors and admins can access caseload management."""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role'):
            return request.user.role in ['supervisor', 'admin']
        return False
    
    def has_view_permission(self, request, obj=None):
        """Only supervisors and admins can view caseload assignments."""
        return self.has_module_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """Only supervisors and admins can change caseload assignments."""
        return self.has_module_permission(request)
    
    def has_add_permission(self, request):
        """Only supervisors and admins can add caseload assignments."""
        return self.has_module_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Only supervisors and admins can delete caseload assignments."""
        return self.has_module_permission(request)
