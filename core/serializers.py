from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, Site, Technician, TeamGroup, Equipment, ClientEquipment, TechnicianGroup, Contract, ProjectInstallation, ProjectInstallationPDF, ProjectInstallationFacture, ProjectInstallationPV, ProjectInstallationQuote, Traveaux, TraveauxReport, ProjectMaintenance, ProjectMaintenancePDF, ProjectMaintenanceFacture, ProjectMaintenancePV, ProjectMaintenanceQuote, MaintenanceTraveaux, MaintenanceTraveauxReport, DeviceToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    client_name = serializers.SerializerMethodField()
    client_id = serializers.SerializerMethodField()
    technician_id = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    identification_number = serializers.SerializerMethodField()
    speciality = serializers.SerializerMethodField()
    date_of_enrollment = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 
            'date_joined', 'client_name', 'client_id', 'technician_id', 'phone_number',
            'identification_number', 'speciality', 'date_of_enrollment'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_client_name(self, obj):
        """Get client name if user is a client"""
        if obj.username.startswith('client_'):
            try:
                client_id = int(obj.username.replace('client_', ''))
                from .models import Client
                client = Client.objects.get(pk=client_id)
                return client.name
            except (Client.DoesNotExist, ValueError):
                return None
        return None
    
    def get_client_id(self, obj):
        """Get client ID if user is a client"""
        if obj.username.startswith('client_'):
            try:
                client_id = int(obj.username.replace('client_', ''))
                return client_id
            except ValueError:
                return None
        return None
    
    def get_technician_id(self, obj):
        """Get technician ID if user is a technician"""
        if hasattr(obj, 'technician_profile'):
            try:
                return obj.technician_profile.id
            except:
                return None
        return None
    
    def get_phone_number(self, obj):
        """Get phone number if user is a technician"""
        if hasattr(obj, 'technician_profile'):
            try:
                return obj.technician_profile.phone_number or None
            except:
                return None
        return None
    
    def get_identification_number(self, obj):
        """Get identification number if user is a technician"""
        if hasattr(obj, 'technician_profile'):
            try:
                return obj.technician_profile.identification_number or None
            except:
                return None
        return None
    
    def get_speciality(self, obj):
        """Get speciality if user is a technician"""
        if hasattr(obj, 'technician_profile'):
            try:
                return obj.technician_profile.speciality or None
            except:
                return None
        return None
    
    def get_date_of_enrollment(self, obj):
        """Get date of enrollment if user is a technician"""
        if hasattr(obj, 'technician_profile'):
            try:
                return obj.technician_profile.date_of_enrollment or None
            except:
                return None
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for User creation
    """
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'password']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client model. Only name is required for creation;
    code_client, telephone1, and password are auto-generated if omitted.
    """
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    token = serializers.CharField(read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'code_client', 'email', 'telephone1', 'telephone2',
            'website', 'logo', 'social_media_link', 'status_juridique',
            'date_creation', 'sites_count', 'equipment_count',
            'password', 'token', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_creation', 'token', 'created_at', 'updated_at']
        extra_kwargs = {
            'code_client': {'required': False, 'allow_blank': True},
            'telephone1': {'required': False, 'allow_blank': True},
            'telephone2': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'website': {'required': False, 'allow_blank': True},
            'social_media_link': {'required': False, 'allow_blank': True},
            'logo': {'required': False},
            'status_juridique': {'required': False},
        }

    def get_sites_count(self, obj):
        return obj.sites.count()
    
    def get_equipment_count(self, obj):
        return obj.client_equipment.count()
    
    def create(self, validated_data):
        # Extract email and password (password optional, use default if missing)
        email = validated_data.pop('email', None) or None
        raw_password = validated_data.pop('password', None)
        if not raw_password or not str(raw_password).strip():
            raw_password = 'password123'
        
        # Generate unique code_client if not provided
        if not validated_data.get('code_client') or not str(validated_data.get('code_client', '')).strip():
            import uuid
            validated_data['code_client'] = f"CLIENT_{str(uuid.uuid4())[:8].upper()}"
        
        # Handle empty telephone1 - use default if empty
        if not validated_data.get('telephone1') or not str(validated_data.get('telephone1', '')).strip():
            validated_data['telephone1'] = '0000000000'
        
        # Normalize optional URL/string fields to None if empty
        for key in ('website', 'social_media_link', 'telephone2'):
            if key in validated_data and validated_data[key] is not None and str(validated_data[key]).strip() == '':
                validated_data[key] = None
        
        # Create client directly (no User account needed)
        client = Client.objects.create(
            email=email,
            password=raw_password,  # Stored then hashed below
            **validated_data
        )
        
        # Hash the password
        client.set_password(raw_password)
        client.save()
        
        return client
    
    def update(self, instance, validated_data):
        # Handle password update if provided
        password = validated_data.pop('password', None)
        email = validated_data.pop('email', None)
        
        # Update client fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update email if provided
        if email:
            instance.email = email
        
        # Update password if provided
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class SiteSerializer(serializers.ModelSerializer):
    """
    Serializer for Site model
    """
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Site
        fields = [
            'id', 'title', 'client', 'client_name', 'address',
            'city', 'wilaya', 'postal_code', 'country', 'sector',
            'nif', 'nis', 'rc', 'region', 'number_of_workers',
            'latitude', 'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Equipment model
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Equipment
        fields = [
            'id', 'code', 'full_name', 'brand', 'model_number', 'image', 'image_url',
            'description', 'specifications', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'image_url', 'created_at', 'updated_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ClientEquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for ClientEquipment model
    """
    equipment_name = serializers.CharField(source='equipment.full_name', read_only=True)
    equipment_brand = serializers.CharField(source='equipment.brand', read_only=True)
    equipment_model = serializers.CharField(source='equipment.model_number', read_only=True)
    site_title = serializers.CharField(source='site.title', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    # For reading: nested objects
    equipment = serializers.SerializerMethodField()
    site = serializers.SerializerMethodField()
    
    # For writing: ID fields (use source to map to the FK fields)
    equipment_id = serializers.PrimaryKeyRelatedField(
        queryset=Equipment.objects.all(),
        source='equipment',
        write_only=True,
        required=False
    )
    site_id = serializers.PrimaryKeyRelatedField(
        queryset=Site.objects.all(),
        source='site',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = ClientEquipment
        fields = [
            'id', 'client', 'client_name', 'equipment', 'equipment_id', 'site', 'site_id', 'site_title',
            'equipment_name', 'equipment_brand', 'equipment_model', 'serial_number',
            'year_of_facturation', 'installation_date', 'warranty_expiry', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_equipment(self, obj):
        """Return nested equipment object"""
        if obj.equipment:
            return {
                'id': obj.equipment.id,
                'brand': obj.equipment.brand,
                'full_name': obj.equipment.full_name,
            }
        return None
    
    def get_site(self, obj):
        """Return nested site object if it exists"""
        if obj.site:
            return {
                'id': obj.site.id,
                'title': obj.site.title
            }
        return None


class TechnicianSerializer(serializers.ModelSerializer):
    """
    Serializer for Technician model
    """
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Technician
        fields = [
            'id', 'first_name', 'last_name', 'identification_number', 'picture',
            'date_of_enrollment', 'speciality', 'status', 'phone_number', 'email',
            'password', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        technician = Technician.objects.create(**validated_data)
        if password:
            technician.set_password(password)
            technician.save()
        return technician
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class TeamGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for TeamGroup model
    """
    class Meta:
        model = TeamGroup
        fields = [
            'id', 'name', 'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TeamGroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for TeamGroup list view
    """
    class Meta:
        model = TeamGroup
        fields = ['id', 'name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class TechnicianGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for TechnicianGroup model
    """
    technicians_count = serializers.SerializerMethodField()
    chef_technician_name = serializers.CharField(source='chef_technician.__str__', read_only=True)
    is_at_capacity = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TechnicianGroup
        fields = [
            'id', 'name', 'specialty', 'specialty_display', 'description',
            'chef_technician', 'chef_technician_name', 'technicians', 'technicians_count',
            'status', 'status_display', 'max_capacity', 'current_assignment',
            'equipment_specialization', 'is_at_capacity', 'available_slots',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.get_technicians_count()
    
    def get_is_at_capacity(self, obj):
        return obj.is_at_capacity()
    
    def get_available_slots(self, obj):
        return obj.get_available_slots()


class TechnicianGroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for TechnicianGroup list view
    """
    technicians_count = serializers.SerializerMethodField()
    chef_technician_name = serializers.CharField(source='chef_technician.__str__', read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TechnicianGroup
        fields = [
            'id', 'name', 'specialty', 'specialty_display', 'description',
            'chef_technician', 'chef_technician_name', 'technicians_count',
            'status', 'status_display', 'max_capacity', 'current_assignment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.get_technicians_count()


class ContractSerializer(serializers.ModelSerializer):
    """
    Serializer for Contract model
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    equipment_data = ClientEquipmentSerializer(source='equipment', many=True, read_only=True)
    contract_type_display = serializers.CharField(source='get_contract_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    pdf_document_url = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 'code', 'client', 'client_name', 'sites', 'sites_data', 'sites_count',
            'description', 'creation_date', 'starting_date', 'ending_date',
            'contract_type', 'contract_type_display', 'status', 'status_display', 'equipment_data',
            'equipment_count', 'prix_ht', 'prix_ttc', 'is_active', 'is_expired',
            'days_until_expiry', 'pdf_document', 'pdf_document_url', 'contract_duration_years',
            'maintenance_frequency_per_year', 'create_project_maintenance_automatically', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'creation_date', 'created_at', 'updated_at']

    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]

    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()

    def get_equipment_count(self, obj):
        return obj.equipment.count()

    def get_contract_type_display(self, obj):
        return obj.get_contract_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry()
    
    def get_pdf_document_url(self, obj):
        if obj.pdf_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_document.url)
            return obj.pdf_document.url
        return None


class ContractListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Contract list view
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    equipment_data = ClientEquipmentSerializer(source='equipment', many=True, read_only=True)
    contract_type_display = serializers.CharField(source='get_contract_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    pdf_document_url = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 'code', 'client', 'client_name', 'sites', 'sites_data', 'sites_count', 'contract_type',
            'contract_type_display', 'status', 'status_display', 'equipment_data', 'equipment_count', 'prix_ht', 'prix_ttc',
            'starting_date', 'ending_date', 'is_active', 'is_expired',
            'days_until_expiry', 'pdf_document_url', 'contract_duration_years',
            'maintenance_frequency_per_year', 'create_project_maintenance_automatically', 'creation_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'creation_date', 'created_at', 'updated_at']

    def get_sites_data(self, obj):
        """Get detailed sites data for list view"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title} for site in sites]

    def get_sites_count(self, obj):
        """Get number of sites for list view"""
        return obj.sites.count()

    def get_equipment_count(self, obj):
        return obj.equipment.count()

    def get_contract_type_display(self, obj):
        return obj.get_contract_type_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry()
    
    def get_pdf_document_url(self, obj):
        if obj.pdf_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_document.url)
            return obj.pdf_document.url
        return None


class ProjectInstallationPDFSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectInstallationPDF model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInstallationPDF
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectInstallationFactureSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectInstallationFacture model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInstallationFacture
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectInstallationPVSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectInstallationPV model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInstallationPV
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectInstallationQuoteSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectInstallationQuote model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInstallationQuote
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectInstallationSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectInstallation model
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    contract_code = serializers.CharField(source='contract.code', read_only=True)
    technician_group_name = serializers.CharField(source='technician_group.name', read_only=True)
    technician_group_specialty = serializers.CharField(source='technician_group.specialty', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_data = ClientEquipmentSerializer(source='equipment', many=True, read_only=True)
    equipment_count = serializers.SerializerMethodField()
    complexity_display = serializers.CharField(source='get_complexity_display', read_only=True)
    pdf_documents = ProjectInstallationPDFSerializer(many=True, read_only=True)
    facture_pdfs = ProjectInstallationFactureSerializer(many=True, read_only=True)
    pv_pdfs = ProjectInstallationPVSerializer(many=True, read_only=True)
    quote_pdfs = ProjectInstallationQuoteSerializer(many=True, read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_finish = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInstallation
        fields = [
            'id', 'project_code', 'project_name', 'contract', 'contract_code',
            'client', 'client_name', 'sites_data', 'sites_count',
            'description', 'date_creation', 'start_date', 'finish_date', 
            'equipment_data', 'equipment_count',
            'technician_group', 'technician_group_name', 'technician_group_specialty',
            'complexity', 'complexity_display', 'is_active', 'pdf_documents',
            'facture_pdfs', 'pv_pdfs', 'quote_pdfs',
            'is_expired', 'days_until_finish', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'project_code', 'date_creation', 'created_at', 'updated_at']
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]

    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()

    def get_equipment_count(self, obj):
        return obj.equipment.count()
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        return timezone.now().date() > obj.finish_date
    
    def get_days_until_finish(self, obj):
        from django.utils import timezone
        delta = obj.finish_date - timezone.now().date()
        return delta.days


class ProjectInstallationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for ProjectInstallation list view
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    contract_code = serializers.CharField(source='contract.code', read_only=True)
    technician_group_name = serializers.CharField(source='technician_group.name', read_only=True)
    technician_group_specialty = serializers.CharField(source='technician_group.specialty', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    complexity_display = serializers.CharField(source='get_complexity_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectInstallation
        fields = [
            'id', 'project_code', 'project_name', 'contract', 'contract_code',
            'client', 'client_name', 'start_date', 'finish_date', 'sites_data', 'sites_count',
            'equipment_count', 'technician_group', 'technician_group_name', 'technician_group_specialty',
            'complexity', 'complexity_display', 'is_active', 'is_expired',
            'date_creation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'project_code', 'date_creation', 'created_at', 'updated_at']
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        return obj.sites.count()

    def get_equipment_count(self, obj):
        return obj.equipment.count()
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        return timezone.now().date() > obj.finish_date


class TraveauxReportSerializer(serializers.ModelSerializer):
    """
    Serializer for TraveauxReport model
    """
    report_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TraveauxReport
        fields = ['id', 'traveaux', 'title', 'report_url', 'uploaded_at']
        read_only_fields = ['id', 'traveaux', 'report_url', 'uploaded_at']
    
    def get_report_url(self, obj):
        if obj.report_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.report_file.url)
            return obj.report_file.url
        return None


class TraveauxSerializer(serializers.ModelSerializer):
    """
    Serializer for Traveaux model
    """
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    reports = TraveauxReportSerializer(many=True, read_only=True)
    
    class Meta:
        model = Traveaux
        fields = [
            'id', 'project', 'project_code', 'project_name', 'title', 'description',
            'quantity', 'quantity_completed', 'status', 'status_display', 'estimated_time',
            'sites', 'sites_data', 'sites_count', 'scheduled_dates', 'progress_percentage',
            'is_completed', 'reports', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()
    
    def to_internal_value(self, data):
        """Override to handle estimated_time conversion before validation"""
        # Handle estimated_time conversion
        if 'estimated_time' in data and isinstance(data['estimated_time'], str):
            estimated_time = data['estimated_time']
            try:
                from datetime import timedelta
                import re
                
                # Parse common duration formats
                if 'hour' in estimated_time.lower():
                    hours = int(re.findall(r'\d+', estimated_time)[0])
                    td = timedelta(hours=hours)
                    # Convert to the format Django expects: seconds
                    data['estimated_time'] = str(int(td.total_seconds()))
                elif 'day' in estimated_time.lower():
                    days = int(re.findall(r'\d+', estimated_time)[0])
                    td = timedelta(days=days)
                    data['estimated_time'] = str(int(td.total_seconds()))
                elif 'minute' in estimated_time.lower():
                    minutes = int(re.findall(r'\d+', estimated_time)[0])
                    td = timedelta(minutes=minutes)
                    data['estimated_time'] = str(int(td.total_seconds()))
            except (ValueError, IndexError):
                # If parsing fails, keep the original value
                pass
        
        return super().to_internal_value(data)


class TraveauxListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Traveaux list view
    """
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    sites_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    reports = TraveauxReportSerializer(many=True, read_only=True)
    
    class Meta:
        model = Traveaux
        fields = [
            'id', 'project', 'project_code', 'project_name', 'title', 'description',
            'quantity', 'quantity_completed', 'status', 'status_display', 'estimated_time',
            'sites_count', 'scheduled_dates', 'progress_percentage', 'is_completed', 'reports',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()


# Project Maintenance Serializers
class ProjectMaintenancePDFSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMaintenancePDF model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMaintenancePDF
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectMaintenanceFactureSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMaintenanceFacture model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMaintenanceFacture
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectMaintenancePVSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMaintenancePV model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMaintenancePV
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectMaintenanceQuoteSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMaintenanceQuote model
    """
    pdf_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMaintenanceQuote
        fields = [
            'id', 'project', 'pdf_file_url', 'title', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def get_pdf_file_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class ProjectMaintenanceSerializer(serializers.ModelSerializer):
    """
    Serializer for ProjectMaintenance model
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    contract_code = serializers.CharField(source='contract.code', read_only=True)
    technician_group_name = serializers.CharField(source='technician_group.name', read_only=True)
    technician_group_specialty = serializers.CharField(source='technician_group.specialty', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_data = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    complexity_display = serializers.CharField(source='get_complexity_display', read_only=True)
    pdf_documents = ProjectMaintenancePDFSerializer(many=True, read_only=True)
    facture_pdfs = ProjectMaintenanceFactureSerializer(many=True, read_only=True)
    pv_pdfs = ProjectMaintenancePVSerializer(many=True, read_only=True)
    quote_pdfs = ProjectMaintenanceQuoteSerializer(many=True, read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_finish = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMaintenance
        fields = [
            'id', 'project_code', 'project_name', 'contract', 'contract_code',
            'client', 'client_name', 'sites_data', 'sites_count',
            'description', 'date_creation', 'start_date', 'finish_date', 
            'equipment_data', 'equipment_count',
            'technician_group', 'technician_group_name', 'technician_group_specialty',
            'complexity', 'complexity_display', 'is_active', 'pdf_documents',
            'facture_pdfs', 'pv_pdfs', 'quote_pdfs',
            'is_expired', 'days_until_finish', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'project_code', 'date_creation', 'created_at', 'updated_at']
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]

    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()

    def get_equipment_data(self, obj):
        """Get equipment data"""
        equipment = obj.equipment.all()
        return [{'id': eq.id, 'equipment_name': eq.equipment.full_name, 'serial_number': eq.serial_number} for eq in equipment]

    def get_equipment_count(self, obj):
        return obj.equipment.count()
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        return timezone.now().date() > obj.finish_date
    
    def get_days_until_finish(self, obj):
        from django.utils import timezone
        delta = obj.finish_date - timezone.now().date()
        return delta.days


class ProjectMaintenanceListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for ProjectMaintenance list view
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    contract_code = serializers.CharField(source='contract.code', read_only=True)
    technician_group_name = serializers.CharField(source='technician_group.name', read_only=True)
    technician_group_specialty = serializers.CharField(source='technician_group.specialty', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    complexity_display = serializers.CharField(source='get_complexity_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = ProjectMaintenance
        fields = [
            'id', 'project_code', 'project_name', 'contract', 'contract_code',
            'client', 'client_name', 'start_date', 'finish_date', 'sites_data', 'sites_count',
            'equipment_count', 'technician_group', 'technician_group_name', 'technician_group_specialty',
            'complexity', 'complexity_display', 'is_active', 'is_expired',
            'date_creation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'project_code', 'date_creation', 'created_at', 'updated_at']
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        return obj.sites.count()

    def get_equipment_count(self, obj):
        return obj.equipment.count()
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        return timezone.now().date() > obj.finish_date


class MaintenanceTraveauxReportSerializer(serializers.ModelSerializer):
    """
    Serializer for MaintenanceTraveauxReport model
    """
    report_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceTraveauxReport
        fields = ['id', 'traveaux', 'title', 'report_url', 'uploaded_at']
        read_only_fields = ['id', 'traveaux', 'report_url', 'uploaded_at']
    
    def get_report_url(self, obj):
        if obj.report_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.report_file.url)
            return obj.report_file.url
        return None


class MaintenanceTraveauxSerializer(serializers.ModelSerializer):
    """
    Serializer for MaintenanceTraveaux model
    """
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    reports = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceTraveaux
        fields = [
            'id', 'project', 'project_code', 'project_name', 'title', 'description',
            'quantity', 'quantity_completed', 'status', 'status_display', 'estimated_time',
            'sites', 'sites_data', 'sites_count', 'scheduled_dates', 'progress_percentage',
            'is_completed', 'reports', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()
    
    def get_reports(self, obj):
        """Return serialized reports"""
        reports = obj.reports.all()
        serializer = MaintenanceTraveauxReportSerializer(reports, many=True, context=self.context)
        return serializer.data
    
    def to_internal_value(self, data):
        """Override to handle estimated_time conversion before validation"""
        # Handle estimated_time conversion
        if 'estimated_time' in data and isinstance(data['estimated_time'], str):
            estimated_time = data['estimated_time']
            try:
                from datetime import timedelta
                import re
                
                # Parse common duration formats
                if 'hour' in estimated_time.lower():
                    hours = int(re.findall(r'\d+', estimated_time)[0])
                    td = timedelta(hours=hours)
                    # Convert to the format Django expects: seconds
                    data['estimated_time'] = str(int(td.total_seconds()))
                elif 'day' in estimated_time.lower():
                    days = int(re.findall(r'\d+', estimated_time)[0])
                    td = timedelta(days=days)
                    data['estimated_time'] = str(int(td.total_seconds()))
                elif 'minute' in estimated_time.lower():
                    minutes = int(re.findall(r'\d+', estimated_time)[0])
                    td = timedelta(minutes=minutes)
                    data['estimated_time'] = str(int(td.total_seconds()))
            except (ValueError, IndexError):
                # If parsing fails, keep the original value
                pass
        
        return super().to_internal_value(data)


class MaintenanceTraveauxListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for MaintenanceTraveaux list view
    """
    project_code = serializers.CharField(source='project.project_code', read_only=True)
    project_name = serializers.CharField(source='project.project_name', read_only=True)
    sites_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    reports = serializers.SerializerMethodField()
    
    class Meta:
        model = MaintenanceTraveaux
        fields = [
            'id', 'project', 'project_code', 'project_name', 'title', 'description',
            'quantity', 'quantity_completed', 'status', 'status_display', 'estimated_time',
            'sites_count', 'scheduled_dates', 'progress_percentage', 'is_completed', 'reports',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()
    
    def get_reports(self, obj):
        serializer = MaintenanceTraveauxReportSerializer(obj.reports.all(), many=True, context=self.context)
        return serializer.data


class DeviceTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for DeviceToken model
    """
    technician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'technician', 'technician_name', 'token', 'device_type', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'technician', 'created_at', 'updated_at']
    
    def get_technician_name(self, obj):
        return f"{obj.technician.first_name} {obj.technician.last_name}"