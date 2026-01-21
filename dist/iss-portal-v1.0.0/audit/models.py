"""
Audit logging system for tracking all changes to key entities.
"""
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType


class AuditLog(models.Model):
    """
    Comprehensive audit log for tracking all data changes.
    
    Tracks:
    - Who made the change
    - What entity was changed
    - When the change occurred
    - What fields changed and their old/new values
    """
    
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('bulk_update', 'Bulk Update'),
    ]
    
    # Who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    
    # What
    entity_type = models.CharField(
        max_length=100,
        help_text='Model name (e.g., Child, Visit, CaseloadAssignment)'
    )
    entity_id = models.IntegerField(
        help_text='Primary key of the entity'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Field-level changes
    field_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name of the field that changed'
    )
    old_value = models.TextField(
        blank=True,
        help_text='Previous value (JSON for complex fields)'
    )
    new_value = models.TextField(
        blank=True,
        help_text='New value (JSON for complex fields)'
    )
    
    # Additional context
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional context (e.g., bulk operation details)'
    )
    
    # When
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log Entry'
        verbose_name_plural = 'Audit Log Entries'
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        user_name = self.user.get_full_name() if self.user else 'System'
        return f"{user_name} {self.action} {self.entity_type} #{self.entity_id} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, user, entity, action, field_name='', old_value='', new_value='', metadata=None):
        """
        Convenience method to create audit log entries.
        
        Args:
            user: User who performed the action
            entity: Model instance that was changed
            action: Action type (created, updated, deleted)
            field_name: Name of the field that changed
            old_value: Previous value
            new_value: New value
            metadata: Additional context dictionary
        """
        entity_type = entity.__class__.__name__
        entity_id = entity.pk if entity.pk else 0
        
        return cls.objects.create(
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else '',
            new_value=str(new_value) if new_value is not None else '',
            metadata=metadata or {}
        )
