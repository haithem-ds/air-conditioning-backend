# Generated manually to remove user relationship from Technician model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_make_email_required'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='technician',
            name='user',
        ),
        migrations.AddField(
            model_name='technician',
            name='first_name',
            field=models.CharField(default='John', help_text="Technician's first name", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='technician',
            name='last_name',
            field=models.CharField(default='Doe', help_text="Technician's last name", max_length=150),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='technician',
            name='email',
            field=models.EmailField(default='technician@example.com', help_text="Technician's email address", max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='technician',
            name='phone_number',
            field=models.CharField(blank=True, help_text="Technician's phone number", max_length=15, null=True),
        ),
    ]

