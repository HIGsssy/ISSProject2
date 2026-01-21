"""
Django signals for automatic audit logging of key entities.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import AuditLog
from .middleware import get_current_user
import json


def track_field_changes(instance, created):
    """
    Compare current instance with database state to track field changes.
    Returns a dict of changed fields with their old and new values.
    """
    if created:
        return {}
    
    try:
        old_instance = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return {}
    
    changes = {}
    for field in instance._meta.fields:
        field_name = field.name
        
        # Skip auto-generated fields
        if field_name in ['id', 'created_at', 'updated_at']:
            continue
        
        old_value = getattr(old_instance, field_name)
        new_value = getattr(instance, field_name)
        
        # Handle FK fields
        if field.is_relation and old_value != new_value:
            changes[field_name] = {
                'old': str(old_value) if old_value else None,
                'new': str(new_value) if new_value else None
            }
        # Handle other fields
        elif old_value != new_value:
            changes[field_name] = {
                'old': str(old_value) if old_value is not None else None,
                'new': str(new_value) if new_value is not None else None
            }
    
    return changes


@receiver(post_save, sender='core.Child')
def audit_child_changes(sender, instance, created, **kwargs):
    """Audit log for Child model changes."""
    user = get_current_user()
    
    if created:
        AuditLog.log_action(
            user=user,
            entity=instance,
            action='created',
            new_value=f"Child {instance.full_name} created"
        )
    else:
        changes = track_field_changes(instance, created)
        for field_name, values in changes.items():
            AuditLog.log_action(
                user=user,
                entity=instance,
                action='updated',
                field_name=field_name,
                old_value=values['old'],
                new_value=values['new']
            )


@receiver(pre_delete, sender='core.Child')
def audit_child_deletion(sender, instance, **kwargs):
    """Audit log for Child deletion."""
    user = get_current_user()
    AuditLog.log_action(
        user=user,
        entity=instance,
        action='deleted',
        old_value=f"Child {instance.full_name} deleted"
    )


@receiver(post_save, sender='core.Centre')
def audit_centre_changes(sender, instance, created, **kwargs):
    """Audit log for Centre model changes."""
    user = get_current_user()
    
    if created:
        AuditLog.log_action(
            user=user,
            entity=instance,
            action='created',
            new_value=f"Centre {instance.name} created"
        )
    else:
        changes = track_field_changes(instance, created)
        for field_name, values in changes.items():
            AuditLog.log_action(
                user=user,
                entity=instance,
                action='updated',
                field_name=field_name,
                old_value=values['old'],
                new_value=values['new']
            )


@receiver(pre_delete, sender='core.Centre')
def audit_centre_deletion(sender, instance, **kwargs):
    """Audit log for Centre deletion."""
    user = get_current_user()
    AuditLog.log_action(
        user=user,
        entity=instance,
        action='deleted',
        old_value=f"Centre {instance.name} deleted"
    )


@receiver(post_save, sender='core.Visit')
def audit_visit_changes(sender, instance, created, **kwargs):
    """Audit log for Visit model changes."""
    user = get_current_user()
    
    if created:
        AuditLog.log_action(
            user=user,
            entity=instance,
            action='created',
            new_value=f"Visit for {instance.child.full_name} on {instance.visit_date} created"
        )
    else:
        # Track all changes to visit records (important for immutability tracking)
        changes = track_field_changes(instance, created)
        for field_name, values in changes.items():
            AuditLog.log_action(
                user=user,
                entity=instance,
                action='updated',
                field_name=field_name,
                old_value=values['old'],
                new_value=values['new'],
                metadata={
                    'warning': 'Visit record modified after creation',
                    'child': instance.child.full_name,
                    'visit_date': str(instance.visit_date)
                }
            )


@receiver(pre_delete, sender='core.Visit')
def audit_visit_deletion(sender, instance, **kwargs):
    """Audit log for Visit deletion."""
    user = get_current_user()
    AuditLog.log_action(
        user=user,
        entity=instance,
        action='deleted',
        old_value=f"Visit for {instance.child.full_name} on {instance.visit_date} deleted",
        metadata={
            'child': instance.child.full_name,
            'staff': instance.staff.get_full_name(),
            'visit_date': str(instance.visit_date),
            'duration': instance.duration_hours
        }
    )


@receiver(post_save, sender='core.CaseloadAssignment')
def audit_caseload_changes(sender, instance, created, **kwargs):
    """Audit log for CaseloadAssignment changes."""
    user = get_current_user()
    
    assignment_type = "Primary" if instance.is_primary else "Secondary"
    
    if created:
        AuditLog.log_action(
            user=user,
            entity=instance,
            action='created',
            new_value=f"{assignment_type} assignment: {instance.staff.get_full_name()} → {instance.child.full_name}",
            metadata={
                'staff': instance.staff.get_full_name(),
                'child': instance.child.full_name,
                'is_primary': instance.is_primary
            }
        )
    else:
        changes = track_field_changes(instance, created)
        for field_name, values in changes.items():
            AuditLog.log_action(
                user=user,
                entity=instance,
                action='updated',
                field_name=field_name,
                old_value=values['old'],
                new_value=values['new'],
                metadata={
                    'staff': instance.staff.get_full_name(),
                    'child': instance.child.full_name
                }
            )


@receiver(pre_delete, sender='core.CaseloadAssignment')
def audit_caseload_deletion(sender, instance, **kwargs):
    """Audit log for CaseloadAssignment deletion."""
    user = get_current_user()
    assignment_type = "Primary" if instance.is_primary else "Secondary"
    AuditLog.log_action(
        user=user,
        entity=instance,
        action='deleted',
        old_value=f"{assignment_type} assignment removed: {instance.staff.get_full_name()} → {instance.child.full_name}",
        metadata={
            'staff': instance.staff.get_full_name(),
            'child': instance.child.full_name,
            'is_primary': instance.is_primary
        }
    )


@receiver(post_save, sender='accounts.User')
def audit_user_changes(sender, instance, created, **kwargs):
    """Audit log for User model changes (admin actions only)."""
    user = get_current_user()
    
    # Only log if changed by another user (not self-updates like login)
    if user and user.pk != instance.pk:
        if created:
            AuditLog.log_action(
                user=user,
                entity=instance,
                action='created',
                new_value=f"User {instance.get_full_name()} created with role {instance.role}"
            )
        else:
            changes = track_field_changes(instance, created)
            # Only log significant changes
            significant_fields = ['role', 'is_active', 'is_staff', 'is_superuser']
            for field_name, values in changes.items():
                if field_name in significant_fields:
                    AuditLog.log_action(
                        user=user,
                        entity=instance,
                        action='updated',
                        field_name=field_name,
                        old_value=values['old'],
                        new_value=values['new'],
                        metadata={'target_user': instance.get_full_name()}
                    )
