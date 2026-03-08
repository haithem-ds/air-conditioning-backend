# Generated manually to fix existing client data

from django.db import migrations


def populate_client_email(apps, schema_editor):
    """
    Populate email field for existing clients
    """
    Client = apps.get_model('core', 'Client')
    
    for client in Client.objects.all():
        if not client.email:
            # Generate email from company name
            email = f"{client.company_name.lower().replace(' ', '').replace('-', '')}@example.com"
            client.email = email
            client.save()


def reverse_populate_client_email(apps, schema_editor):
    """
    Reverse operation - not needed
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_remove_user_from_client'),
    ]

    operations = [
        migrations.RunPython(
            populate_client_email,
            reverse_populate_client_email,
        ),
    ]

