from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Client, Site, Technician, TeamGroup, Equipment, ClientEquipment, TechnicianGroup, Contract

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'role', 'phone_number', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'role', 'phone_number', 'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client model
    """
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=True)
    token = serializers.CharField(read_only=True)
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'code_client', 'telephone1', 'telephone2',
            'website', 'logo', 'social_media_link', 'status_juridique',
            'date_creation', 'sites_count', 'equipment_count',
            'email', 'password', 'token', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_creation', 'token', 'created_at', 'updated_at']
    
    def get_sites_count(self, obj):
        return obj.sites.count()
    
    def get_equipment_count(self, obj):
        return obj.client_equipment.count()
    
    def create(self, validated_data):
        # Extract email and password
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        
        # Generate unique code_client if not provided
        if not validated_data.get('code_client'):
            import uuid
            validated_data['code_client'] = f"CLIENT_{str(uuid.uuid4())[:8].upper()}"
        
        # Handle empty telephone1 - use default if empty
        if not validated_data.get('telephone1'):
            validated_data['telephone1'] = '0000000000'
        
        # Create client directly (no User account needed)
        client = Client.objects.create(
            email=email,
            password=password,  # Store plain password for now, will be hashed in save()
            **validated_data
        )
        
        # Hash the password
        client.set_password(password)
        client.save()
        
        return client
    
    def update(self, instance, validated_data):
        # Handle password update if provided
        password = validated_data.pop('password', None)
        email = validated_data.pop('email', None)
        
        # Update client fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update email and password if provided
        if email:
            instance.email = email
        
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
            'id', 'client', 'client_name', 'title', 'city', 'wilaya', 'country',
            'postal_code', 'region', 'sector', 'address', 'longitude', 'latitude',
            'nif', 'nis', 'rc', 'number_of_workers', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TechnicianSerializer(serializers.ModelSerializer):
    """
    Serializer for Technician model
    """
    full_name = serializers.SerializerMethodField()
    team_groups_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Technician
        fields = [
            'id', 'first_name', 'last_name', 'identification_number', 'picture',
            'date_of_enrollment', 'speciality', 'status', 'status_display',
            'phone_number', 'email', 'full_name', 'team_groups_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_team_groups_count(self, obj):
        try:
            return obj.team_groups.count()
        except:
            return 0




class TeamGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for TeamGroup model
    """
    technicians_data = TechnicianSerializer(source='technicians', many=True, read_only=True)
    technicians_count = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamGroup
        fields = [
            'id', 'name', 'description', 'technicians', 'technicians_data',
            'technicians_count', 'team_lead', 'team_lead_name', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.technicians.count()
    
    def get_team_lead_name(self, obj):
        if obj.team_lead:
            return f"{obj.team_lead.first_name} {obj.team_lead.last_name}"
        return None


class TeamGroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for TeamGroup list views
    """
    technicians_count = serializers.SerializerMethodField()
    team_lead_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamGroup
        fields = [
            'id', 'name', 'description', 'technicians_count',
            'team_lead_name', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.technicians.count()
    
    def get_team_lead_name(self, obj):
        if obj.team_lead:
            return f"{obj.team_lead.first_name} {obj.team_lead.last_name}"
        return None


class EquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Equipment catalog model
    """
    client_instances_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Equipment
        fields = [
            'id', 'full_name', 'code', 'brand', 'model_number',
            'image', 'image_url', 'description', 'specifications',
            'is_active', 'client_instances_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_client_instances_count(self, obj):
        return obj.client_instances.count()
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ClientEquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for ClientEquipment model - Equipment instances owned by clients
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    equipment_name = serializers.CharField(source='equipment.full_name', read_only=True)
    equipment_brand = serializers.CharField(source='equipment.brand', read_only=True)
    site_title = serializers.CharField(source='site.title', read_only=True)
    
    class Meta:
        model = ClientEquipment
        fields = [
            'id', 'client', 'client_name', 'equipment', 'equipment_name', 'equipment_brand',
            'serial_number', 'year_of_facturation', 'warranty_expiry', 'site', 'site_title',
            'installation_date', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TechnicianGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for TechnicianGroup model
    """
    chef_technician_name = serializers.SerializerMethodField()
    technicians_count = serializers.SerializerMethodField()
    technicians_data = TechnicianSerializer(source='technicians', many=True, read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_at_capacity = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicianGroup
        fields = [
            'id', 'name', 'specialty', 'specialty_display', 'description', 
            'chef_technician', 'chef_technician_name', 'technicians', 'technicians_data',
            'technicians_count', 'status', 'status_display', 'max_capacity',
            'current_assignment', 'equipment_specialization', 'is_at_capacity',
            'available_slots', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_chef_technician_name(self, obj):
        if obj.chef_technician:
            return f"{obj.chef_technician.first_name} {obj.chef_technician.last_name}"
        return None
    
    def get_technicians_count(self, obj):
        return obj.get_technicians_count()
    
    def get_is_at_capacity(self, obj):
        return obj.is_at_capacity()
    
    def get_available_slots(self, obj):
        return obj.get_available_slots()


class TechnicianGroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for TechnicianGroup list views
    """
    chef_technician_name = serializers.SerializerMethodField()
    technicians_count = serializers.SerializerMethodField()
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TechnicianGroup
        fields = [
            'id', 'name', 'specialty', 'specialty_display', 'chef_technician_name',
            'technicians_count', 'status', 'status_display', 'max_capacity',
            'current_assignment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_chef_technician_name(self, obj):
        if obj.chef_technician:
            return f"{obj.chef_technician.first_name} {obj.chef_technician.last_name}"
        return None
    
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
            'days_until_expiry', 'pdf_document', 'pdf_document_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'creation_date', 'created_at', 'updated_at']
    
    def get_equipment_count(self, obj):
        return obj.get_equipment_count()
    
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
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()


class ContractListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for Contract list views
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    sites_data = serializers.SerializerMethodField()
    sites_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()
    contract_type_display = serializers.CharField(source='get_contract_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    pdf_document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = [
            'id', 'code', 'client', 'client_name', 'sites', 'sites_data', 'sites_count', 'contract_type',
            'contract_type_display', 'status', 'status_display', 'equipment_count', 'prix_ht', 'prix_ttc',
            'starting_date', 'ending_date', 'is_active', 'is_expired',
            'days_until_expiry', 'pdf_document_url', 'creation_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'code', 'creation_date', 'created_at', 'updated_at']
    
    def get_equipment_count(self, obj):
        return obj.get_equipment_count()
    
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
    

