from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from core.models import Organization

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a new organization with an admin user (empty tenant space).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Unique organization slug')
        parser.add_argument('--name', required=True, help='Organization display name')
        parser.add_argument('--admin-username', required=True)
        parser.add_argument('--admin-password', required=True)
        parser.add_argument('--admin-email', default='')

    def handle(self, *args, **options):
        org, created = Organization.objects.get_or_create(
            slug=options['slug'],
            defaults={'name': options['name'], 'is_active': True},
        )
        if not created:
            org.name = options['name']
            org.is_active = True
            org.save(update_fields=['name', 'is_active', 'updated_at'])

        username = options['admin_username']
        if User.objects.filter(username=username).exists():
            self.stderr.write(self.style.ERROR(f'User {username} already exists'))
            return

        User.objects.create(
            username=username,
            email=options['admin_email'] or f'{username}@pika.local',
            password=make_password(options['admin_password']),
            role='ADMIN',
            is_staff=True,
            is_active=True,
            organization=org,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Organization "{org.name}" ({org.slug}) ready. Admin user: {username}'
        ))
