# Data migration: legal status code SAEL -> SARL (matches updated Client.STATUS_JURIDIQUE_CHOICES)

from django.db import migrations


def sael_to_sarl(apps, schema_editor):
    Client = apps.get_model('core', 'Client')
    Client.objects.filter(status_juridique='SAEL').update(status_juridique='SARL')


def sarl_to_sael(apps, schema_editor):
    Client = apps.get_model('core', 'Client')
    Client.objects.filter(status_juridique='SARL').update(status_juridique='SAEL')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_devicetoken'),
    ]

    operations = [
        migrations.RunPython(sael_to_sarl, sarl_to_sael),
    ]
