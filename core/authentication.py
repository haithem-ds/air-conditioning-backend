from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Client, Technician

User = get_user_model()

class ClientAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend for Client model
    Allows clients to login directly with their email and password
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
            
        try:
            # Try to find client by email
            client = Client.objects.get(email=username)
            
            # Check if password is correct
            if client.check_password(password):
                # Create or get a User record for this client
                user, created = User.objects.get_or_create(
                    username=f"client_{client.id}",
                    defaults={
                        'email': client.email,
                        'first_name': client.name,
                        'last_name': '',
                        'role': 'CLIENT',
                        'is_active': True,
                        'is_staff': False,
                        'is_superuser': False,
                    }
                )
                
                # Update user info if client info changed
                if not created:
                    user.email = client.email
                    user.first_name = client.name
                    user.role = 'CLIENT'
                    user.is_active = True
                    user.save()
                
                # Store reference to actual client
                user._client = client
                return user
                
        except Client.DoesNotExist:
            return None
                    
        return None
    
    def get_user(self, user_id):
        try:
            # Try to get user by ID
            user = User.objects.get(pk=user_id)
            
            # If this is a client user, attach the client object
            if user.username.startswith('client_'):
                try:
                    client_id = int(user.username.replace('client_', ''))
                    client = Client.objects.get(pk=client_id)
                    user._client = client
                except (Client.DoesNotExist, ValueError):
                    pass
            
            return user
        except User.DoesNotExist:
            return None

class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with either username or email
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
            
        try:
            # Try to find user by username or email
            user = User.objects.get(
                Q(username=username) | Q(email=username)
            )
            
            # Check if password is correct
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            return None
            
        except User.MultipleObjectsReturned:
            # If multiple users found, try username first, then email
            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=username)
                    if user.check_password(password):
                        return user
                except User.DoesNotExist:
                    return None
                    
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class TechnicianAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend for Technician model
    Allows technicians to login directly with their email/identification_number and password
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
            
        try:
            # Try to find technician by email or identification_number
            technician = Technician.objects.get(
                Q(email=username) | Q(identification_number=username)
            )
            
            # Check if password is correct
            if technician.check_password(password):
                # Ensure user account exists for this technician
                if not technician.user:
                    # Create user if doesn't exist
                    username_for_user = f"tech_{technician.id}" if technician.id else f"tech_{technician.identification_number}"
                    user = User.objects.create(
                        username=username_for_user,
                        email=technician.email or f"tech{technician.id}@pika.local",
                        first_name=technician.first_name,
                        last_name=technician.last_name,
                        role='TECHNICIAN',
                        is_active=True,
                        is_staff=False,
                        is_superuser=False,
                    )
                    user.set_password(technician.password if technician.password else '123')
                    user.save()
                    technician.user = user
                    technician.save()
                    return user
                else:
                    # Update user info
                    technician.user.email = technician.email or technician.user.email
                    technician.user.first_name = technician.first_name
                    technician.user.last_name = technician.last_name
                    technician.user.role = 'TECHNICIAN'
                    technician.user.is_active = True
                    technician.user.save()
                    return technician.user
                
        except Technician.DoesNotExist:
            return None
        except Technician.MultipleObjectsReturned:
            # If multiple technicians found, try email first, then identification_number
            try:
                technician = Technician.objects.get(email=username)
                if technician.check_password(password):
                    if technician.user:
                        return technician.user
            except Technician.DoesNotExist:
                try:
                    technician = Technician.objects.get(identification_number=username)
                    if technician.check_password(password):
                        if technician.user:
                            return technician.user
                except Technician.DoesNotExist:
                    return None
                    
        return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            # If this is a technician user, attach the technician object
            if hasattr(user, 'technician_profile'):
                try:
                    user._technician = user.technician_profile
                except Technician.DoesNotExist:
                    pass
            return user
        except User.DoesNotExist:
            return None
