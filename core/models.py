"""
Core models for Inclusion Support Services Portal.

Models:
- Centre: Child care centres where services are provided
- Child: Children receiving inclusion support services
- VisitType: Lookup table for visit types
- Visit: Service visit records (immutable historical records)
- CaseloadAssignment: Staff-to-child caseload assignments with history
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class Centre(models.Model):
    """Child care centres where inclusion support services are provided."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=200)
    
    # Address fields
    address_line1 = models.CharField(max_length=200, verbose_name='Address Line 1')
    address_line2 = models.CharField(max_length=200, blank=True, verbose_name='Address Line 2')
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=50, default='ON')
    postal_code = models.CharField(max_length=10)
    
    phone = models.CharField(max_length=20)
    
    # Primary contact
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Centre'
        verbose_name_plural = 'Centres'
    
    def __str__(self):
        return self.name
    
    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        parts.append(f"{self.city}, {self.province} {self.postal_code}")
        return ', '.join(parts)


class Child(models.Model):
    """Children receiving inclusion support services."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('discharged', 'Discharged'),
        ('non_caseload', 'Non-Caseload'),
    ]
    
    # Basic information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    
    # Address fields
    address_line1 = models.CharField(max_length=200, blank=True, verbose_name='Address Line 1')
    address_line2 = models.CharField(max_length=200, blank=True, verbose_name='Address Line 2')
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=50, blank=True, default='ON')
    postal_code = models.CharField(max_length=10, blank=True)
    
    # Guardian information
    guardian_name = models.CharField(max_length=200, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    guardian_email = models.EmailField(blank=True)
    guardian2_name = models.CharField(max_length=200, blank=True, verbose_name='Second Guardian Name')
    guardian2_phone = models.CharField(max_length=20, blank=True, verbose_name='Second Guardian Phone')
    guardian2_email = models.EmailField(blank=True, verbose_name='Second Guardian Email')
    
    # Optional centre association
    centre = models.ForeignKey(
        Centre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text='Current centre (can be empty for non-caseload children)'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text='Non-caseload children will not appear in staff caseloads'
    )
    
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date services ended (for discharged children)'
    )
    
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='children_created',
        blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='children_updated',
        blank=True
    )
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Child'
        verbose_name_plural = 'Children'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        """Return child's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Calculate child's current age."""
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
        return age
    
    @property
    def is_non_caseload(self):
        """Check if child is non-caseload."""
        return self.status == 'non_caseload'
    
    def get_primary_staff(self):
        """Get the primary staff member assigned to this child."""
        assignment = self.caseload_assignments.filter(
            is_primary=True,
            unassigned_at__isnull=True
        ).first()
        return assignment.staff if assignment else None
    
    def get_all_staff(self):
        """Get all staff members assigned to this child."""
        assignments = self.caseload_assignments.filter(
            unassigned_at__isnull=True
        ).select_related('staff')
        return [assignment.staff for assignment in assignments]


class VisitType(models.Model):
    """Lookup table for types of visits."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Visit Type'
        verbose_name_plural = 'Visit Types'
    
    def __str__(self):
        return self.name


class Visit(models.Model):
    """
    Service visit records - immutable historical records.
    
    The centre field captures the child's centre at time of visit creation
    and does not update if the child's centre changes later.
    """
    
    child = models.ForeignKey(
        Child,
        on_delete=models.PROTECT,
        related_name='visits',
        help_text='Child who received the visit'
    )
    
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='visits',
        help_text='Staff member who conducted the visit'
    )
    
    # Historical snapshot of child's centre at time of visit
    centre = models.ForeignKey(
        Centre,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='visits',
        help_text='Centre where visit occurred (snapshot at time of visit creation)'
    )
    
    visit_date = models.DateField(default=timezone.now)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    visit_type = models.ForeignKey(
        VisitType,
        on_delete=models.PROTECT,
        related_name='visits'
    )
    
    # For visits not at a tracked centre
    location_description = models.CharField(
        max_length=200,
        blank=True,
        help_text='Description of visit location if not at a tracked centre'
    )
    
    notes = models.TextField(
        blank=True,
        help_text='Visit notes (include co-visitors here if applicable)'
    )
    
    # Flag for visits over 7 hours
    flagged_for_review = models.BooleanField(
        default=False,
        help_text='Automatically flagged if duration exceeds 7 hours'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-visit_date', '-start_time']
        verbose_name = 'Visit'
        verbose_name_plural = 'Visits'
        indexes = [
            models.Index(fields=['visit_date']),
            models.Index(fields=['child', 'visit_date']),
            models.Index(fields=['staff', 'visit_date']),
        ]
    
    def __str__(self):
        return f"{self.child.full_name} - {self.visit_date} ({self.staff.get_full_name()})"
    
    def clean(self):
        """Validate visit data."""
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError({
                    'end_time': 'End time must be after start time.'
                })
            
            # Check for 7+ hour duration
            duration = self.calculate_duration()
            if duration and duration >= 7.0:
                self.flagged_for_review = True
    
    def save(self, *args, **kwargs):
        """
        Override save to capture child's current centre as historical snapshot
        only on creation (not on updates).
        """
        if not self.pk and not self.centre:  # Only on creation and if centre not explicitly set
            self.centre = self.child.centre
        
        # Run validation
        self.full_clean()
        super().save(*args, **kwargs)
    
    def calculate_duration(self):
        """Calculate visit duration in hours."""
        if self.start_time and self.end_time:
            # Create datetime objects for today to calculate duration
            today = timezone.now().date()
            start_dt = timezone.datetime.combine(today, self.start_time)
            end_dt = timezone.datetime.combine(today, self.end_time)
            
            # Handle cases where end time is past midnight
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            
            duration_td = end_dt - start_dt
            return duration_td.total_seconds() / 3600  # Convert to hours
        return None
    
    @property
    def duration_hours(self):
        """Return duration as formatted string."""
        duration = self.calculate_duration()
        if duration:
            hours = int(duration)
            minutes = int((duration - hours) * 60)
            return f"{hours}h {minutes}m"
        return "N/A"
    
    @property
    def duration_decimal(self):
        """Return duration as decimal hours."""
        return self.calculate_duration()


class CaseloadAssignment(models.Model):
    """
    Tracks staff-to-child caseload assignments with full history.
    
    Non-caseload children will have no assignments.
    A child can have one primary staff member and multiple secondary staff.
    """
    
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='caseload_assignments'
    )
    
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='caseload_assignments'
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text='Primary staff member responsible for this child'
    )
    
    assigned_at = models.DateTimeField(default=timezone.now)
    unassigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date when assignment ended (null = still active)'
    )
    
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='caseload_assignments_made',
        help_text='Supervisor or admin who made this assignment'
    )
    
    class Meta:
        ordering = ['-assigned_at']
        verbose_name = 'Caseload Assignment'
        verbose_name_plural = 'Caseload Assignments'
        indexes = [
            models.Index(fields=['staff', 'unassigned_at']),
            models.Index(fields=['child', 'is_primary']),
        ]
    
    def __str__(self):
        status = "Primary" if self.is_primary else "Secondary"
        active = "Active" if not self.unassigned_at else f"Ended {self.unassigned_at.date()}"
        return f"{self.staff.get_full_name()} → {self.child.full_name} ({status}, {active})"
    
    def clean(self):
        """Validate caseload assignment."""
        # Check that staff user has staff role
        if hasattr(self.staff, 'role') and self.staff.role not in ['staff', 'supervisor', 'admin']:
            raise ValidationError({
                'staff': 'Only staff, supervisors, or admins can be assigned to caseloads.'
            })
        
        # Check for duplicate active primary assignments
        if self.is_primary and not self.unassigned_at:
            existing = CaseloadAssignment.objects.filter(
                child=self.child,
                is_primary=True,
                unassigned_at__isnull=True
            ).exclude(pk=self.pk)
            
            if existing.exists():
                raise ValidationError({
                    'is_primary': f'Child already has a primary staff member: {existing.first().staff.get_full_name()}'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
