# Generated migration file

from django.db import migrations
import colorfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_themesetting'),
    ]

    operations = [
        migrations.AddField(
            model_name='themesetting',
            name='header_bg_color',
            field=colorfield.fields.ColorField(default='#ffffff', help_text='Header/navbar background color', max_length=18),
        ),
    ]
