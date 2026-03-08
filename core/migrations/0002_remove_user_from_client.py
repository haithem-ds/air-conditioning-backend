# Generated manually to remove user relationship from Client model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='client',
            name='user',
        ),
        migrations.AddField(
            model_name='client',
            name='email',
            field=models.EmailField(help_text='Company email address', max_length=254, null=True, blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='client',
            name='phone_number',
            field=models.CharField(blank=True, help_text='Company phone number', max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='billing_address',
            field=models.TextField(help_text='Billing address for the company'),
        ),
        migrations.AlterField(
            model_name='client',
            name='contact_person',
            field=models.CharField(help_text='Primary contact person at the company', max_length=255),
        ),
    ]
