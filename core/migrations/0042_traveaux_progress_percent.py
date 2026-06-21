from django.db import migrations, models


def backfill_progress_percent(apps, schema_editor):
    for model_name in ('Traveaux', 'MaintenanceTraveaux'):
        Model = apps.get_model('core', model_name)
        for row in Model.objects.all().iterator():
            if row.quantity and row.quantity > 0:
                raw = round(row.quantity_completed / row.quantity * 100)
            else:
                raw = 0
            row.progress_percent = int(round(max(0, min(100, raw)) / 10) * 10)
            row.save(update_fields=['progress_percent'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_maintenancetraveaux_is_secondary_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='traveaux',
            name='progress_percent',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Work progress as percentage (0-100, stored in 10% steps)',
            ),
        ),
        migrations.AddField(
            model_name='maintenancetraveaux',
            name='progress_percent',
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text='Work progress as percentage (0-100, stored in 10% steps)',
            ),
        ),
        migrations.RunPython(backfill_progress_percent, migrations.RunPython.noop),
    ]
