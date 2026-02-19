# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_themesetting_header_bg_color'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgeProgressionEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_category', models.CharField(choices=[('infant', 'Infant'), ('toddler', 'Toddler'), ('preschooler', 'Preschooler'), ('jk_sk', 'JK/SK'), ('school_age', 'School Age'), ('other', 'Other')], help_text='Age category before transition', max_length=20)),
                ('new_category', models.CharField(choices=[('infant', 'Infant'), ('toddler', 'Toddler'), ('preschooler', 'Preschooler'), ('jk_sk', 'JK/SK'), ('school_age', 'School Age'), ('other', 'Other')], help_text='Age category after transition', max_length=20)),
                ('transition_date', models.DateField(help_text='Date the transition occurred')),
                ('age_in_months', models.DecimalField(decimal_places=2, help_text="Child's age in months at transition", max_digits=5)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('child', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='age_progression_events', to='core.child')),
            ],
            options={
                'verbose_name': 'Age Progression Event',
                'verbose_name_plural': 'Age Progression Events',
                'ordering': ['-transition_date'],
                'indexes': [
                    models.Index(fields=['child', 'transition_date'], name='core_agepro_child_i_idx'),
                    models.Index(fields=['transition_date'], name='core_agepro_transit_idx'),
                ],
            },
        ),
    ]
