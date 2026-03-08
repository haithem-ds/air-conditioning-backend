# Generated manually to make email field required after data population

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_fix_client_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='email',
            field=models.EmailField(help_text='Company email address', max_length=254),
        ),
    ]

