from django.db import migrations, models


def migrate_status_data(apps, schema_editor):
    """Migrate existing status data to new fields."""
    Child = apps.get_model('core', 'Child')
    
    for child in Child.objects.all():
        old_status = child.status
        
        # Set overall_status
        if old_status == 'discharged':
            child.overall_status = 'discharged'
        else:
            child.overall_status = 'active'
        
        # Set caseload_status based on old status
        if old_status == 'non_caseload':
            child.caseload_status = 'non_caseload'
        elif old_status in ['active', 'on_hold']:
            # Check if child has active caseload assignments
            has_assignment = child.caseload_assignments.filter(
                unassigned_at__isnull=True
            ).exists()
            child.caseload_status = 'caseload' if has_assignment else 'awaiting_assignment'
        elif old_status == 'discharged':
            child.caseload_status = 'non_caseload'
        
        # Set on_hold flag
        child.on_hold = (old_status == 'on_hold')
        
        child.save(update_fields=['overall_status', 'caseload_status', 'on_hold'])


def reverse_migrate_status_data(apps, schema_editor):
    """Reverse migration - restore old status from new fields."""
    Child = apps.get_model('core', 'Child')
    
    for child in Child.objects.all():
        if child.overall_status == 'discharged':
            child.status = 'discharged'
        elif child.on_hold:
            child.status = 'on_hold'
        elif child.caseload_status == 'non_caseload':
            child.status = 'non_caseload'
        else:
            child.status = 'active'
        
        child.save(update_fields=['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_rename_core_referr_child_i_7a3f92_idx_core_referr_child_i_2736d2_idx_and_more'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='child',
            name='overall_status',
            field=models.CharField(
                choices=[('active', 'Active'), ('discharged', 'Discharged')],
                default='active',
                max_length=20,
                help_text='Overall status of the child'
            ),
        ),
        migrations.AddField(
            model_name='child',
            name='caseload_status',
            field=models.CharField(
                choices=[
                    ('caseload', 'Caseload'),
                    ('non_caseload', 'Non-Caseload'),
                    ('awaiting_assignment', 'Awaiting Assignment')
                ],
                default='awaiting_assignment',
                max_length=20,
                help_text='Caseload assignment status'
            ),
        ),
        migrations.AddField(
            model_name='child',
            name='on_hold',
            field=models.BooleanField(
                default=False,
                help_text='Indicates if child is temporarily on hold (not actively seen)'
            ),
        ),
        
        # Migrate data
        migrations.RunPython(migrate_status_data, reverse_migrate_status_data),
        
        # Add indexes for new fields
        migrations.AddIndex(
            model_name='child',
            index=models.Index(fields=['overall_status'], name='core_child_overall_idx'),
        ),
        migrations.AddIndex(
            model_name='child',
            index=models.Index(fields=['caseload_status'], name='core_child_caseload_idx'),
        ),
        migrations.AddIndex(
            model_name='child',
            index=models.Index(fields=['on_hold'], name='core_child_on_hold_idx'),
        ),
        
        # Remove old index
        migrations.RemoveIndex(
            model_name='child',
            name='core_child_status_f8bbac_idx',
        ),
        
        # Remove old status field
        migrations.RemoveField(
            model_name='child',
            name='status',
        ),
    ]
