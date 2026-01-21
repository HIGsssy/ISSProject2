"""
Custom User model with role-based access control.
Supports future SSO integration with M365/Azure AD.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    Roles:
    - staff: Front-line inclusion support workers (mobile users)
    - supervisor: Managers with full access except user/settings management
    - admin: Full system access including user and SSO configuration
    - auditor: Read-only access to reports and audit logs
    """
    
    ROLE_CHOICES = [
        ('staff', 'Staff'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Administrator'),
        ('auditor', 'Auditor'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='staff',
        help_text='User role determines access permissions'
    )
    
    # Future SSO integration field for M365/Azure AD
    sso_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text='Azure AD Object ID for SSO integration (future use)'
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text='Contact phone number'
    )
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_staff_member(self):
        """Check if user is a front-line staff member."""
        return self.role == 'staff'
    
    @property
    def is_supervisor(self):
        """Check if user is a supervisor."""
        return self.role == 'supervisor'
    
    @property
    def is_admin_user(self):
        """Check if user is an administrator."""
        return self.role == 'admin'
    
    @property
    def is_auditor(self):
        """Check if user is an auditor."""
        return self.role == 'auditor'
    
    @property
    def can_manage_users(self):
        """Only admins can manage users."""
        return self.role == 'admin'
    
    @property
    def can_manage_caseloads(self):
        """Supervisors and admins can manage caseloads."""
        return self.role in ['supervisor', 'admin']
    
    @property
    def can_access_reports(self):
        """Supervisors, admins, and auditors can access reports."""
        return self.role in ['supervisor', 'admin', 'auditor']
    
    @property
    def can_bulk_assign(self):
        """Supervisors and admins can bulk assign caseloads."""
        return self.role in ['supervisor', 'admin']
