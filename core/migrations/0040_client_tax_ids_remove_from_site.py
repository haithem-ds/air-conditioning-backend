# Move NIF / NIS / RC from Site to Client (optional fields); copy values from first site per client.

from django.db import migrations, models


def copy_site_tax_ids_to_client(apps, schema_editor):
    Client = apps.get_model('core', 'Client')
    Site = apps.get_model('core', 'Site')
    placeholders = frozenset({'NIF000000000', 'NIS000000000', 'RC000000000'})

    def good(val):
        v = (val or '').strip()
        return v if v and v not in placeholders else ''

    for client in Client.objects.all():
        site = Site.objects.filter(client_id=client.pk).order_by('id').first()
        if not site:
            continue
        updates = []
        if not (client.nif or '').strip():
            sn = good(site.nif)
            if sn:
                client.nif = sn
                updates.append('nif')
        if not (client.nis or '').strip():
            sn = good(site.nis)
            if sn:
                client.nis = sn
                updates.append('nis')
        if not (client.rc or '').strip():
            sn = good(site.rc)
            if sn:
                client.rc = sn
                updates.append('rc')
        if updates:
            client.save(update_fields=updates)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_rename_sael_to_sarl_status_juridique'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='nif',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Fiscal identification number (optional)',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='nis',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Statistical identification number (optional)',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='rc',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Commercial register number (optional)',
                max_length=50,
            ),
        ),
        migrations.RunPython(copy_site_tax_ids_to_client, noop_reverse),
        migrations.RemoveField(model_name='site', name='nif'),
        migrations.RemoveField(model_name='site', name='nis'),
        migrations.RemoveField(model_name='site', name='rc'),
    ]
