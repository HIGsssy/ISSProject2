# Generated manually to add missing alternate_location field

from django.db import migrations
import encrypted_model_fields.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_restructure_child_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='alternate_location',
            field=encrypted_model_fields.fields.EncryptedTextField(blank=True, help_text='Location if different than mailing address'),
        ),
    ]
