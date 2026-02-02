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
from encrypted_model_fields.fields import (
    EncryptedCharField,
    EncryptedTextField,
    EncryptedEmailField
)


class Centre(models.Model):
    """Child care centres where inclusion support services are provided."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=200)
    
    # Address fields - encrypted
    address_line1 = EncryptedCharField(max_length=200, verbose_name='Address Line 1')
    address_line2 = EncryptedCharField(max_length=200, blank=True, verbose_name='Address Line 2')
    city = EncryptedCharField(max_length=100)
    province = EncryptedCharField(max_length=50, default='ON')
    postal_code = EncryptedCharField(max_length=10)
    
    phone = EncryptedCharField(max_length=20)
    
    # Primary contact - encrypted
    contact_name = EncryptedCharField(max_length=200, blank=True)
    contact_email = EncryptedEmailField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = EncryptedTextField(blank=True)
    
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
    
    OVERALL_STATUS_CHOICES = [
        ('active', 'Active'),
        ('discharged', 'Discharged'),
    ]
    
    CASELOAD_STATUS_CHOICES = [
        ('caseload', 'Caseload'),
        ('non_caseload', 'Non-Caseload'),
        ('awaiting_assignment', 'Awaiting Assignment'),
    ]
    
    # Basic information - encrypted
    first_name = EncryptedCharField(max_length=100)
    last_name = EncryptedCharField(max_length=100)
    date_of_birth = models.DateField()
    
    # Address fields - encrypted
    address_line1 = EncryptedCharField(max_length=200, blank=True, verbose_name='Address Line 1')
    address_line2 = EncryptedCharField(max_length=200, blank=True, verbose_name='Address Line 2')
    city = EncryptedCharField(max_length=100, blank=True)
    province = EncryptedCharField(max_length=50, blank=True, default='ON')
    postal_code = EncryptedCharField(max_length=10, blank=True)
    alternate_location = EncryptedTextField(blank=True, help_text='Location if different than mailing address')
    
    # Guardian 1 information - encrypted
    guardian1_name = EncryptedCharField(max_length=200, blank=True)
    guardian1_home_phone = EncryptedCharField(max_length=20, blank=True)
    guardian1_work_phone = EncryptedCharField(max_length=20, blank=True)
    guardian1_cell_phone = EncryptedCharField(max_length=20, blank=True)
    guardian1_email = EncryptedEmailField(blank=True)
    
    # Guardian 2 information - encrypted
    guardian2_name = EncryptedCharField(max_length=200, blank=True, verbose_name='Second Guardian Name')
    guardian2_home_phone = EncryptedCharField(max_length=20, blank=True, verbose_name='Second Guardian Home Phone')
    guardian2_work_phone = EncryptedCharField(max_length=20, blank=True, verbose_name='Second Guardian Work Phone')
    guardian2_cell_phone = EncryptedCharField(max_length=20, blank=True, verbose_name='Second Guardian Cell Phone')
    guardian2_email = EncryptedEmailField(blank=True, verbose_name='Second Guardian Email')
    
    # Referral source information - encrypted
    REFERRAL_SOURCE_CHOICES = [
        ('parent_guardian', 'Parent/Guardian'),
        ('other_agency', 'Other Agency'),
    ]
    referral_source_type = models.CharField(max_length=20, choices=REFERRAL_SOURCE_CHOICES, blank=True)
    referral_source_name = EncryptedCharField(max_length=200, blank=True, help_text='Name of person/contact referring')
    referral_source_phone = EncryptedCharField(max_length=20, blank=True)
    referral_agency_name = EncryptedCharField(max_length=200, blank=True, help_text='Agency name (if other_agency)')
    referral_agency_address = EncryptedTextField(blank=True, help_text='Agency address (if other_agency)')
    
    # Reason for referral - encrypted details
    referral_reason_cognitive = models.BooleanField(default=False)
    referral_reason_language = models.BooleanField(default=False)
    referral_reason_gross_motor = models.BooleanField(default=False)
    referral_reason_fine_motor = models.BooleanField(default=False)
    referral_reason_social_emotional = models.BooleanField(default=False)
    referral_reason_self_help = models.BooleanField(default=False)
    referral_reason_other = models.BooleanField(default=False)
    referral_reason_details = EncryptedTextField(blank=True, help_text='Details about referral reasons')
    
    # Program attendance
    attends_childcare = models.BooleanField(default=False, help_text='Attending licensed childcare')
    childcare_centre = models.ForeignKey(
        Centre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='childcare_children',
        help_text='Childcare centre (if attending)'
    )
    childcare_frequency = EncryptedCharField(max_length=100, blank=True, help_text='How often attending childcare')
    
    attends_earlyon = models.BooleanField(default=False, help_text='Attending EarlyON Child and Family Center')
    earlyon_centre = models.ForeignKey(
        Centre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='earlyon_children',
        help_text='EarlyON centre (if attending)'
    )
    earlyon_frequency = EncryptedCharField(max_length=100, blank=True, help_text='How often attending EarlyON')
    
    agency_continuing_involvement = models.BooleanField(default=False, help_text='Referring agency continuing involvement')
    referral_consent_on_file = models.BooleanField(default=False, help_text='Referral consent form on file')
    
    # Optional centre association (for caseload tracking)
    centre = models.ForeignKey(
        Centre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        help_text='Current centre for caseload (can be empty for non-caseload children)'
    )
    
    # Status fields
    overall_status = models.CharField(
        max_length=20,
        choices=OVERALL_STATUS_CHOICES,
        default='active',
        help_text='Overall status of the child'
    )
    
    caseload_status = models.CharField(
        max_length=20,
        choices=CASELOAD_STATUS_CHOICES,
        default='awaiting_assignment',
        help_text='Caseload assignment status'
    )
    
    on_hold = models.BooleanField(
        default=False,
        help_text='Indicates if child is temporarily on hold (not actively seen)'
    )
    
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date services ended (for discharged children)'
    )
    discharge_reason = EncryptedTextField(
        blank=True,
        default='',
        help_text='Reason for discharge (required when status is discharged)'
    )
    
    notes = EncryptedTextField(blank=True)
    
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
    def is_active(self):
        """Check if child is active (not discharged)."""
        return self.overall_status == 'active'
    
    @property
    def is_discharged(self):
        """Check if child is discharged."""
        return self.overall_status == 'discharged'
    
    @property
    def is_in_caseload(self):
        """Check if child is in caseload."""
        return self.caseload_status == 'caseload'
    
    @property
    def is_non_caseload(self):
        """Check if child is non-caseload."""
        return self.caseload_status == 'non_caseload'
    
    @property
    def is_awaiting_assignment(self):
        """Check if child is awaiting assignment."""
        return self.caseload_status == 'awaiting_assignment'
    
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
    
    For site visits (without a child), the child field is null.
    """
    
    child = models.ForeignKey(
        Child,
        on_delete=models.PROTECT,
        related_name='visits',
        null=True,
        blank=True,
        help_text='Child who received the visit (null for site visits)'
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
    
    # For visits not at a tracked centre - encrypted
    location_description = EncryptedCharField(
        max_length=200,
        blank=True,
        help_text='Description of visit location if not at a tracked centre'
    )
    
    notes = EncryptedTextField(
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
        if self.child:
            return f"{self.child.full_name} - {self.visit_date} ({self.staff.get_full_name()})"
        return f"Site Visit - {self.visit_date} ({self.staff.get_full_name()})"
    
    def clean(self):
        """Validate visit data."""
        # At least one of child or centre must be specified
        if not self.child and not self.centre:
            raise ValidationError('Either a child or a centre must be specified for the visit.')
        
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
        
        # Note: We don't check for duplicate primary assignments here anymore
        # The viewset handles automatically unassigning the old primary when creating a new one
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CommunityPartner(models.Model):
    """Community partners for referrals (e.g., therapists, social services, etc.)."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    PARTNER_TYPE_CHOICES = [
        ('speech_therapy', 'Speech Therapy'),
        ('occupational_therapy', 'Occupational Therapy'),
        ('physical_therapy', 'Physical Therapy'),
        ('behavioural_therapy', 'Behavioural Therapy'),
        ('social_services', 'Social Services'),
        ('medical', 'Medical/Healthcare'),
        ('educational', 'Educational Services'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    partner_type = models.CharField(max_length=50, choices=PARTNER_TYPE_CHOICES, default='other')
    
    # Contact information - encrypted
    contact_name = EncryptedCharField(max_length=200, blank=True, verbose_name='Primary Contact')
    phone = EncryptedCharField(max_length=20, blank=True)
    email = EncryptedEmailField(blank=True)
    
    # Address fields - encrypted
    address_line1 = EncryptedCharField(max_length=200, blank=True, verbose_name='Address Line 1')
    address_line2 = EncryptedCharField(max_length=200, blank=True, verbose_name='Address Line 2')
    city = EncryptedCharField(max_length=100, blank=True)
    province = EncryptedCharField(max_length=50, blank=True, default='ON')
    postal_code = EncryptedCharField(max_length=10, blank=True)
    
    website = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = EncryptedTextField(blank=True, help_text='General notes about this partner')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Community Partner'
        verbose_name_plural = 'Community Partners'
    
    def __str__(self):
        return f"{self.name} ({self.get_partner_type_display()})"


class Referral(models.Model):
    """Referrals from children to community partners."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    child = models.ForeignKey(
        Child,
        on_delete=models.PROTECT,
        related_name='referrals'
    )
    community_partner = models.ForeignKey(
        CommunityPartner,
        on_delete=models.PROTECT,
        related_name='referrals'
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='referrals_made'
    )
    
    referral_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    reason = EncryptedTextField(help_text='Reason for referral')
    notes = EncryptedTextField(blank=True, help_text='Additional notes or follow-up information')
    
    # Tracking fields
    status_updated_at = models.DateTimeField(null=True, blank=True)
    status_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral_status_updates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-referral_date']
        verbose_name = 'Referral'
        verbose_name_plural = 'Referrals'
        indexes = [
            models.Index(fields=['child', 'referral_date']),
            models.Index(fields=['community_partner', 'status']),
        ]
    
    def __str__(self):
        return f"{self.child.full_name} → {self.community_partner.name} ({self.referral_date})"


# Signal handlers for auto-updating caseload_status
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver


@receiver(post_save, sender=CaseloadAssignment)
def update_child_caseload_status_on_assign(sender, instance, created, **kwargs):
    """Auto-update child caseload_status when staff is assigned."""
    if instance.unassigned_at is None:  # Active assignment
        child = instance.child
        # Only update if child is active and not already in caseload
        if child.overall_status == 'active' and child.caseload_status != 'caseload':
            child.caseload_status = 'caseload'
            child.save(update_fields=['caseload_status'])


@receiver(pre_save, sender=CaseloadAssignment)
def update_child_caseload_status_on_unassign(sender, instance, **kwargs):
    """Update child caseload_status when assignment is unassigned."""
    if instance.pk:  # Existing assignment
        try:
            old_instance = CaseloadAssignment.objects.get(pk=instance.pk)
            # If being unassigned (was None, now has value)
            if old_instance.unassigned_at is None and instance.unassigned_at is not None:
                child = instance.child
                # Check if child has any other active assignments
                other_assignments = child.caseload_assignments.filter(
                    unassigned_at__isnull=True
                ).exclude(pk=instance.pk).exists()
                
                if not other_assignments and child.overall_status == 'active' and child.caseload_status == 'caseload':
                    child.caseload_status = 'awaiting_assignment'
                    child.save(update_fields=['caseload_status'])
        except CaseloadAssignment.DoesNotExist:
            pass


@receiver(post_delete, sender=CaseloadAssignment)
def update_child_caseload_status_on_delete(sender, instance, **kwargs):
    """Update child caseload_status when assignment is deleted."""
    child = instance.child
    # Check if child has any other active assignments
    has_assignments = child.caseload_assignments.filter(unassigned_at__isnull=True).exists()
    
    if not has_assignments and child.overall_status == 'active' and child.caseload_status == 'caseload':
        child.caseload_status = 'awaiting_assignment'
        child.save(update_fields=['caseload_status'])
