"""
Migration for ThemeSetting model - UI theme customization.
Adds singleton theme configuration table with color and image fields.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_remove_child_core_child_last_na_66f284_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThemeSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('primary_color', models.CharField(default='#3b82f6', help_text='Primary brand color (hex format)', max_length=7)),
                ('secondary_color', models.CharField(default='#8b5cf6', help_text='Secondary color (hex format)', max_length=7)),
                ('accent_color', models.CharField(default='#10b981', help_text='Accent/success color (hex format)', max_length=7)),
                ('success_color', models.CharField(default='#10b981', help_text='Success color (hex format)', max_length=7)),
                ('warning_color', models.CharField(default='#f59e0b', help_text='Warning color (hex format)', max_length=7)),
                ('danger_color', models.CharField(default='#ef4444', help_text='Danger/error color (hex format)', max_length=7)),
                ('logo_image', models.ImageField(blank=True, help_text='Logo image displayed in navbar (recommended: 40x40px)', upload_to='theme/')),
                ('favicon', models.ImageField(blank=True, help_text='Favicon image (recommended: 32x32px or square)', upload_to='theme/')),
                ('background_image', models.ImageField(blank=True, help_text='Optional background image', upload_to='theme/')),
                ('site_title', models.CharField(default='Inclusion Support Services Portal', help_text='Site title shown in navbar and page title', max_length=100)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Theme Settings',
                'verbose_name_plural': 'Theme Settings',
            },
        ),
    ]
