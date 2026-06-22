"""Multi-tenant helpers: scope data by organization."""

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from .models import Client


def client_for_user(user):
    """Resolve the Client record linked to a CLIENT-role user."""
    if user is None or user.role != 'CLIENT':
        return None
    try:
        return Client.objects.get(user=user)
    except Client.DoesNotExist:
        pass
    username = getattr(user, 'username', '') or ''
    if username.startswith('client_'):
        try:
            return Client.objects.get(pk=int(username.replace('client_', '')))
        except (ValueError, Client.DoesNotExist):
            return None
    return None


def get_user_organization(user):
    """Resolve the Organization for the authenticated user."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None

    if getattr(user, 'organization_id', None):
        return user.organization

    if user.role == 'CLIENT':
        client = client_for_user(user)
        return client.organization if client else None

    if user.role == 'TECHNICIAN':
        try:
            return user.technician_profile.organization
        except Exception:
            return None

    return None


def scope_by_tenant(queryset, user, path='organization'):
    """Filter queryset to the user's organization."""
    org = get_user_organization(user)
    if org is None:
        return queryset.none()
    return queryset.filter(**{path: org})


def scope_users_by_tenant(queryset, user):
    org = get_user_organization(user)
    if org is None:
        return queryset.none()
    return queryset.filter(
        Q(organization=org)
        | Q(client_profile__organization=org)
        | Q(technician_profile__organization=org)
    ).distinct()


def require_organization(user):
    org = get_user_organization(user)
    if org is None:
        raise PermissionDenied('No organization linked to this account')
    return org


def assert_client_in_organization(client, user):
    org = require_organization(user)
    if client.organization_id != org.id:
        raise PermissionDenied('Client belongs to another organization')
