# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import encrypted_model_fields.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_ageprogressionevent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', encrypted_model_fields.fields.EncryptedTextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='case_notes',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('child', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='case_notes',
                    to='core.child',
                )),
                ('deleted_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='deleted_case_notes',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='edited_case_notes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Case Note',
                'verbose_name_plural': 'Case Notes',
                'ordering': ['-created_at'],
            },
        ),
    ]
