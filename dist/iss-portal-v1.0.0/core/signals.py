"""
Core app signals for setting audit fields.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Child, Visit
from audit.middleware import get_current_user


@receiver(pre_save, sender=Child)
def set_child_user_fields(sender, instance, **kwargs):
    """Set created_by and updated_by fields for Child model."""
    user = get_current_user()
    if user:
        if not instance.pk:  # New instance
            instance.created_by = user
        instance.updated_by = user
