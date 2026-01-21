"""
Custom permission classes for role-based access control.
"""
from rest_framework import permissions


class IsStaffMember(permissions.BasePermission):
    """
    Permission for front-line staff members.
    Can view all children/centres, create/edit own visits only.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Staff members have access
        if hasattr(request.user, 'role'):
            return request.user.role in ['staff', 'supervisor', 'admin']
        
        return request.user.is_staff or request.user.is_superuser
    
    def has_object_permission(self, request, view, obj):
        # Staff can only edit their own visits
        if hasattr(obj, 'staff'):
            return obj.staff == request.user or request.user.role in ['supervisor', 'admin']
        return True


class IsSupervisorOrAdmin(permissions.BasePermission):
    """
    Permission for supervisors and administrators.
    Full read/write access to children, centres, visits, and caseloads.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'role'):
            return request.user.role in ['supervisor', 'admin']
        
        return False


class IsAdminUser(permissions.BasePermission):
    """
    Permission for administrators only.
    Can manage users and system settings.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'role'):
            return request.user.role == 'admin'
        
        return False


class CanAccessReports(permissions.BasePermission):
    """
    Permission for accessing reports.
    Supervisors, admins, and auditors can access reports.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'role'):
            return request.user.role in ['supervisor', 'admin', 'auditor']
        
        return False


class CanEditVisit(permissions.BasePermission):
    """
    Permission for editing visits.
    Staff can edit their own visits.
    Supervisors and admins can edit all visits.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True
    
    def has_object_permission(self, request, view, obj):
        # Allow read for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Supervisors and admins can edit all visits
        if hasattr(request.user, 'role'):
            if request.user.role in ['supervisor', 'admin']:
                return True
        
        # Staff can only edit their own visits
        return obj.staff == request.user


class IsReadOnly(permissions.BasePermission):
    """
    Permission for read-only access (auditors).
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only allow safe methods (GET, HEAD, OPTIONS)
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        if request.user.is_superuser:
            return True
        
        if hasattr(request.user, 'role'):
            return request.user.role in ['auditor', 'supervisor', 'admin']
        
        return False
