"""
Core app signals for setting audit fields and age progression tracking.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Child, Visit, AgeProgressionEvent
from audit.middleware import get_current_user
from .utils.age_utils import calculate_age_in_months, get_age_group


@receiver(pre_save, sender=Child)
def set_child_user_fields(sender, instance, **kwargs):
    """Set created_by and updated_by fields for Child model."""
    user = get_current_user()
    if user:
        if not instance.pk:  # New instance
            instance.created_by = user
        instance.updated_by = user


@receiver(post_save, sender=Child)
def track_age_progression(sender, instance, created, **kwargs):
    """Detect age category changes and create AgeProgressionEvent records.
    
    Triggers when:
    1. Child's date_of_birth changes (unlikely but covered)
    2. Child transitions to a new age category (detected on save)
    
    Only creates events for upward transitions (younger → older category).
    """
    if not instance.date_of_birth:
        return
    
    # Calculate current age and category
    today = timezone.now().date()
    age_in_months = calculate_age_in_months(instance.date_of_birth, today)
    new_category = get_age_group(age_in_months)
    
    # Check if we already have a record for this child/date combo (avoid duplicates)
    existing_event = AgeProgressionEvent.objects.filter(
        child=instance,
        transition_date=today
    ).first()
    
    if existing_event:
        # Event already recorded today, skip
        return
    
    # Get the most recent age progression event for this child
    last_event = AgeProgressionEvent.objects.filter(
        child=instance
    ).order_by('-transition_date').first()
    
    if last_event is None:
        # No prior events, this is the first time we've tracked this child
        # We don't create an initial event - only track transitions
        return
    
    previous_category = last_event.new_category
    
    # Check if category changed (only upward transitions)
    if new_category != previous_category:
        category_order = ['infant', 'toddler', 'preschooler', 'jk_sk', 'school_age', 'other']
        new_idx = category_order.index(new_category) if new_category in category_order else -1
        prev_idx = category_order.index(previous_category) if previous_category in category_order else -1
        
        # Only create event if it's an actual progression (upward)
        if new_idx > prev_idx:
            AgeProgressionEvent.objects.create(
                child=instance,
                previous_category=previous_category,
                new_category=new_category,
                transition_date=today,
                age_in_months=age_in_months
            )
