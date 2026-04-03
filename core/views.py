from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.db.models import Q
from datetime import datetime, timedelta
from collections import defaultdict
from calendar import monthrange
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import json
from .models import Client, Site, Technician, TeamGroup, Equipment, ClientEquipment, TechnicianGroup, Contract, ProjectInstallation, ProjectInstallationPDF, ProjectInstallationFacture, ProjectInstallationPV, ProjectInstallationQuote, Traveaux, TraveauxReport, ProjectMaintenance, ProjectMaintenancePDF, ProjectMaintenanceFacture, ProjectMaintenancePV, ProjectMaintenanceQuote, MaintenanceTraveaux, MaintenanceTraveauxReport, DeviceToken
from .serializers import (
    UserSerializer, UserCreateSerializer, ClientSerializer,
    SiteSerializer, TechnicianSerializer,
    TeamGroupSerializer, TeamGroupListSerializer, EquipmentSerializer,
    ClientEquipmentSerializer, TechnicianGroupSerializer, TechnicianGroupListSerializer,
    ContractSerializer, ContractListSerializer, ProjectInstallationSerializer, ProjectInstallationListSerializer,
    ProjectInstallationPDFSerializer, ProjectInstallationFactureSerializer, ProjectInstallationPVSerializer, ProjectInstallationQuoteSerializer,
    TraveauxSerializer, TraveauxListSerializer, TraveauxReportSerializer,
    ProjectMaintenanceSerializer, ProjectMaintenanceListSerializer,
    ProjectMaintenancePDFSerializer, ProjectMaintenanceFactureSerializer, ProjectMaintenancePVSerializer, ProjectMaintenanceQuoteSerializer,
    MaintenanceTraveauxSerializer, MaintenanceTraveauxListSerializer, MaintenanceTraveauxReportSerializer,
    DeviceTokenSerializer
)

User = get_user_model()


def create_maintenance_projects_automatically(contract):
    """
    Automatically create maintenance projects based on contract specifications.
    
    This function:
    - Calculates the total number of projects needed (years × frequency)
    - Gets all equipment and sites from the contract
    - Distributes projects evenly across the contract duration
    - Considers existing maintenance projects to balance months
    - Creates ProjectMaintenance instances with balanced start/end dates
    """
    if not contract.create_project_maintenance_automatically:
        return []
    
    if contract.contract_type != 'MAINTENANCE':
        return []
    
    if not contract.contract_duration_years or not contract.maintenance_frequency_per_year:
        return []
    
    # Calculate total number of projects
    total_projects = contract.contract_duration_years * contract.maintenance_frequency_per_year
    
    if total_projects == 0:
        return []
    
    # Get contract equipment and sites
    contract_equipment = contract.equipment.all()
    contract_sites = contract.sites.all()
    
    if not contract_equipment.exists() or not contract_sites.exists():
        return []
    
    # Get existing maintenance projects to balance load
    existing_projects = ProjectMaintenance.objects.filter(
        start_date__gte=contract.starting_date,
        finish_date__lte=contract.ending_date
    ).order_by('start_date')
    
    # Count existing projects per month
    month_counts = defaultdict(int)
    for proj in existing_projects:
        month_key = (proj.start_date.year, proj.start_date.month)
        month_counts[month_key] += 1
    
    # Calculate project distribution
    start_date = contract.starting_date
    end_date = contract.ending_date
    
    # Calculate days per project (roughly)
    total_days = (end_date - start_date).days
    days_per_project = total_days / total_projects
    
    created_projects = []
    
    # Generate project dates with balancing
    # First, calculate ideal evenly-spaced dates
    ideal_dates = []
    for i in range(total_projects):
        target_days = (i + 0.5) * days_per_project
        target_date = start_date + timedelta(days=int(target_days))
        ideal_dates.append(target_date)
    
    # Group ideal dates into months and balance
    project_dates = []
    total_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    avg_per_month = total_projects / max(1, total_months)
    
    for ideal_date in ideal_dates:
        # Round to month start for balancing
        month_start = ideal_date.replace(day=1)
        month_key = (month_start.year, month_start.month)
        
        # Check current month count
        current_count = month_counts.get(month_key, 0)
        
        # If month is too loaded, try to find a better month
        if current_count > avg_per_month * 1.2:  # Allow 20% above average
            # Check previous month
            prev_month_year = month_start.year
            prev_month_month = month_start.month - 1
            if prev_month_month < 1:
                prev_month_month = 12
                prev_month_year -= 1
            prev_month = datetime(prev_month_year, prev_month_month, 1).date()
            prev_key = (prev_month.year, prev_month.month)
            
            if prev_month >= start_date and month_counts.get(prev_key, 0) < avg_per_month:
                month_start = prev_month
                month_key = prev_key
            else:
                # Check next month
                next_month_year = month_start.year
                next_month_month = month_start.month + 1
                if next_month_month > 12:
                    next_month_month = 1
                    next_month_year += 1
                next_month = datetime(next_month_year, next_month_month, 1).date()
                next_key = (next_month.year, next_month.month)
                
                if next_month <= end_date and month_counts.get(next_key, 0) < avg_per_month:
                    month_start = next_month
                    month_key = next_key
        
        # Increment month count for this month
        month_counts[month_key] += 1
        
        # Set project dates to span one month
        project_start = month_start
        # Calculate end of month
        days_in_month = monthrange(month_start.year, month_start.month)[1]
        project_end = datetime(month_start.year, month_start.month, days_in_month).date()
        
        # Ensure project_end doesn't exceed contract end_date
        if project_end > end_date:
            project_end = end_date
        
        # Ensure project_start is not before contract start_date
        if project_start < start_date:
            project_start = start_date
        
        project_dates.append((project_start, project_end))
    
    # Sort dates to ensure chronological order
    project_dates.sort(key=lambda x: x[0])
    
    # Create projects
    for idx, (proj_start, proj_end) in enumerate(project_dates, 1):
        project = ProjectMaintenance.objects.create(
            contract=contract,
            client=contract.client,
            project_name=f"Maintenance {contract.code} - Project {idx}/{total_projects}",
            description=f"Automated maintenance project {idx} of {total_projects} for contract {contract.code}. "
                      f"Frequency: {contract.maintenance_frequency_per_year} per year, "
                      f"Duration: {contract.contract_duration_years} year(s)",
            start_date=proj_start,
            finish_date=proj_end,
            complexity='NORMAL',
            is_active=True
        )
        
        # Assign equipment and sites
        project.equipment.set(contract_equipment)
        project.sites.set(contract_sites)
        
        created_projects.append(project)
    
    return created_projects


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model with role-based permissions
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """
        Filter users based on role and permissions
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return User.objects.all()
        elif user.role == 'CLIENT':
            return User.objects.filter(role__in=['CLIENT', 'TECHNICIAN'])
        elif user.role == 'TECHNICIAN':
            return User.objects.filter(role__in=['TECHNICIAN'])
        else:
            return User.objects.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user profile
        """
        # Refresh user from database with related objects
        user = User.objects.select_related('technician_profile').get(pk=request.user.pk)
        
        # If user is a technician, ensure user account is synced with technician data
        if user.role == 'TECHNICIAN':
            try:
                technician = user.technician_profile
                if technician:
                    # Sync technician data to user account
                    needs_save = False
                    if (not user.first_name or user.first_name == '') and technician.first_name:
                        user.first_name = technician.first_name
                        needs_save = True
                    if (not user.last_name or user.last_name == '') and technician.last_name:
                        user.last_name = technician.last_name
                        needs_save = True
                    if (not user.email or user.email == '') and technician.email:
                        user.email = technician.email
                        needs_save = True
                    if user.role != 'TECHNICIAN':
                        user.role = 'TECHNICIAN'
                        needs_save = True
                    if not user.is_active:
                        user.is_active = True
                        needs_save = True
                    
                    if needs_save:
                        user.save()
            except Technician.DoesNotExist:
                pass
            except AttributeError:
                pass
        
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """
        Update current user profile
        """
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Client model
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Admin UI loads the full list in one request; default PAGE_SIZE pagination hid
    # newly created clients (highest id) off page 1, so they vanished after refresh.
    pagination_class = None

    def get_queryset(self):
        """
        Filter clients based on user role and search query
        """
        user = self.request.user
        queryset = Client.objects.all().order_by('-created_at', '-id')
        
        # Apply search filter if search parameter is provided
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(code_client__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'CLIENT':
            # For now, return all clients since we removed user relationship
            # In the future, you might want to add a different filtering mechanism
            return queryset
        elif user.role == 'TECHNICIAN':
            # Technicians can view all clients (for service assignments and site information)
            return queryset
        else:
            return Client.objects.none()
    
    @action(detail=True, methods=['get'])
    def sites(self, request, pk=None):
        """
        Get all sites for a specific client
        """
        client = self.get_object()
        sites = client.sites.all()
        serializer = SiteSerializer(sites, many=True)
        return Response(serializer.data)


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Site model
    """
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter sites based on user role and client access
        """
        user = self.request.user
        queryset = Site.objects.all()
        
        # Apply client filter if provided
        client_id_param = self.request.query_params.get('client')
        client_id = None
        
        if client_id_param:
            try:
                client_id = int(client_id_param)
                queryset = queryset.filter(client_id=client_id)
            except ValueError:
                pass  # Invalid client_id, will be handled below
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'CLIENT':
            # Extract client ID from username (format: client_<id>) if not provided in query params
            if not client_id and user.username.startswith('client_'):
                try:
                    client_id = int(user.username.replace('client_', ''))
                    queryset = queryset.filter(client_id=client_id)
                except ValueError:
                    return Site.objects.none()
            elif not client_id:
                # If no client_id found, return no sites for security
                return Site.objects.none()
            # If client_id was provided in query params, it's already filtered above
            return queryset
        elif user.role == 'TECHNICIAN':
            # Technicians can view all sites (for service assignments)
            return queryset
        else:
            return Site.objects.none()
    
    def perform_create(self, serializer):
        """
        Ensure only clients can create sites for their own company
        """
        user = self.request.user
        if user.role == 'CLIENT':
            # Since Client model no longer has direct user relationship,
            # we'll need to get the client from the request data or handle differently
            # For now, let the serializer handle it based on the client field in request
            serializer.save()
        else:
            serializer.save()


class TechnicianViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Technician model
    """
    queryset = Technician.objects.all()
    serializer_class = TechnicianSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter technicians based on user role
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'CLIENT']:
            return Technician.objects.all()
        elif user.role == 'TECHNICIAN':
            # For now, return all technicians since we removed user relationship
            # In the future, you might want to add a different filtering mechanism
            return Technician.objects.all()
        else:
            return Technician.objects.none()
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Get all available technicians
        """
        available_technicians = self.get_queryset().filter(is_available=True)
        serializer = self.get_serializer(available_technicians, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def toggle_availability(self, request, pk=None):
        """
        Toggle technician availability status
        """
        technician = self.get_object()
        technician.is_available = not technician.is_available
        technician.save()
        serializer = self.get_serializer(technician)
        return Response(serializer.data)


class TeamGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TeamGroup model
    """
    queryset = TeamGroup.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TeamGroupListSerializer
        return TeamGroupSerializer
    
    def get_queryset(self):
        """
        Filter team groups based on user role
        """
        user = self.request.user
        
        if user.role in ['ADMIN', 'CLIENT']:
            return TeamGroup.objects.all()
        elif user.role == 'TECHNICIAN':
            # Technicians can see teams they belong to
            return TeamGroup.objects.filter(technicians__user=user)
        else:
            return TeamGroup.objects.none()
    
    @action(detail=True, methods=['post'])
    def add_technician(self, request, pk=None):
        """
        Add a technician to the team group
        """
        team_group = self.get_object()
        technician_id = request.data.get('technician_id')
        
        if not technician_id:
            return Response(
                {'error': 'technician_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            technician = Technician.objects.get(id=technician_id)
            team_group.technicians.add(technician)
            return Response({'message': 'Technician added to team successfully'})
        except Technician.DoesNotExist:
            return Response(
                {'error': 'Technician not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['delete'])
    def remove_technician(self, request, pk=None):
        """
        Remove a technician from the team group
        """
        team_group = self.get_object()
        technician_id = request.data.get('technician_id')
        
        if not technician_id:
            return Response(
                {'error': 'technician_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            technician = Technician.objects.get(id=technician_id)
            team_group.technicians.remove(technician)
            return Response({'message': 'Technician removed from team successfully'})
        except Technician.DoesNotExist:
            return Response(
                {'error': 'Technician not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token view that includes user role in response
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Try to get user by username first, then by email if that fails
            try:
                user = User.objects.get(username=request.data['username'])
            except User.DoesNotExist:
                # If username not found, try to find by email (for client login)
                try:
                    user = User.objects.get(email=request.data['username'])
                except User.DoesNotExist:
                    # If still not found, try to find client user
                    from .models import Client, Technician
                    try:
                        client = Client.objects.get(email=request.data['username'])
                        user = User.objects.get(username=f"client_{client.id}")
                    except (Client.DoesNotExist, User.DoesNotExist):
                        # Try to find technician user
                        try:
                            technician = Technician.objects.get(
                                Q(email=request.data['username']) | 
                                Q(identification_number=request.data['username'])
                            )
                            if technician.user:
                                user = technician.user
                            else:
                                return response  # Return response without user data
                        except (Technician.DoesNotExist, User.DoesNotExist):
                            return response  # Return response without user data
            
            response.data['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.get_full_name()
            }
        
        return response


class EquipmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Equipment model
    """
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter equipment based on user role
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return Equipment.objects.all()
        else:
            # For now, return all equipment for non-admin users
            # In the future, you might want to add different filtering logic
            return Equipment.objects.all()
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Get equipment filtered by type
        """
        equipment_type = request.query_params.get('type')
        if equipment_type:
            equipment = self.get_queryset().filter(equipment_type=equipment_type)
            serializer = self.get_serializer(equipment, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """
        Get equipment filtered by status
        """
        status = request.query_params.get('status')
        if status:
            equipment = self.get_queryset().filter(status=status)
            serializer = self.get_serializer(equipment, many=True)
            return Response(serializer.data)
        return Response([])


class ClientEquipmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ClientEquipment model
    """
    queryset = ClientEquipment.objects.all()
    serializer_class = ClientEquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter client equipment based on user role and permissions
        """
        user = self.request.user
        queryset = ClientEquipment.objects.select_related('client', 'equipment', 'site')
        
        # Filter by contract if contract_id is provided
        contract_id = self.request.query_params.get('contract_id')
        if contract_id:
            try:
                contract = Contract.objects.get(id=contract_id)
                # Get equipment IDs that are assigned to this contract
                equipment_ids = contract.equipment.values_list('id', flat=True)
                queryset = queryset.filter(id__in=equipment_ids)
            except Contract.DoesNotExist:
                return ClientEquipment.objects.none()
        
        if user.role == 'ADMIN':
            return queryset.all()
        elif user.role == 'CLIENT':
            # Extract client ID from username (format: client_<id>)
            if user.username.startswith('client_'):
                try:
                    client_id = int(user.username.replace('client_', ''))
                    return queryset.filter(client_id=client_id)
                except ValueError:
                    # If client_id can't be parsed, return empty queryset
                    return ClientEquipment.objects.none()
            # Fallback: try to filter by client__user if user relationship exists
            return queryset.filter(client__user=user)
        elif user.role == 'TECHNICIAN':
            # Technicians can see all client equipment (for maintenance purposes)
            return queryset.all()
        else:
            return ClientEquipment.objects.none()
    
    @action(detail=False, methods=['get'])
    def by_client(self, request):
        """
        Get client equipment filtered by client
        """
        client_id = request.query_params.get('client_id')
        if client_id:
            equipment = self.get_queryset().filter(client_id=client_id)
            serializer = self.get_serializer(equipment, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_equipment_type(self, request):
        """
        Get client equipment filtered by equipment type
        """
        equipment_id = request.query_params.get('equipment_id')
        if equipment_id:
            equipment = self.get_queryset().filter(equipment_id=equipment_id)
            serializer = self.get_serializer(equipment, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_site(self, request):
        """
        Get client equipment filtered by site
        """
        site_id = request.query_params.get('site_id')
        if site_id:
            equipment = self.get_queryset().filter(site_id=site_id)
            serializer = self.get_serializer(equipment, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get only active client equipment
        """
        equipment = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(equipment, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_warranty(self, request):
        """
        Get client equipment with warranties expiring soon (within 30 days)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_from_now = timezone.now().date() + timedelta(days=30)
        equipment = self.get_queryset().filter(
            is_active=True,
            warranty_expiry__lte=thirty_days_from_now,
            warranty_expiry__gte=timezone.now().date()
        )
        serializer = self.get_serializer(equipment, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """
        Create multiple client equipment instances from general equipment
        """
        print(f"Bulk create request data: {request.data}")
        
        equipment_data = request.data.get('equipment_data', [])
        client_id = request.data.get('client_id')
        site_id = request.data.get('site_id')
        
        print(f"Parsed data - equipment_data: {equipment_data}, client_id: {client_id}, site_id: {site_id}")
        
        if not equipment_data or not client_id:
            print("Missing required data")
            return Response(
                {'error': 'equipment_data and client_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            client = Client.objects.get(id=client_id)
            site = Site.objects.get(id=site_id) if site_id else None
            print(f"Found client: {client.name}, site: {site.title if site else 'None'}")
            
            created_equipment = []
            for i, eq_data in enumerate(equipment_data):
                print(f"Processing equipment {i+1}: {eq_data}")
                
                equipment_id = eq_data.get('equipment_id')
                serial_number = eq_data.get('serial_number')
                year_of_facturation = eq_data.get('year_of_facturation')
                warranty_expiry = eq_data.get('warranty_expiry')
                installation_date = eq_data.get('installation_date')
                notes = eq_data.get('notes', '')
                
                print(f"Equipment data - ID: {equipment_id}, SN: {serial_number}, Year: {year_of_facturation}, Warranty: {warranty_expiry}")
                
                if not all([equipment_id, serial_number, year_of_facturation, warranty_expiry]):
                    print(f"Missing required fields for equipment {i+1}")
                    return Response(
                        {'error': 'equipment_id, serial_number, year_of_facturation, and warranty_expiry are required for each equipment'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if serial number already exists
                if ClientEquipment.objects.filter(serial_number=serial_number).exists():
                    print(f"Serial number {serial_number} already exists")
                    return Response(
                        {'error': f'Serial number {serial_number} already exists'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                equipment = Equipment.objects.get(id=equipment_id)
                print(f"Found equipment: {equipment.full_name}")
                
                client_equipment = ClientEquipment.objects.create(
                    client=client,
                    equipment=equipment,
                    serial_number=serial_number,
                    year_of_facturation=year_of_facturation,
                    warranty_expiry=warranty_expiry,
                    site=site,
                    installation_date=installation_date,
                    notes=notes,
                    is_active=True
                )
                
                print(f"Created client equipment: {client_equipment.id}")
                created_equipment.append(client_equipment)
            
            serializer = self.get_serializer(created_equipment, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Client.DoesNotExist:
            return Response(
                {'error': 'Client not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Site.DoesNotExist:
            return Response(
                {'error': 'Site not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Equipment.DoesNotExist:
            return Response(
                {'error': 'Equipment not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class TechnicianGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TechnicianGroup model
    """
    queryset = TechnicianGroup.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TechnicianGroupListSerializer
        return TechnicianGroupSerializer
    
    def get_queryset(self):
        """
        Filter groups based on user role
        """
        user = self.request.user
        
        if user.role == 'ADMIN':
            return TechnicianGroup.objects.all()
        elif user.role == 'TECHNICIAN':
            # Technicians can view groups they belong to
            return TechnicianGroup.objects.filter(technicians__user=user)
        else:
            return TechnicianGroup.objects.none()
    
    @action(detail=True, methods=['post'])
    def add_technician(self, request, pk=None):
        """
        Add a technician to this group
        """
        group = self.get_object()
        technician_id = request.data.get('technician_id')
        
        if not technician_id:
            return Response({'error': 'technician_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            technician = Technician.objects.get(id=technician_id)
            
            if group.is_at_capacity():
                return Response({'error': 'Group is at maximum capacity'}, status=status.HTTP_400_BAD_REQUEST)
            
            if technician in group.technicians.all():
                return Response({'error': 'Technician is already in this group'}, status=status.HTTP_400_BAD_REQUEST)
            
            group.technicians.add(technician)
            return Response({'message': 'Technician added to group successfully'})
            
        except Technician.DoesNotExist:
            return Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['delete'])
    def remove_technician(self, request, pk=None):
        """
        Remove a technician from this group
        """
        group = self.get_object()
        technician_id = request.data.get('technician_id')
        
        if not technician_id:
            return Response({'error': 'technician_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            technician = Technician.objects.get(id=technician_id)
            
            if technician not in group.technicians.all():
                return Response({'error': 'Technician is not in this group'}, status=status.HTTP_400_BAD_REQUEST)
            
            group.technicians.remove(technician)
            return Response({'message': 'Technician removed from group successfully'})
            
        except Technician.DoesNotExist:
            return Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def available_technicians(self, request):
        """
        Get list of technicians not assigned to any group
        """
        technicians = Technician.objects.filter(technician_groups__isnull=True)
        serializer = TechnicianSerializer(technicians, many=True)
        return Response(serializer.data)


class ContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Contract model
    """
    queryset = Contract.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContractListSerializer
        return ContractSerializer
    
    def get_queryset(self):
        """
        Filter contracts based on user role and permissions
        """
        user = self.request.user
        queryset = Contract.objects.select_related('client').prefetch_related('sites', 'equipment')
        
        # Filter by contract type if specified
        contract_type = self.request.query_params.get('contract_type')
        if contract_type:
            queryset = queryset.filter(contract_type=contract_type)
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'CLIENT':
            # Clients can only see their own contracts
            # Primary: use explicit relation between Client and User
            try:
                client = Client.objects.get(user=user)
                return queryset.filter(client=client)
            except Client.DoesNotExist:
                # Fallback: extract client ID from username (format: client_<id>)
                username = getattr(user, "username", "") or ""
                if username.startswith("client_"):
                    try:
                        client_id = int(username.replace("client_", ""))
                        return queryset.filter(client_id=client_id)
                    except ValueError:
                        return Contract.objects.none()
                return Contract.objects.none()
        elif user.role == 'TECHNICIAN':
            # Technicians can see all contracts (for service purposes)
            return queryset
        else:
            return Contract.objects.none()
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single contract with full details
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        print(f"Contract {instance.id} equipment IDs: {[eq.id for eq in instance.equipment.all()]}")
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        Handle contract creation with file upload support
        """
        try:
            # Handle equipment data from form data
            equipment_ids = []
            # Handle equipment as JSON string
            if 'equipment' in request.data:
                equipment_data = request.data['equipment']
                try:
                    # Try to parse as JSON first
                    if isinstance(equipment_data, str):
                        equipment_ids = json.loads(equipment_data)
                    else:
                        # Fallback to single value
                        equipment_ids = [int(equipment_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    # Fallback to empty list if parsing fails
                    print(f"DEBUG: Error parsing equipment data: {e}")
                    equipment_ids = []
            
            # Also handle old format for backward compatibility
            for key, value in request.data.items():
                if key.startswith('equipment[') and key.endswith(']'):
                    equipment_ids.append(int(value))
            
            # Handle sites data from form data
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    # Try to parse as JSON first
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    else:
                        # Fallback to single value
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError):
                    # Fallback to old format
                    sites_ids = [int(sites_data)]
            
            # Also handle old format for backward compatibility
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))
            
            # Create a mutable copy of the data (without equipment and sites)
            data = request.data.copy()
            # Remove equipment and sites from data since we'll handle them separately
            if 'equipment' in data:
                del data['equipment']
            if 'sites' in data:
                del data['sites']
            
            serializer = self.get_serializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            contract = serializer.save()
            
            # Handle sites assignment after contract creation
            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                contract.sites.set(sites_objects)
            
            # Handle equipment assignment after contract creation
            if equipment_ids:
                equipment_objects = ClientEquipment.objects.filter(id__in=equipment_ids if isinstance(equipment_ids, list) else [equipment_ids])
                contract.equipment.set(equipment_objects)
            
            if not contract.code:
                import uuid
                contract.code = f"CONT_{str(uuid.uuid4())[:8].upper()}"
                contract.save()
            
            # Automatically create maintenance projects if requested
            if contract.create_project_maintenance_automatically:
                try:
                    created_projects = create_maintenance_projects_automatically(contract)
                    print(f"Created {len(created_projects)} maintenance projects for contract {contract.code}")
                except Exception as e:
                    print(f"Error creating automatic maintenance projects: {str(e)}")
                    # Don't fail the contract creation if project creation fails
                    # The contract is already created successfully
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print(f"Error creating contract: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """
        Handle contract update with file upload support
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            # Handle equipment data from form data
            equipment_ids = []
            # Handle equipment as JSON string
            if 'equipment' in request.data:
                equipment_data = request.data['equipment']
                try:
                    # Try to parse as JSON first
                    if isinstance(equipment_data, str):
                        equipment_ids = json.loads(equipment_data)
                    else:
                        # Fallback to single value
                        equipment_ids = [int(equipment_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    # Fallback to empty list if parsing fails
                    print(f"DEBUG: Error parsing equipment data: {e}")
                    equipment_ids = []
            
            # Also handle old format for backward compatibility
            for key, value in request.data.items():
                if key.startswith('equipment[') and key.endswith(']'):
                    equipment_ids.append(int(value))
            
            # Handle sites data from form data
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    # Try to parse as JSON first
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    else:
                        # Fallback to single value
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError):
                    # Fallback to old format
                    sites_ids = [int(sites_data)]
            
            # Also handle old format for backward compatibility
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))
            
            # Create a mutable copy of the data (without equipment and sites)
            data = request.data.copy()
            # Remove equipment and sites from data since we'll handle them separately
            if 'equipment' in data:
                del data['equipment']
            if 'sites' in data:
                del data['sites']
            
            serializer = self.get_serializer(instance, data=data, partial=partial, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Handle sites assignment after contract update
            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                instance.sites.set(sites_objects)
            else:
                instance.sites.clear()
            
            # Handle equipment assignment after contract update
            if equipment_ids:
                equipment_objects = ClientEquipment.objects.filter(id__in=equipment_ids if isinstance(equipment_ids, list) else [equipment_ids])
                instance.equipment.set(equipment_objects)
            else:
                instance.equipment.clear()
            return Response(serializer.data)
        except Exception as e:
            print(f"Error updating contract: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Handle partial contract updates (PATCH requests)
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Dedicated endpoint for updating contract status only
        """
        try:
            contract = self.get_object()
            new_status = request.data.get('status')
            
            if not new_status:
                return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate status choice
            valid_statuses = [choice[0] for choice in Contract.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the status
            contract.status = new_status
            contract.save()
            
            # Return updated contract data
            serializer = self.get_serializer(contract)
            return Response({
                'message': f'Status updated to {new_status}',
                'contract': serializer.data
            })
            
        except Contract.DoesNotExist:
            return Response({'error': 'Contract not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error updating contract status: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        """
        Set the contract code if not provided
        """
        contract = serializer.save()
        if not contract.code:
            import uuid
            contract.code = f"CONT_{str(uuid.uuid4())[:8].upper()}"
            contract.save()
    
    @action(detail=True, methods=['post'])
    def add_equipment(self, request, pk=None):
        """
        Add equipment to this contract
        """
        contract = self.get_object()
        equipment_ids = request.data.get('equipment_ids', [])
        
        if not equipment_ids:
            return Response({'error': 'equipment_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify all equipment belongs to the same client
            equipment = ClientEquipment.objects.filter(id__in=equipment_ids)
            if not equipment.exists():
                return Response({'error': 'No valid equipment found'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if all equipment belongs to the contract's client
            for eq in equipment:
                if eq.client != contract.client:
                    return Response({'error': f'Equipment {eq.serial_number} does not belong to contract client'}, status=status.HTTP_400_BAD_REQUEST)
            
            contract.equipment.add(*equipment)
            return Response({'message': 'Equipment added to contract successfully'})
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'])
    def remove_equipment(self, request, pk=None):
        """
        Remove equipment from this contract
        """
        contract = self.get_object()
        equipment_id = request.data.get('equipment_id')
        
        if not equipment_id:
            return Response({'error': 'equipment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            equipment = ClientEquipment.objects.get(id=equipment_id)
            contract.equipment.remove(equipment)
            return Response({'message': 'Equipment removed from contract successfully'})
            
        except ClientEquipment.DoesNotExist:
            return Response({'error': 'Equipment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get list of expired contracts
        """
        from django.utils import timezone
        expired_contracts = self.get_queryset().filter(ending_date__lt=timezone.now().date())
        serializer = self.get_serializer(expired_contracts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Get list of contracts expiring within 30 days
        """
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_from_now = timezone.now().date() + timedelta(days=30)
        expiring_contracts = self.get_queryset().filter(
            ending_date__lte=thirty_days_from_now,
            ending_date__gte=timezone.now().date(),
            is_active=True
        )
        serializer = self.get_serializer(expiring_contracts, many=True)
        return Response(serializer.data)


class ProjectInstallationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProjectInstallation model
    """
    queryset = ProjectInstallation.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectInstallationListSerializer
        return ProjectInstallationSerializer

    def get_queryset(self):
        """
        Filter projects based on user role and permissions
        """
        user = self.request.user
        queryset = ProjectInstallation.objects.select_related('client', 'contract', 'technician_group').prefetch_related('equipment', 'pdf_documents', 'facture_pdfs', 'pv_pdfs', 'quote_pdfs')
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'CLIENT':
            # Extract client ID from username (format: client_<id>)
            if user.username.startswith('client_'):
                try:
                    client_id = int(user.username.replace('client_', ''))
                    return queryset.filter(client_id=client_id)
                except ValueError:
                    return ProjectInstallation.objects.none()
            # Fallback: return no projects if client ID can't be determined
            return ProjectInstallation.objects.none()
        elif user.role == 'TECHNICIAN':
            # Filter projects assigned to technician's technician groups
            try:
                technician = user.technician_profile
                if not technician:
                    return ProjectInstallation.objects.none()
                
                # Get all technician groups this technician belongs to
                technician_groups = technician.technician_groups.filter(status='ACTIVE')
                
                if technician_groups.exists():
                    technician_group_ids = list(technician_groups.values_list('id', flat=True))
                    return queryset.filter(
                        technician_group__in=technician_group_ids,
                        is_active=True
                    )
                else:
                    return ProjectInstallation.objects.none()
            except (Technician.DoesNotExist, AttributeError):
                return ProjectInstallation.objects.none()
        else:
            return ProjectInstallation.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Handle project creation with file upload support
        """
        import json
        try:
            # Handle equipment data from form data - use getlist as primary method
            equipment_ids = []
            if hasattr(request.data, 'getlist'):
                equipment_list = request.data.getlist('equipment')
                if equipment_list:
                    # Check if the first item is a JSON string (e.g., '[25,26]')
                    if len(equipment_list) == 1 and isinstance(equipment_list[0], str) and equipment_list[0].startswith('['):
                        try:
                            equipment_ids = json.loads(equipment_list[0])
                            print(f"DEBUG CREATE: Equipment from getlist (parsed JSON): {equipment_ids}")
                        except json.JSONDecodeError:
                            equipment_ids = [int(item) for item in equipment_list]
                            print(f"DEBUG CREATE: Equipment from getlist (direct): {equipment_ids}")
                    else:
                        equipment_ids = [int(item) for item in equipment_list]
                        print(f"DEBUG CREATE: Equipment from getlist: {equipment_ids}")
            
            # Fallback: Handle equipment data from form data
            if not equipment_ids and 'equipment' in request.data:
                equipment_data = request.data['equipment']
                try:
                    if isinstance(equipment_data, str):
                        equipment_ids = json.loads(equipment_data)
                    elif isinstance(equipment_data, list):
                        equipment_ids = [int(item) for item in equipment_data]
                    else:
                        equipment_ids = [int(equipment_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing equipment data: {e}")
                    print(f"DEBUG CREATE: equipment_data value: {equipment_data}")
                    equipment_ids = []
                print(f"DEBUG CREATE: Equipment from fallback: {equipment_ids}")

            # Handle additional equipment from form fields
            for key, value in request.data.items():
                if key.startswith('equipment[') and key.endswith(']'):
                    equipment_ids.append(int(value))

            data = request.data.copy()
            if 'equipment' in data:
                del data['equipment']
            if 'sites' in data:
                del data['sites']

            serializer = self.get_serializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            project = serializer.save()

            # Handle sites assignment after project creation - use getlist as primary method
            sites_ids = []
            if hasattr(request.data, 'getlist'):
                sites_list = request.data.getlist('sites')
                if sites_list:
                    # Check if the first item is a JSON string (e.g., '21]')
                    if len(sites_list) == 1 and isinstance(sites_list[0], str) and sites_list[0].startswith('['):
                        try:
                            sites_ids = json.loads(sites_list[0])
                            print(f"DEBUG CREATE: Sites from getlist (parsed JSON): {sites_ids}")
                        except json.JSONDecodeError:
                            sites_ids = [int(item) for item in sites_list]
                            print(f"DEBUG CREATE: Sites from getlist (direct): {sites_ids}")
                    else:
                        sites_ids = [int(item) for item in sites_list]
                        print(f"DEBUG CREATE: Sites from getlist: {sites_ids}")
            
            # Fallback: Handle sites data from form data
            if not sites_ids and 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        sites_ids = [int(item) for item in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []
                print(f"DEBUG CREATE: Sites from fallback: {sites_ids}")

            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))

            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                project.sites.set(sites_objects)

            # Handle equipment assignment after project creation
            print(f"DEBUG CREATE: Final equipment_ids: {equipment_ids}")
            if equipment_ids:
                equipment_objects = ClientEquipment.objects.filter(id__in=equipment_ids if isinstance(equipment_ids, list) else [equipment_ids])
                print(f"DEBUG CREATE: Found equipment objects: {[eq.id for eq in equipment_objects]}")
                project.equipment.set(equipment_objects)
                print(f"DEBUG CREATE: Project equipment count after set: {project.equipment.count()}")

            # Handle PDF uploads - extract and process files immediately
            pdf_files = request.FILES.getlist('pdf_files')
            pdf_titles = request.data.getlist('pdf_titles')
            
            # Handle different formats of pdf_titles
            if isinstance(pdf_titles, str):
                try:
                    pdf_titles = json.loads(pdf_titles)
                except (json.JSONDecodeError, ValueError):
                    pdf_titles = [pdf_titles]
            elif not isinstance(pdf_titles, list):
                pdf_titles = [str(pdf_titles)]
            
            # Ensure we have enough titles for all files
            while len(pdf_titles) < len(pdf_files):
                pdf_titles.append(f"PDF {len(pdf_titles) + 1}")
            
            print(f"DEBUG: Final PDF files count: {len(pdf_files)}")
            print(f"DEBUG: Final PDF titles: {pdf_titles}")
            print(f"DEBUG: Project ID: {project.id}")
            print(f"DEBUG: Project name: {project.project_name}")
            
            # CRITICAL: Remove PDF file references from request data to prevent serialization
            # This prevents Django from trying to serialize the file objects later
            if 'pdf_files' in request.FILES:
                # Clear the FILES dictionary to remove file object references
                request.FILES.clear()
                print("DEBUG: Cleared request.FILES to remove file object references")
            
            # Also remove from request.data if present
            if hasattr(request, 'data') and 'pdf_files' in request.data:
                del request.data['pdf_files']
                print("DEBUG: Removed pdf_files from request.data")
            
            # Force garbage collection to clean up any remaining file objects
            import gc
            gc.collect()
            print("DEBUG: Forced garbage collection to clean up file objects")
            
            # Create PDF documents after project creation to avoid serialization issues
            try:
                print(f"DEBUG: Starting PDF creation loop for {len(pdf_files)} files")
                for i, pdf_file in enumerate(pdf_files):
                    title = pdf_titles[i] if i < len(pdf_titles) else f"PDF {i+1}"
                    print(f"DEBUG: Creating PDF {i+1}: {title}")
                    print(f"DEBUG: PDF file name: {pdf_file.name}")
                    print(f"DEBUG: PDF file size: {pdf_file.size if hasattr(pdf_file, 'size') else 'Unknown'}")
                    print(f"DEBUG: PDF file type: {type(pdf_file)}")
                    
                    # Create PDF document with proper file handling
                    pdf_doc = ProjectInstallationPDF(
                        project=project,
                        title=title
                    )
                    
                    # Save the file using raw binary data to avoid serialization issues
                    try:
                        print(f"DEBUG: Attempting to save PDF file...")
                        
                        # Read the file content immediately and create a new file object
                        pdf_file.seek(0)
                        file_content = pdf_file.read()
                        original_filename = pdf_file.name
                        print(f"DEBUG: File content size: {len(file_content)} bytes")
                        print(f"DEBUG: Original filename: {original_filename}")
                        
                        # Create a new ContentFile from the raw binary data
                        from django.core.files.base import ContentFile
                        content_file = ContentFile(file_content, name=original_filename)
                        
                        # Save using the content file (no file handles involved)
                        pdf_doc.pdf_file.save(original_filename, content_file, save=True)
                        print(f"DEBUG: Successfully created PDF: {pdf_doc.id}")
                        
                        # Verify the PDF was created and saved
                        print(f"DEBUG: PDF document created with ID: {pdf_doc.id}, Title: {pdf_doc.title}")
                        print(f"DEBUG: PDF file exists: {pdf_doc.pdf_file.name if pdf_doc.pdf_file else 'No file'}")
                        print(f"DEBUG: PDF file URL: {pdf_doc.pdf_file.url if pdf_doc.pdf_file else 'No URL'}")
                        
                    except Exception as file_error:
                        print(f"DEBUG: Error saving PDF file: {file_error}")
                        import traceback
                        traceback.print_exc()
                        # If all else fails, create the PDF document without the file
                        pdf_doc.save()
                        print(f"DEBUG: Created PDF document without file: {pdf_doc.id}")
                    
                # CRITICAL: Clear the pdf_files list to remove all file object references
                pdf_files.clear()
                print("DEBUG: Cleared pdf_files list to remove all file object references")
                    
            except Exception as pdf_error:
                print(f"Error creating PDF documents: {pdf_error}")
                import traceback
                traceback.print_exc()
                # Continue without failing the entire project creation

            # Refresh the project instance to get the PDF documents
            project.refresh_from_db()
            
            # Debug: Check if PDF documents exist
            pdf_docs = project.pdf_documents.all()
            print(f"Project {project.id} has {pdf_docs.count()} PDF documents")
            for pdf_doc in pdf_docs:
                print(f"  - PDF: {pdf_doc.title} (ID: {pdf_doc.id})")
            
            # Send notification if technician group is assigned
            if project.technician_group:
                from .notifications import notify_technicians_new_project
                try:
                    notify_technicians_new_project(project, project.technician_group)
                except Exception as e:
                    logger.error(f"Error sending notification for new project: {str(e)}")
            
            # Create a new serializer instance with the updated project
            response_serializer = self.get_serializer(project)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error creating project: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Handle project update with file upload support
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()

            # Handle equipment data from form data - use getlist as primary method
            equipment_ids = []
            if hasattr(request.data, 'getlist'):
                equipment_list = request.data.getlist('equipment')
                if equipment_list:
                    # Check if the first item is a JSON string (e.g., '[25,26]')
                    if len(equipment_list) == 1 and isinstance(equipment_list[0], str) and equipment_list[0].startswith('['):
                        try:
                            equipment_ids = json.loads(equipment_list[0])
                            print(f"DEBUG CREATE: Equipment from getlist (parsed JSON): {equipment_ids}")
                        except json.JSONDecodeError:
                            equipment_ids = [int(item) for item in equipment_list]
                            print(f"DEBUG CREATE: Equipment from getlist (direct): {equipment_ids}")
                    else:
                        equipment_ids = [int(item) for item in equipment_list]
                        print(f"DEBUG CREATE: Equipment from getlist: {equipment_ids}")
            
            # Fallback: Handle equipment data from form data
            if not equipment_ids and 'equipment' in request.data:
                equipment_data = request.data['equipment']
                try:
                    if isinstance(equipment_data, str):
                        equipment_ids = json.loads(equipment_data)
                    elif isinstance(equipment_data, list):
                        equipment_ids = [int(item) for item in equipment_data]
                    else:
                        equipment_ids = [int(equipment_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing equipment data: {e}")
                    print(f"DEBUG CREATE: equipment_data value: {equipment_data}")
                    equipment_ids = []
                print(f"DEBUG CREATE: Equipment from fallback: {equipment_ids}")

            # Handle additional equipment from form fields
            for key, value in request.data.items():
                if key.startswith('equipment[') and key.endswith(']'):
                    equipment_ids.append(int(value))

            # Handle sites data from form data
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        # Handle multiple sites sent as a list
                        sites_ids = [int(item) for item in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []

            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))

            data = request.data.copy()
            if 'equipment' in data:
                del data['equipment']
            if 'sites' in data:
                del data['sites']

            serializer = self.get_serializer(instance, data=data, partial=partial, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            # Handle sites assignment after project update
            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                instance.sites.set(sites_objects)
            else:
                instance.sites.clear()

            # Handle equipment assignment after project update
            if equipment_ids:
                equipment_objects = ClientEquipment.objects.filter(id__in=equipment_ids if isinstance(equipment_ids, list) else [equipment_ids])
                instance.equipment.set(equipment_objects)
            else:
                instance.equipment.clear()

            # Handle PDF uploads - extract and process files immediately
            pdf_files = request.FILES.getlist('pdf_files')
            pdf_titles = request.data.getlist('pdf_titles')
            
            # Handle different formats of pdf_titles
            if isinstance(pdf_titles, str):
                try:
                    pdf_titles = json.loads(pdf_titles)
                except (json.JSONDecodeError, ValueError):
                    pdf_titles = [pdf_titles]
            elif not isinstance(pdf_titles, list):
                pdf_titles = [str(pdf_titles)]
            
            # Ensure we have enough titles for all files
            while len(pdf_titles) < len(pdf_files):
                pdf_titles.append(f"PDF {len(pdf_titles) + 1}")
            
            # CRITICAL: Remove PDF file references from request data to prevent serialization
            # This prevents Django from trying to serialize the file objects later
            if 'pdf_files' in request.FILES:
                # Clear the FILES dictionary to remove file object references
                request.FILES.clear()
                print("DEBUG: Cleared request.FILES to remove file object references")
            
            # Also remove from request.data if present
            if hasattr(request, 'data') and 'pdf_files' in request.data:
                del request.data['pdf_files']
                print("DEBUG: Removed pdf_files from request.data")
            
            # Force garbage collection to clean up any remaining file objects
            import gc
            gc.collect()
            print("DEBUG: Forced garbage collection to clean up file objects")
            
            # Handle PDF removal first
            try:
                pdfs_to_remove = []
                if 'pdfs_to_remove' in request.data:
                    pdfs_to_remove_data = request.data['pdfs_to_remove']
                    try:
                        if isinstance(pdfs_to_remove_data, str):
                            pdfs_to_remove = json.loads(pdfs_to_remove_data)
                        else:
                            pdfs_to_remove = [int(pdfs_to_remove_data)]
                    except (json.JSONDecodeError, ValueError):
                        pdfs_to_remove = [int(pdfs_to_remove_data)]
                
                # Remove PDF documents
                if pdfs_to_remove:
                    print(f"DEBUG: Removing PDF documents: {pdfs_to_remove}")
                    from core.models import ProjectInstallationPDF
                    ProjectInstallationPDF.objects.filter(
                        id__in=pdfs_to_remove,
                        project=instance
                    ).delete()
                    print(f"DEBUG: Successfully removed {len(pdfs_to_remove)} PDF documents")
                    
            except Exception as remove_error:
                print(f"Error removing PDF documents: {remove_error}")
                import traceback
                traceback.print_exc()
                # Continue without failing the entire project update

            # Create PDF documents after project update to avoid serialization issues
            try:
                for i, pdf_file in enumerate(pdf_files):
                    title = pdf_titles[i] if i < len(pdf_titles) else f"PDF {i+1}"
                    print(f"Creating PDF {i+1}: {title}")  # Debug log
                    
                    # Create PDF document with proper file handling
                    pdf_doc = ProjectInstallationPDF(
                        project=instance,
                        title=title
                    )
                    
                    # Save the file using raw binary data to avoid serialization issues
                    try:
                        print(f"DEBUG: Attempting to save PDF file in update...")
                        
                        # Read the file content immediately and create a new file object
                        pdf_file.seek(0)
                        file_content = pdf_file.read()
                        original_filename = pdf_file.name
                        print(f"DEBUG: File content size: {len(file_content)} bytes")
                        print(f"DEBUG: Original filename: {original_filename}")
                        
                        # Create a new ContentFile from the raw binary data
                        from django.core.files.base import ContentFile
                        content_file = ContentFile(file_content, name=original_filename)
                        
                        # Save using the content file (no file handles involved)
                        pdf_doc.pdf_file.save(original_filename, content_file, save=True)
                        print(f"DEBUG: Successfully created PDF: {pdf_doc.id}")
                        
                    except Exception as file_error:
                        print(f"DEBUG: Error saving PDF file in update: {file_error}")
                        import traceback
                        traceback.print_exc()
                        # If all else fails, create the PDF document without the file
                        pdf_doc.save()
                        print(f"DEBUG: Created PDF document without file: {pdf_doc.id}")
                
                # CRITICAL: Clear the pdf_files list to remove all file object references
                pdf_files.clear()
                print("DEBUG: Cleared pdf_files list to remove all file object references")
                    
            except Exception as pdf_error:
                print(f"Error creating PDF documents: {pdf_error}")
                import traceback
                traceback.print_exc()
                # Continue without failing the entire project update

            # Refresh the instance to get the PDF documents
            instance.refresh_from_db()
            
            # Create a new serializer instance with the updated project
            response_serializer = self.get_serializer(instance)
            return Response(response_serializer.data)

        except Exception as e:
            print(f"Error updating project: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def installation_contracts(self, request):
        """
        Get contracts with type 'INSTALLATION' for project creation
        """
        contracts = Contract.objects.filter(
            contract_type='INSTALLATION',
            is_active=True
        ).order_by('-created_at')
        
        serializer = ContractListSerializer(contracts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def client_equipment(self, request):
        """
        Get equipment for a specific client (when no contract is selected)
        """
        client_id = request.query_params.get('client_id')
        if client_id:
            equipment = ClientEquipment.objects.filter(
                client_id=client_id,
                is_active=True
            ).select_related('equipment', 'site')
            serializer = ClientEquipmentSerializer(equipment, many=True, context={'request': request})
            return Response(serializer.data)
        return Response([])

    @action(detail=False, methods=['get'])
    def contract_equipment(self, request):
        """
        Get equipment for a specific contract
        """
        contract_id = request.query_params.get('contract_id')
        if contract_id:
            try:
                contract = Contract.objects.get(id=contract_id)
                equipment = contract.equipment.filter(is_active=True)
                serializer = ClientEquipmentSerializer(equipment, many=True, context={'request': request})
                return Response(serializer.data)
            except Contract.DoesNotExist:
                return Response({'error': 'Contract not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response([])

    @action(detail=True, methods=['post'])
    def add_facture_pdf(self, request, pk=None):
        """
        Add a facture PDF to this project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', 'Facture PDF')
        
        if not pdf_file:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            facture_pdf = ProjectInstallationFacture.objects.create(
                project=project,
                pdf_file=pdf_file,
                title=title
            )
            serializer = ProjectInstallationFactureSerializer(facture_pdf, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_pv_pdf(self, request, pk=None):
        """
        Add a PV PDF to this project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', 'PV PDF')
        
        if not pdf_file:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            pv_pdf = ProjectInstallationPV.objects.create(
                project=project,
                pdf_file=pdf_file,
                title=title
            )
            serializer = ProjectInstallationPVSerializer(pv_pdf, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_quote_pdf(self, request, pk=None):
        """
        Add a quote PDF to this project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', 'Quote PDF')
        
        if not pdf_file:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quote_pdf = ProjectInstallationQuote.objects.create(
                project=project,
                pdf_file=pdf_file,
                title=title
            )
            serializer = ProjectInstallationQuoteSerializer(quote_pdf, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_facture_pdf(self, request, pk=None):
        """
        Remove a facture PDF from this project
        """
        project = self.get_object()
        pdf_id = request.data.get('pdf_id')
        
        if not pdf_id:
            return Response({'error': 'pdf_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            facture_pdf = ProjectInstallationFacture.objects.get(id=pdf_id, project=project)
            facture_pdf.delete()
            return Response({'message': 'Facture PDF removed successfully'})
        except ProjectInstallationFacture.DoesNotExist:
            return Response({'error': 'Facture PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def remove_pv_pdf(self, request, pk=None):
        """
        Remove a PV PDF from this project
        """
        project = self.get_object()
        pdf_id = request.data.get('pdf_id')
        
        if not pdf_id:
            return Response({'error': 'pdf_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            pv_pdf = ProjectInstallationPV.objects.get(id=pdf_id, project=project)
            pv_pdf.delete()
            return Response({'message': 'PV PDF removed successfully'})
        except ProjectInstallationPV.DoesNotExist:
            return Response({'error': 'PV PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def remove_quote_pdf(self, request, pk=None):
        """
        Remove a quote PDF from this project
        """
        project = self.get_object()
        pdf_id = request.data.get('pdf_id')
        
        if not pdf_id:
            return Response({'error': 'pdf_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quote_pdf = ProjectInstallationQuote.objects.get(id=pdf_id, project=project)
            quote_pdf.delete()
            return Response({'message': 'Quote PDF removed successfully'})
        except ProjectInstallationQuote.DoesNotExist:
            return Response({'error': 'Quote PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def get_facture_pdfs(self, request, pk=None):
        """
        Get all facture PDFs for this project
        """
        project = self.get_object()
        facture_pdfs = project.facture_pdfs.all()
        serializer = ProjectInstallationFactureSerializer(facture_pdfs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_pv_pdfs(self, request, pk=None):
        """
        Get all PV PDFs for this project
        """
        project = self.get_object()
        pv_pdfs = project.pv_pdfs.all()
        serializer = ProjectInstallationPVSerializer(pv_pdfs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_quote_pdfs(self, request, pk=None):
        """
        Get all quote PDFs for this project
        """
        project = self.get_object()
        quote_pdfs = project.quote_pdfs.all()
        serializer = ProjectInstallationQuoteSerializer(quote_pdfs, many=True, context={'request': request})
        return Response(serializer.data)


class TraveauxViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Traveaux model
    """
    queryset = Traveaux.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TraveauxListSerializer
        return TraveauxSerializer
    
    def get_queryset(self):
        """
        Filter traveaux based on user role and project
        """
        user = self.request.user
        queryset = Traveaux.objects.select_related('project').prefetch_related('sites', 'reports')
        
        # Filter by project if project_id is provided
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'CLIENT':
            # Clients can see traveaux for their projects
            return queryset.filter(project__client__user=user)
        elif user.role == 'TECHNICIAN':
            # Technicians can see all traveaux (for service purposes)
            return queryset
        else:
            return Traveaux.objects.none()
    
    def create(self, request, *args, **kwargs):
        """
        Handle traveaux creation with sites assignment
        """
        try:
            # Handle sites data from form data
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        sites_ids = [int(site_id) for site_id in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []
            
            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))
            
            # Handle scheduled dates
            scheduled_dates = request.data.get('scheduled_dates')
            if scheduled_dates:
                try:
                    if isinstance(scheduled_dates, str):
                        scheduled_dates = json.loads(scheduled_dates)
                except (json.JSONDecodeError, ValueError):
                    scheduled_dates = [scheduled_dates]
            
            data = request.data.copy()
            if 'sites' in data:
                del data['sites']
            if 'scheduled_dates' in data:
                del data['scheduled_dates']
            
            serializer = self.get_serializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            traveaux = serializer.save()
            
            # Handle sites assignment after traveaux creation
            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                traveaux.sites.set(sites_objects)
            
            # Handle scheduled dates assignment
            if scheduled_dates:
                traveaux.scheduled_dates = scheduled_dates
                traveaux.save()
            
            # Send notification for new task
            if traveaux.project and traveaux.project.technician_group:
                from .notifications import notify_technicians_new_task
                try:
                    notify_technicians_new_task(traveaux, traveaux.project)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending notification for new task: {str(e)}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """
        Handle traveaux update with sites assignment
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            # Handle sites data from form data
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        # Handle multiple sites sent as a list
                        sites_ids = [int(item) for item in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []
            
            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))
            
            # Handle scheduled dates
            scheduled_dates = request.data.get('scheduled_dates')
            if scheduled_dates:
                try:
                    if isinstance(scheduled_dates, str):
                        scheduled_dates = json.loads(scheduled_dates)
                except (json.JSONDecodeError, ValueError):
                    scheduled_dates = [scheduled_dates]
            
            data = request.data.copy()
            if 'sites' in data:
                del data['sites']
            if 'scheduled_dates' in data:
                del data['scheduled_dates']
            
            serializer = self.get_serializer(instance, data=data, partial=partial, context={'request': request})
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Handle sites assignment after traveaux update
            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                instance.sites.set(sites_objects)
            else:
                instance.sites.clear()
            
            # Handle scheduled dates assignment
            if scheduled_dates:
                instance.scheduled_dates = scheduled_dates
                instance.save()
            
            return Response(serializer.data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(
        detail=True,
        methods=['get', 'post'],
        url_path='reports',
        parser_classes=[MultiPartParser, FormParser]
    )
    def manage_reports(self, request, pk=None):
        """
        List or upload PDF reports for a specific traveaux
        """
        traveaux = self.get_object()
        
        if request.method.lower() == 'get':
            serializer = TraveauxReportSerializer(
                traveaux.reports.all(),
                many=True,
                context={'request': request}
            )
            return Response(serializer.data)
        
        files = request.FILES.getlist('reports') or request.FILES.getlist('report_files')
        if not files:
            return Response({'error': 'Please provide at least one PDF report'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_reports = []
        for upload in files:
            if upload.content_type not in ('application/pdf', 'application/x-pdf'):
                return Response({'error': f'{upload.name} is not a PDF file'}, status=status.HTTP_400_BAD_REQUEST)
            report = TraveauxReport.objects.create(
                traveaux=traveaux,
                report_file=upload,
                title=request.data.get('title', '').strip()
            )
            created_reports.append(report)
        
        serializer = TraveauxReportSerializer(created_reports, many=True, context={'request': request})
        return Response(
            {'message': 'Reports uploaded successfully', 'reports': serializer.data},
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['delete'], url_path='reports/(?P<report_id>[^/.]+)')
    def delete_report(self, request, pk=None, report_id=None):
        """
        Delete a specific report attached to a traveaux
        """
        traveaux = self.get_object()
        try:
            report = traveaux.reports.get(pk=report_id)
            # Remove file from storage
            if report.report_file:
                report.report_file.delete(save=False)
            report.delete()
            return Response({'message': 'Report deleted successfully'})
        except TraveauxReport.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='generate-intervention-report')
    def generate_intervention_report(self, request, pk=None):
        """
        Generate intervention report PDF from form data
        """
        traveaux = self.get_object()
        
        try:
            # Get form data
            form_data = request.data
            
            # Create PDF buffer
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # Colors
            red_color = colors.HexColor('#FF0000')
            black_color = colors.HexColor('#000000')
            
            # Header with logo (simplified - you can add actual logo image)
            p.setFillColor(red_color)
            p.setFont("Helvetica-Bold", 20)
            p.drawString(50, height - 50, "FCA")
            p.setFillColor(black_color)
            p.setFont("Helvetica", 10)
            p.drawString(50, height - 70, "Les spécialistes")
            
            # Title
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(width / 2, height - 50, "rapport intervention")
            
            # Right logo
            p.setFillColor(red_color)
            p.setFont("Helvetica-Bold", 20)
            p.drawRightString(width - 50, height - 50, "FCA")
            p.setFillColor(black_color)
            p.setFont("Helvetica", 10)
            p.drawRightString(width - 50, height - 70, "Les spécialistes")
            
            y_position = height - 120
            
            # General Information Section
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Informations Générales")
            y_position -= 30
            
            p.setFont("Helvetica", 10)
            # Left column
            date_str = form_data.get('date', '')
            time_str = form_data.get('time', '')
            p.drawString(50, y_position, f"Date: {date_str} à {time_str}")
            p.drawString(50, y_position - 20, f"Nom du TS intervenant: {form_data.get('technician_name', '')}")
            p.drawString(50, y_position - 40, f"N° de téléphone: {form_data.get('technician_phone', '')}")
            
            # Right column
            p.drawString(width / 2 + 20, y_position, f"Client: {form_data.get('client', '')}")
            p.drawString(width / 2 + 20, y_position - 20, f"Adresse: {form_data.get('address', '')}")
            p.drawString(width / 2 + 20, y_position - 40, f"Contact: {form_data.get('contact', '')}")
            
            y_position -= 60
            p.drawString(50, y_position, f"Site intervention: {form_data.get('intervention_site', '')}")
            y_position -= 30
            
            # Object of Intervention
            p.setFont("Helvetica-Bold", 12)
            p.drawCentredString(width / 2, y_position, "Objet de l'intervention")
            y_position -= 30
            
            p.setFont("Helvetica", 10)
            intervention_type = form_data.get('intervention_type', '')
            intervention_labels = {
                'preventive': 'Maintenance préventive.',
                'corrective': 'Maintenance corrective.',
                'installation': 'Installation / Mise en service.',
                'urgent': 'Dépannage urgent.',
                'other': f"Autre : {form_data.get('intervention_other', '')}"
            }
            if intervention_type in intervention_labels:
                p.drawString(50, y_position, f"☑ {intervention_labels[intervention_type]}")
            y_position -= 30
            
            # Equipment Table
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Équipements et Prestations")
            y_position -= 30
            
            equipment_items = form_data.get('equipment_items', [])
            if equipment_items:
                # Create paragraph styles for text wrapping
                styles = getSampleStyleSheet()
                cell_style = ParagraphStyle(
                    'TableCell',
                    parent=styles['Normal'],
                    fontSize=8,
                    leading=10,
                    alignment=TA_LEFT,
                    wordWrap='LTR',
                )
                header_style = ParagraphStyle(
                    'TableHeader',
                    parent=styles['Normal'],
                    fontSize=9,
                    leading=11,
                    fontName='Helvetica-Bold',
                    alignment=TA_LEFT,
                    wordWrap='LTR',
                )
                
                # Table headers
                headers = [
                    Paragraph('N°', header_style),
                    Paragraph('Equipement', header_style),
                    Paragraph('Emplacement', header_style),
                    Paragraph('Prestation', header_style),
                    Paragraph('Diagnostic', header_style),
                    Paragraph('Remède', header_style)
                ]
                col_widths = [1*cm, 3*cm, 2.5*cm, 3*cm, 3*cm, 3*cm]
                
                # Create table data with Paragraph objects for text wrapping
                table_data = [headers]
                for item in equipment_items:
                    table_data.append([
                        Paragraph(str(item.get('number', '')), cell_style),
                        Paragraph(str(item.get('equipment', '') or ''), cell_style),
                        Paragraph(str(item.get('location', '') or ''), cell_style),
                        Paragraph(str(item.get('service', '') or ''), cell_style),
                        Paragraph(str(item.get('diagnosis', '') or ''), cell_style),
                        Paragraph(str(item.get('remedy', '') or ''), cell_style)
                    ])
                
                # Draw table
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('WORDWRAP', (0, 0), (-1, -1), True),
                ]))
                
                # Calculate table height dynamically
                table_width = width - 100
                table.wrapOn(p, table_width, height)
                # Get the actual wrapped height
                table_height = table._height if hasattr(table, '_height') else (len(equipment_items) + 1) * 30
                table.drawOn(p, 50, y_position - table_height)
                y_position -= table_height + 20
            
            # Observations
            y_position -= 20
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Observations & Recommandations :")
            y_position -= 20
            p.setFont("Helvetica", 10)
            observations = form_data.get('observations', '')
            # Split long text into multiple lines
            words = observations.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + word) < 80:
                    current_line += word + " "
                else:
                    lines.append(current_line)
                    current_line = word + " "
            if current_line:
                lines.append(current_line)
            
            for line in lines[:10]:  # Limit to 10 lines
                p.drawString(50, y_position, line)
                y_position -= 15
            
            # Signatures
            y_position -= 20
            p.drawString(50, y_position, f"Signature du TS : {form_data.get('technician_signature', '')}")
            p.drawString(width / 2 + 20, y_position, f"Nom et signature du client : {form_data.get('client_signature', '')}")
            
            p.showPage()
            p.save()
            
            # Get PDF content
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            # Save PDF to TraveauxReport
            from django.core.files.base import ContentFile
            from django.utils import timezone
            
            report_file = ContentFile(pdf_content)
            report_file.name = f"rapport_intervention_{traveaux.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            report = TraveauxReport.objects.create(
                traveaux=traveaux,
                report_file=report_file,
                title=f"Rapport d'intervention - {form_data.get('date', '')}"
            )
            
            serializer = TraveauxReportSerializer(report, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"Error generating intervention report: {e}")
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def update_progress(self, request, pk=None):
        """
        Update the progress of a traveaux by updating quantity_completed
        """
        try:
            traveaux = self.get_object()
            quantity_completed = request.data.get('quantity_completed')
            
            if quantity_completed is None:
                return Response({'error': 'quantity_completed is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if quantity_completed < 0 or quantity_completed > traveaux.quantity:
                return Response({
                    'error': f'quantity_completed must be between 0 and {traveaux.quantity}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the quantity completed
            traveaux.quantity_completed = quantity_completed
            
            # Automatically update status based on progress
            traveaux.update_status()
            
            serializer = self.get_serializer(traveaux)
            return Response({
                'message': 'Progress updated successfully',
                'traveaux': serializer.data
            })
            
        except Traveaux.DoesNotExist:
            return Response({'error': 'Traveaux not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """
        Manually update the status of a traveaux
        """
        try:
            traveaux = self.get_object()
            new_status = request.data.get('status')
            
            if not new_status:
                return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate status choice
            valid_statuses = [choice[0] for choice in Traveaux.STATUS_CHOICES]
            if new_status not in valid_statuses:
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the status
            traveaux.status = new_status
            traveaux.save()
            
            # Return updated traveaux data
            serializer = self.get_serializer(traveaux)
            return Response({
                'message': f'Status updated to {new_status}',
                'traveaux': serializer.data
            })
            
        except Traveaux.DoesNotExist:
            return Response({'error': 'Traveaux not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """
        Get traveaux for a specific project
        """
        project_id = request.query_params.get('project_id')
        if project_id:
            traveaux = self.get_queryset().filter(project_id=project_id)
            serializer = self.get_serializer(traveaux, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """
        Get traveaux filtered by status
        """
        status = request.query_params.get('status')
        if status:
            traveaux = self.get_queryset().filter(status=status)
            serializer = self.get_serializer(traveaux, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_site(self, request):
        """
        Get traveaux for a specific site
        """
        site_id = request.query_params.get('site_id')
        if site_id:
            traveaux = self.get_queryset().filter(sites__id=site_id)
            serializer = self.get_serializer(traveaux, many=True)
            return Response(serializer.data)
        return Response([])


# Project Maintenance Viewsets
class ProjectMaintenanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProjectMaintenance model
    """
    queryset = ProjectMaintenance.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectMaintenanceListSerializer
        return ProjectMaintenanceSerializer
    
    def get_queryset(self):
        """
        Filter projects based on user role and permissions
        """
        user = self.request.user
        queryset = ProjectMaintenance.objects.select_related('client', 'contract', 'technician_group').prefetch_related('equipment', 'pdf_documents', 'facture_pdfs', 'pv_pdfs', 'quote_pdfs')
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'CLIENT':
            # Extract client ID from username (format: client_<id>)
            if user.username.startswith('client_'):
                try:
                    client_id = int(user.username.replace('client_', ''))
                    return queryset.filter(client_id=client_id)
                except ValueError:
                    return ProjectMaintenance.objects.none()
            # Fallback: return no projects if client ID can't be determined
            return ProjectMaintenance.objects.none()
        elif user.role == 'TECHNICIAN':
            # Filter projects assigned to technician's technician groups
            try:
                technician = user.technician_profile
                if not technician:
                    return ProjectMaintenance.objects.none()
                
                # Get all technician groups this technician belongs to
                technician_groups = technician.technician_groups.filter(status='ACTIVE')
                
                if technician_groups.exists():
                    technician_group_ids = list(technician_groups.values_list('id', flat=True))
                    return queryset.filter(
                        technician_group__in=technician_group_ids,
                        is_active=True
                    )
                else:
                    return ProjectMaintenance.objects.none()
            except (Technician.DoesNotExist, AttributeError):
                return ProjectMaintenance.objects.none()
        else:
            return ProjectMaintenance.objects.none()
    
    def create(self, request, *args, **kwargs):
        """
        Handle project creation with file upload support
        """
        import json
        try:
            # Handle equipment data from form data - use getlist as primary method
            equipment_ids = []
            if hasattr(request.data, 'getlist'):
                equipment_list = request.data.getlist('equipment')
                if equipment_list:
                    # Check if the first item is a JSON string (e.g., '[25,26]')
                    if len(equipment_list) == 1 and isinstance(equipment_list[0], str) and equipment_list[0].startswith('['):
                        try:
                            equipment_ids = json.loads(equipment_list[0])
                            print(f"DEBUG CREATE: Equipment from getlist (parsed JSON): {equipment_ids}")
                        except json.JSONDecodeError:
                            equipment_ids = [int(item) for item in equipment_list]
                            print(f"DEBUG CREATE: Equipment from getlist (direct): {equipment_ids}")
                    else:
                        equipment_ids = [int(item) for item in equipment_list]
                        print(f"DEBUG CREATE: Equipment from getlist: {equipment_ids}")
            
            # Fallback: Handle equipment data from form data
            if not equipment_ids and 'equipment' in request.data:
                equipment_data = request.data['equipment']
                try:
                    if isinstance(equipment_data, str):
                        equipment_ids = json.loads(equipment_data)
                    elif isinstance(equipment_data, list):
                        equipment_ids = [int(item) for item in equipment_data]
                    else:
                        equipment_ids = [int(equipment_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing equipment data: {e}")
                    print(f"DEBUG CREATE: equipment_data value: {equipment_data}")
                    equipment_ids = []
                print(f"DEBUG CREATE: Equipment from fallback: {equipment_ids}")

            # Handle additional equipment from form fields
            for key, value in request.data.items():
                if key.startswith('equipment[') and key.endswith(']'):
                    equipment_ids.append(int(value))

            data = request.data.copy()
            if 'equipment' in data:
                del data['equipment']
            if 'sites' in data:
                del data['sites']

            serializer = self.get_serializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)

            project = serializer.save()

            # Handle sites assignment after project creation - use getlist as primary method
            sites_ids = []
            if hasattr(request.data, 'getlist'):
                sites_list = request.data.getlist('sites')
                if sites_list:
                    # Check if the first item is a JSON string (e.g., '21]')
                    if len(sites_list) == 1 and isinstance(sites_list[0], str) and sites_list[0].startswith('['):
                        try:
                            sites_ids = json.loads(sites_list[0])
                            print(f"DEBUG CREATE: Sites from getlist (parsed JSON): {sites_ids}")
                        except json.JSONDecodeError:
                            sites_ids = [int(item) for item in sites_list]
                            print(f"DEBUG CREATE: Sites from getlist (direct): {sites_ids}")
                    else:
                        sites_ids = [int(item) for item in sites_list]
                        print(f"DEBUG CREATE: Sites from getlist: {sites_ids}")
            
            # Fallback: Handle sites data from form data
            if not sites_ids and 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        sites_ids = [int(item) for item in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []
                print(f"DEBUG CREATE: Sites from fallback: {sites_ids}")

            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))

            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                project.sites.set(sites_objects)

            # Handle equipment assignment after project creation
            print(f"DEBUG CREATE: Final equipment_ids: {equipment_ids}")
            if equipment_ids:
                equipment_objects = ClientEquipment.objects.filter(id__in=equipment_ids if isinstance(equipment_ids, list) else [equipment_ids])
                print(f"DEBUG CREATE: Found equipment objects: {[eq.id for eq in equipment_objects]}")
                project.equipment.set(equipment_objects)
                print(f"DEBUG CREATE: Project equipment count after set: {project.equipment.count()}")

            # Handle PDF uploads - extract and process files immediately
            pdf_files = request.FILES.getlist('pdf_files')
            pdf_titles = request.data.getlist('pdf_titles')
            
            # Handle different formats of pdf_titles - fix the iteration issue
            if not pdf_titles:
                pdf_titles = []
            elif isinstance(pdf_titles, str):
                try:
                    pdf_titles = json.loads(pdf_titles)
                except (json.JSONDecodeError, ValueError):
                    pdf_titles = [pdf_titles]
            elif not isinstance(pdf_titles, list):
                # Handle case where getlist returns a single value
                try:
                    pdf_titles = list(pdf_titles)
                except TypeError:
                    pdf_titles = [str(pdf_titles)]
            
            # Ensure pdf_titles is always a list
            if not isinstance(pdf_titles, list):
                pdf_titles = [str(pdf_titles)]
            
            # Ensure we have enough titles for all files
            while len(pdf_titles) < len(pdf_files):
                pdf_titles.append(f"PDF {len(pdf_titles) + 1}")
            
            print(f"DEBUG: Final PDF files count: {len(pdf_files)}")
            print(f"DEBUG: Final PDF titles: {pdf_titles}")
            print(f"DEBUG: Project ID: {project.id}")
            print(f"DEBUG: Project name: {project.project_name}")
            
            # Process each PDF file
            for i, pdf_file in enumerate(pdf_files):
                if pdf_file and i < len(pdf_titles):
                    title = pdf_titles[i] if pdf_titles[i] else f"PDF {i + 1}"
                    try:
                        ProjectMaintenancePDF.objects.create(
                            project=project,
                            pdf_file=pdf_file,
                            title=title
                        )
                        print(f"DEBUG: Created PDF {i + 1}: {title}")
                    except Exception as e:
                        print(f"DEBUG: Error creating PDF {i + 1}: {str(e)}")
                        continue
            
            # CRITICAL: Remove PDF file references from request data to prevent serialization
            # This prevents Django from trying to serialize the file objects later
            if 'pdf_files' in request.FILES:
                # Clear the FILES dictionary to remove file object references
                request.FILES.clear()
                print("DEBUG: Cleared request.FILES to remove file object references")
            
            # Also remove from request.data if present
            if hasattr(request, 'data') and 'pdf_files' in request.data:
                del request.data['pdf_files']
                print("DEBUG: Removed pdf_files from request.data")
            
            # Force garbage collection to clean up any remaining file objects
            import gc
            gc.collect()
            
            # Send notification if technician group is assigned
            if project.technician_group:
                from .notifications import notify_technicians_new_project
                try:
                    notify_technicians_new_project(project, project.technician_group)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending notification for new project: {str(e)}")
            
            # Return the created project with all its data
            response_serializer = self.get_serializer(project, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"DEBUG: Error in create method: {str(e)}")
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        """
        Create a new project maintenance
        """
        serializer.save()
    
    def update(self, request, *args, **kwargs):
        """
        Handle project update with equipment and sites
        """
        import json
        try:
            instance = self.get_object()
            
            # Handle equipment data from form data - use getlist as primary method
            equipment_ids = []
            if hasattr(request.data, 'getlist'):
                equipment_list = request.data.getlist('equipment')
                if equipment_list:
                    # Check if the first item is a JSON string (e.g., '[25,26]')
                    if len(equipment_list) == 1 and isinstance(equipment_list[0], str) and equipment_list[0].startswith('['):
                        try:
                            equipment_ids = json.loads(equipment_list[0])
                            print(f"DEBUG CREATE: Equipment from getlist (parsed JSON): {equipment_ids}")
                        except json.JSONDecodeError:
                            equipment_ids = [int(item) for item in equipment_list]
                            print(f"DEBUG CREATE: Equipment from getlist (direct): {equipment_ids}")
                    else:
                        equipment_ids = [int(item) for item in equipment_list]
                        print(f"DEBUG CREATE: Equipment from getlist: {equipment_ids}")
            
            # Fallback: Handle equipment data from form data
            if not equipment_ids and 'equipment' in request.data:
                equipment_data = request.data['equipment']
                try:
                    if isinstance(equipment_data, str):
                        equipment_ids = json.loads(equipment_data)
                    elif isinstance(equipment_data, list):
                        equipment_ids = [int(item) for item in equipment_data]
                    else:
                        equipment_ids = [int(equipment_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing equipment data: {e}")
                    print(f"DEBUG CREATE: equipment_data value: {equipment_data}")
                    equipment_ids = []
                print(f"DEBUG CREATE: Equipment from fallback: {equipment_ids}")

            # Handle additional equipment from form fields
            for key, value in request.data.items():
                if key.startswith('equipment[') and key.endswith(']'):
                    equipment_ids.append(int(value))

            data = request.data.copy()
            if 'equipment' in data:
                del data['equipment']

            serializer = self.get_serializer(instance, data=data, context={'request': request}, partial=kwargs.get('partial', False))
            serializer.is_valid(raise_exception=True)
            project = serializer.save()

            # Handle sites assignment
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        # Handle multiple sites sent as a list
                        sites_ids = [int(item) for item in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []

            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))

            if sites_ids:
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                project.sites.set(sites_objects)

            # Handle equipment assignment
            if equipment_ids:
                equipment_objects = ClientEquipment.objects.filter(id__in=equipment_ids if isinstance(equipment_ids, list) else [equipment_ids])
                project.equipment.set(equipment_objects)

            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        """
        Update a project maintenance
        """
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Delete a project maintenance
        """
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def upload_pdf(self, request, pk=None):
        """
        Upload a PDF document for the project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', '')
        
        if not pdf_file:
            return Response({'error': 'No PDF file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        pdf_doc = ProjectMaintenancePDF.objects.create(
            project=project,
            pdf_file=pdf_file,
            title=title
        )
        
        serializer = ProjectMaintenancePDFSerializer(pdf_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def upload_facture(self, request, pk=None):
        """
        Upload a Facture PDF for the project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', '')
        
        if not pdf_file:
            return Response({'error': 'No PDF file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        facture_doc = ProjectMaintenanceFacture.objects.create(
            project=project,
            pdf_file=pdf_file,
            title=title
        )
        
        serializer = ProjectMaintenanceFactureSerializer(facture_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def upload_pv(self, request, pk=None):
        """
        Upload a PV PDF for the project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', '')
        
        if not pdf_file:
            return Response({'error': 'No PDF file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        pv_doc = ProjectMaintenancePV.objects.create(
            project=project,
            pdf_file=pdf_file,
            title=title
        )
        
        serializer = ProjectMaintenancePVSerializer(pv_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def upload_quote(self, request, pk=None):
        """
        Upload a Quote PDF for the project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', '')
        
        if not pdf_file:
            return Response({'error': 'No PDF file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        quote_doc = ProjectMaintenanceQuote.objects.create(
            project=project,
            pdf_file=pdf_file,
            title=title
        )
        
        serializer = ProjectMaintenanceQuoteSerializer(quote_doc, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def by_client(self, request):
        """
        Get projects for a specific client
        """
        client_id = request.query_params.get('client_id')
        if client_id:
            projects = self.get_queryset().filter(client_id=client_id)
            serializer = self.get_serializer(projects, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_technician_group(self, request):
        """
        Get projects for a specific technician group
        """
        group_id = request.query_params.get('group_id')
        if group_id:
            projects = self.get_queryset().filter(technician_group_id=group_id)
            serializer = self.get_serializer(projects, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get only active projects
        """
        projects = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get expired projects
        """
        from django.utils import timezone
        projects = self.get_queryset().filter(finish_date__lt=timezone.now().date())
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_facture_pdfs(self, request, pk=None):
        """
        Get all facture PDFs for this project
        """
        project = self.get_object()
        facture_pdfs = project.facture_pdfs.all()
        serializer = ProjectMaintenanceFactureSerializer(facture_pdfs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_pv_pdfs(self, request, pk=None):
        """
        Get all PV PDFs for this project
        """
        project = self.get_object()
        pv_pdfs = project.pv_pdfs.all()
        serializer = ProjectMaintenancePVSerializer(pv_pdfs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def get_quote_pdfs(self, request, pk=None):
        """
        Get all quote PDFs for this project
        """
        project = self.get_object()
        quote_pdfs = project.quote_pdfs.all()
        serializer = ProjectMaintenanceQuoteSerializer(quote_pdfs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_facture_pdf(self, request, pk=None):
        """
        Add a facture PDF to this project
        """
        print(f"DEBUG PDF UPLOAD: add_facture_pdf called with pk={pk}")
        print(f"DEBUG PDF UPLOAD: Request method: {request.method}")
        print(f"DEBUG PDF UPLOAD: Request headers: {dict(request.headers)}")
        print(f"DEBUG PDF UPLOAD: Request data: {request.data}")
        print(f"DEBUG PDF UPLOAD: Request FILES: {request.FILES}")
        
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', 'Facture PDF')
        
        if not pdf_file:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            facture_pdf = ProjectMaintenanceFacture.objects.create(
                project=project,
                pdf_file=pdf_file,
                title=title
            )
            serializer = ProjectMaintenanceFactureSerializer(facture_pdf, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_pv_pdf(self, request, pk=None):
        """
        Add a PV PDF to this project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', 'PV PDF')
        
        if not pdf_file:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            pv_pdf = ProjectMaintenancePV.objects.create(
                project=project,
                pdf_file=pdf_file,
                title=title
            )
            serializer = ProjectMaintenancePVSerializer(pv_pdf, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_quote_pdf(self, request, pk=None):
        """
        Add a quote PDF to this project
        """
        project = self.get_object()
        pdf_file = request.FILES.get('pdf_file')
        title = request.data.get('title', 'Quote PDF')
        
        if not pdf_file:
            return Response({'error': 'PDF file is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quote_pdf = ProjectMaintenanceQuote.objects.create(
                project=project,
                pdf_file=pdf_file,
                title=title
            )
            serializer = ProjectMaintenanceQuoteSerializer(quote_pdf, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_facture_pdf(self, request, pk=None):
        """
        Remove a facture PDF from this project
        """
        project = self.get_object()
        pdf_id = request.data.get('pdf_id')
        
        if not pdf_id:
            return Response({'error': 'pdf_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            facture_pdf = ProjectMaintenanceFacture.objects.get(id=pdf_id, project=project)
            facture_pdf.delete()
            return Response({'message': 'Facture PDF removed successfully'})
        except ProjectMaintenanceFacture.DoesNotExist:
            return Response({'error': 'Facture PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def remove_pv_pdf(self, request, pk=None):
        """
        Remove a PV PDF from this project
        """
        project = self.get_object()
        pdf_id = request.data.get('pdf_id')
        
        if not pdf_id:
            return Response({'error': 'pdf_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            pv_pdf = ProjectMaintenancePV.objects.get(id=pdf_id, project=project)
            pv_pdf.delete()
            return Response({'message': 'PV PDF removed successfully'})
        except ProjectMaintenancePV.DoesNotExist:
            return Response({'error': 'PV PDF not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'])
    def remove_quote_pdf(self, request, pk=None):
        """
        Remove a quote PDF from this project
        """
        project = self.get_object()
        pdf_id = request.data.get('pdf_id')
        
        if not pdf_id:
            return Response({'error': 'pdf_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quote_pdf = ProjectMaintenanceQuote.objects.get(id=pdf_id, project=project)
            quote_pdf.delete()
            return Response({'message': 'Quote PDF removed successfully'})
        except ProjectMaintenanceQuote.DoesNotExist:
            return Response({'error': 'Quote PDF not found'}, status=status.HTTP_404_NOT_FOUND)


class MaintenanceTraveauxViewSet(viewsets.ModelViewSet):
    """
    ViewSet for MaintenanceTraveaux model
    """
    queryset = MaintenanceTraveaux.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MaintenanceTraveauxListSerializer
        return MaintenanceTraveauxSerializer
    
    def get_queryset(self):
        """
        Filter traveaux based on user role and permissions
        """
        user = self.request.user
        
        # Start with base queryset
        queryset = MaintenanceTraveaux.objects.select_related('project').prefetch_related('sites', 'reports')
        
        # Filter by project if project_id is provided
        project_id = self.request.query_params.get('project_id')
        if project_id:
            try:
                project_id = int(project_id)
                queryset = queryset.filter(project_id=project_id)
                print(f"DEBUG MaintenanceTraveaux: Filtering by project_id={project_id}, found {queryset.count()} traveaux")
            except (ValueError, TypeError) as e:
                # If project_id can't be converted to int, ignore the filter
                print(f"DEBUG MaintenanceTraveaux: Error converting project_id '{project_id}': {e}")
                pass
        
        if user.role == 'ADMIN':
            result = queryset
            print(f"DEBUG MaintenanceTraveaux: ADMIN user, returning {result.count()} traveaux")
            return result
        elif user.role == 'CLIENT':
            # Extract client ID from username (format: client_<id>)
            if user.username.startswith('client_'):
                try:
                    client_id = int(user.username.replace('client_', ''))
                    result = queryset.filter(project__client_id=client_id)
                    print(f"DEBUG MaintenanceTraveaux: CLIENT user (client_id={client_id}), returning {result.count()} traveaux")
                    return result
                except ValueError:
                    print(f"DEBUG MaintenanceTraveaux: CLIENT user - Error parsing client_id from username '{user.username}'")
                    return MaintenanceTraveaux.objects.none()
            # Fallback: try to filter by client__user if username doesn't match pattern
            result = queryset.filter(project__client__user=user)
            print(f"DEBUG MaintenanceTraveaux: CLIENT user (fallback), returning {result.count()} traveaux")
            return result
        elif user.role == 'TECHNICIAN':
            result = queryset.filter(project__technician_group__technicians__user=user)
            print(f"DEBUG MaintenanceTraveaux: TECHNICIAN user, returning {result.count()} traveaux")
            return result
        else:
            print(f"DEBUG MaintenanceTraveaux: Unknown role {user.role}, returning empty queryset")
            return MaintenanceTraveaux.objects.none()
    
    def create(self, request, *args, **kwargs):
        """
        Handle traveaux creation with sites assignment
        """
        import json
        try:
            # Handle sites data from form data
            sites_ids = []
            if 'sites' in request.data:
                sites_data = request.data['sites']
                try:
                    if isinstance(sites_data, str):
                        sites_ids = json.loads(sites_data)
                    elif isinstance(sites_data, list):
                        sites_ids = [int(site_id) for site_id in sites_data]
                    else:
                        sites_ids = [int(sites_data)]
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"DEBUG CREATE: Error parsing sites data: {e}")
                    print(f"DEBUG CREATE: sites_data value: {sites_data}")
                    sites_ids = []
            
            # Handle additional sites from form fields
            for key, value in request.data.items():
                if key.startswith('sites[') and key.endswith(']'):
                    sites_ids.append(int(value))
            
            # Handle scheduled dates
            scheduled_dates = request.data.get('scheduled_dates')
            if scheduled_dates:
                try:
                    if isinstance(scheduled_dates, str):
                        scheduled_dates = json.loads(scheduled_dates)
                except (json.JSONDecodeError, ValueError):
                    scheduled_dates = [scheduled_dates]
            
            data = request.data.copy()
            if 'sites' in data:
                del data['sites']
            if 'scheduled_dates' in data:
                del data['scheduled_dates']
            
            serializer = self.get_serializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            
            traveaux = serializer.save()
            
            # Handle sites assignment after traveaux creation
            if sites_ids:
                from core.models import Site
                sites_objects = Site.objects.filter(id__in=sites_ids if isinstance(sites_ids, list) else [sites_ids])
                traveaux.sites.set(sites_objects)
            
            # Handle scheduled dates assignment
            if scheduled_dates:
                traveaux.scheduled_dates = scheduled_dates
                traveaux.save()
            
            # Send notification for new task
            if traveaux.project and traveaux.project.technician_group:
                from .notifications import notify_technicians_new_task
                try:
                    notify_technicians_new_task(traveaux, traveaux.project)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error sending notification for new maintenance task: {str(e)}")
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        """
        Create a new maintenance traveaux
        """
        traveaux = serializer.save()
        
        # Send notification for new task
        if traveaux.project and traveaux.project.technician_group:
            from .notifications import notify_technicians_new_task
            try:
                notify_technicians_new_task(traveaux, traveaux.project)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending notification for new maintenance task: {str(e)}")
    
    def perform_update(self, serializer):
        """
        Update a maintenance traveaux
        """
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Delete a maintenance traveaux
        """
        instance.delete()
    
    @action(detail=True, methods=['patch'])
    def update_progress(self, request, pk=None):
        """
        Update the progress of a traveaux
        """
        traveaux = self.get_object()
        quantity_completed = request.data.get('quantity_completed')
        
        if quantity_completed is not None:
            traveaux.quantity_completed = quantity_completed
            traveaux.update_status()  # This will automatically update the status
            traveaux.save()
            
            serializer = self.get_serializer(traveaux)
            return Response(serializer.data)
        
        return Response({'error': 'quantity_completed is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(
        detail=True,
        methods=['get', 'post'],
        url_path='reports',
        parser_classes=[MultiPartParser, FormParser]
    )
    def manage_reports(self, request, pk=None):
        """
        List or upload PDF reports for a maintenance traveaux
        """
        traveaux = self.get_object()
        
        if request.method.lower() == 'get':
            serializer = MaintenanceTraveauxReportSerializer(
                traveaux.reports.all(),
                many=True,
                context={'request': request}
            )
            return Response(serializer.data)
        
        files = request.FILES.getlist('reports') or request.FILES.getlist('report_files')
        if not files:
            return Response({'error': 'Please provide at least one PDF report'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_reports = []
        for upload in files:
            if upload.content_type not in ('application/pdf', 'application/x-pdf'):
                return Response({'error': f'{upload.name} is not a PDF file'}, status=status.HTTP_400_BAD_REQUEST)
            report = MaintenanceTraveauxReport.objects.create(
                traveaux=traveaux,
                report_file=upload,
                title=request.data.get('title', '').strip()
            )
            created_reports.append(report)
        
        serializer = MaintenanceTraveauxReportSerializer(created_reports, many=True, context={'request': request})
        return Response({'message': 'Reports uploaded successfully', 'reports': serializer.data}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='reports/(?P<report_id>[^/.]+)')
    def delete_report(self, request, pk=None, report_id=None):
        """
        Delete a report attached to a maintenance traveaux
        """
        traveaux = self.get_object()
        try:
            report = traveaux.reports.get(pk=report_id)
            if report.report_file:
                report.report_file.delete(save=False)
            report.delete()
            return Response({'message': 'Report deleted successfully'})
        except MaintenanceTraveauxReport.DoesNotExist:
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='generate-intervention-report')
    def generate_intervention_report(self, request, pk=None):
        """
        Generate intervention report PDF from form data for maintenance traveaux
        """
        traveaux = self.get_object()
        
        try:
            # Get form data
            form_data = request.data
            
            # Create PDF buffer
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # Colors
            red_color = colors.HexColor('#FF0000')
            black_color = colors.HexColor('#000000')
            
            # Header with logo (simplified - you can add actual logo image)
            p.setFillColor(red_color)
            p.setFont("Helvetica-Bold", 20)
            p.drawString(50, height - 50, "FCA")
            p.setFillColor(black_color)
            p.setFont("Helvetica", 10)
            p.drawString(50, height - 70, "Les spécialistes")
            
            # Title
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(width / 2, height - 50, "rapport intervention")
            
            # Right logo
            p.setFillColor(red_color)
            p.setFont("Helvetica-Bold", 20)
            p.drawRightString(width - 50, height - 50, "FCA")
            p.setFillColor(black_color)
            p.setFont("Helvetica", 10)
            p.drawRightString(width - 50, height - 70, "Les spécialistes")
            
            y_position = height - 120
            
            # General Information Section
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Informations Générales")
            y_position -= 30
            
            p.setFont("Helvetica", 10)
            # Left column
            date_str = form_data.get('date', '')
            time_str = form_data.get('time', '')
            p.drawString(50, y_position, f"Date: {date_str} à {time_str}")
            p.drawString(50, y_position - 20, f"Nom du TS intervenant: {form_data.get('technician_name', '')}")
            p.drawString(50, y_position - 40, f"N° de téléphone: {form_data.get('technician_phone', '')}")
            
            # Right column
            p.drawString(width / 2 + 20, y_position, f"Client: {form_data.get('client', '')}")
            p.drawString(width / 2 + 20, y_position - 20, f"Adresse: {form_data.get('address', '')}")
            p.drawString(width / 2 + 20, y_position - 40, f"Contact: {form_data.get('contact', '')}")
            
            y_position -= 60
            p.drawString(50, y_position, f"Site intervention: {form_data.get('intervention_site', '')}")
            y_position -= 30
            
            # Object of Intervention
            p.setFont("Helvetica-Bold", 12)
            p.drawCentredString(width / 2, y_position, "Objet de l'intervention")
            y_position -= 30
            
            p.setFont("Helvetica", 10)
            intervention_type = form_data.get('intervention_type', '')
            intervention_labels = {
                'preventive': 'Maintenance préventive.',
                'corrective': 'Maintenance corrective.',
                'installation': 'Installation / Mise en service.',
                'urgent': 'Dépannage urgent.',
                'other': f"Autre : {form_data.get('intervention_other', '')}"
            }
            if intervention_type in intervention_labels:
                p.drawString(50, y_position, f"☑ {intervention_labels[intervention_type]}")
            y_position -= 30
            
            # Equipment Table
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Équipements et Prestations")
            y_position -= 30
            
            equipment_items = form_data.get('equipment_items', [])
            if equipment_items:
                # Create paragraph styles for text wrapping
                styles = getSampleStyleSheet()
                cell_style = ParagraphStyle(
                    'TableCell',
                    parent=styles['Normal'],
                    fontSize=8,
                    leading=10,
                    alignment=TA_LEFT,
                    wordWrap='LTR',
                )
                header_style = ParagraphStyle(
                    'TableHeader',
                    parent=styles['Normal'],
                    fontSize=9,
                    leading=11,
                    fontName='Helvetica-Bold',
                    alignment=TA_LEFT,
                    wordWrap='LTR',
                )
                
                # Table headers
                headers = [
                    Paragraph('N°', header_style),
                    Paragraph('Equipement', header_style),
                    Paragraph('Emplacement', header_style),
                    Paragraph('Prestation', header_style),
                    Paragraph('Diagnostic', header_style),
                    Paragraph('Remède', header_style)
                ]
                col_widths = [1*cm, 3*cm, 2.5*cm, 3*cm, 3*cm, 3*cm]
                
                # Create table data with Paragraph objects for text wrapping
                table_data = [headers]
                for item in equipment_items:
                    table_data.append([
                        Paragraph(str(item.get('number', '')), cell_style),
                        Paragraph(str(item.get('equipment', '') or ''), cell_style),
                        Paragraph(str(item.get('location', '') or ''), cell_style),
                        Paragraph(str(item.get('service', '') or ''), cell_style),
                        Paragraph(str(item.get('diagnosis', '') or ''), cell_style),
                        Paragraph(str(item.get('remedy', '') or ''), cell_style)
                    ])
                
                # Draw table
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('WORDWRAP', (0, 0), (-1, -1), True),
                ]))
                
                # Calculate table height dynamically
                table_width = width - 100
                table.wrapOn(p, table_width, height)
                # Get the actual wrapped height
                table_height = table._height if hasattr(table, '_height') else (len(equipment_items) + 1) * 30
                table.drawOn(p, 50, y_position - table_height)
                y_position -= table_height + 20
            
            # Observations
            y_position -= 20
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Observations & Recommandations :")
            y_position -= 20
            p.setFont("Helvetica", 10)
            observations = form_data.get('observations', '')
            # Split long text into multiple lines
            words = observations.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line + word) < 80:
                    current_line += word + " "
                else:
                    lines.append(current_line)
                    current_line = word + " "
            if current_line:
                lines.append(current_line)
            
            for line in lines[:10]:  # Limit to 10 lines
                p.drawString(50, y_position, line)
                y_position -= 15
            
            # Signatures
            y_position -= 20
            p.drawString(50, y_position, f"Signature du TS : {form_data.get('technician_signature', '')}")
            p.drawString(width / 2 + 20, y_position, f"Nom et signature du client : {form_data.get('client_signature', '')}")
            
            p.showPage()
            p.save()
            
            # Get PDF content
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            # Save PDF to MaintenanceTraveauxReport
            from django.core.files.base import ContentFile
            from django.utils import timezone
            
            report_file = ContentFile(pdf_content)
            report_file.name = f"rapport_intervention_{traveaux.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            report = MaintenanceTraveauxReport.objects.create(
                traveaux=traveaux,
                report_file=report_file,
                title=f"Rapport d'intervention - {form_data.get('date', '')}"
            )
            
            serializer = MaintenanceTraveauxReportSerializer(report, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"Error generating intervention report: {e}")
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_project(self, request):
        """
        Get traveaux for a specific project
        """
        project_id = request.query_params.get('project_id')
        if project_id:
            traveaux = self.get_queryset().filter(project_id=project_id)
            serializer = self.get_serializer(traveaux, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """
        Get traveaux filtered by status
        """
        status = request.query_params.get('status')
        if status:
            traveaux = self.get_queryset().filter(status=status)
            serializer = self.get_serializer(traveaux, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def by_site(self, request):
        """
        Get traveaux for a specific site
        """
        site_id = request.query_params.get('site_id')
        if site_id:
            traveaux = self.get_queryset().filter(sites__id=site_id)
            serializer = self.get_serializer(traveaux, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """
        Get completed traveaux
        """
        traveaux = self.get_queryset().filter(status='FINISHED')
        serializer = self.get_serializer(traveaux, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def ongoing(self, request):
        """
        Get ongoing traveaux
        """
        traveaux = self.get_queryset().filter(status='ONGOING')


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DeviceToken model - manages push notification tokens
    """
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Filter device tokens based on user role
        """
        user = self.request.user
        queryset = DeviceToken.objects.select_related('technician')
        
        if user.role == 'ADMIN':
            return queryset
        elif user.role == 'TECHNICIAN':
            # Technicians can only see their own tokens
            try:
                technician = user.technician_profile
                if technician:
                    return queryset.filter(technician=technician)
            except (Technician.DoesNotExist, AttributeError):
                pass
            return DeviceToken.objects.none()
        else:
            return DeviceToken.objects.none()
    
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        """
        Custom endpoint to register or update device token
        Handles both create and update in one endpoint
        """
        user = request.user
        if user.role != 'TECHNICIAN':
            return Response(
                {'error': 'Only technicians can register device tokens'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            technician = user.technician_profile
            if not technician:
                return Response(
                    {'error': 'Technician profile not found'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            token = request.data.get('token')
            device_type = request.data.get('device_type', 'ANDROID')
            
            if not token:
                return Response(
                    {'error': 'Token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if token exists for this technician
            device_token = DeviceToken.objects.filter(
                technician=technician,
                token=token
            ).first()
            
            if device_token:
                # Update existing token
                device_token.device_type = device_type
                device_token.is_active = True
                device_token.save()
                serializer = self.get_serializer(device_token)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # Check if token exists for another technician (update to point to this technician)
                existing_token = DeviceToken.objects.filter(token=token).first()
                
                if existing_token:
                    # Update existing token to point to this technician
                    existing_token.technician = technician
                    existing_token.device_type = device_type
                    existing_token.is_active = True
                    existing_token.save()
                    serializer = self.get_serializer(existing_token)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    # Create new token for this technician
                    device_token = DeviceToken.objects.create(
                        technician=technician,
                        token=token,
                        device_type=device_type,
                        is_active=True
                    )
                    serializer = self.get_serializer(device_token)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Technician.DoesNotExist:
            return Response(
                {'error': 'Technician profile not found'},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def perform_create(self, serializer):
        """
        Create or update device token for the authenticated technician
        """
        user = self.request.user
        if user.role != 'TECHNICIAN':
            raise permissions.PermissionDenied("Only technicians can register device tokens")
        
        try:
            technician = user.technician_profile
            if not technician:
                raise permissions.PermissionDenied("Technician profile not found")
            
            token = serializer.validated_data.get('token')
            device_type = serializer.validated_data.get('device_type', 'ANDROID')
            
            # Check if token exists for this technician
            device_token = DeviceToken.objects.filter(
                technician=technician,
                token=token
            ).first()
            
            if device_token:
                # Update existing token
                device_token.device_type = device_type
                device_token.is_active = True
                device_token.save()
            else:
                # Check if token exists for another technician (update to point to this technician)
                existing_token = DeviceToken.objects.filter(token=token).first()
                
                if existing_token:
                    # Update existing token to point to this technician
                    existing_token.technician = technician
                    existing_token.device_type = device_type
                    existing_token.is_active = True
                    existing_token.save()
                    device_token = existing_token
                else:
                    # Create new token for this technician
                    device_token = DeviceToken.objects.create(
                        technician=technician,
                        token=token,
                        device_type=device_type,
                        is_active=True
                    )
            
            serializer.instance = device_token
        except Technician.DoesNotExist:
            raise permissions.PermissionDenied("Technician profile not found")

