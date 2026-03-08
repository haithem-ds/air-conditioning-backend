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
        return f"{obj.first_name} {obj.last_name}".strip()


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users
    """
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'role', 'phone_number', 'is_active'
        ]
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for Client model
    """
    sites_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'code_client', 'email', 'phone_number', 
            'address', 'city', 'postal_code', 'country', 'is_active',
            'sites_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sites_count(self, obj):
        return obj.sites.count()


class SiteSerializer(serializers.ModelSerializer):
    """
    Serializer for Site model
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = Site
        fields = [
            'id', 'title', 'client', 'client_name', 'address', 
            'city', 'postal_code', 'country', 'is_active', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TechnicianSerializer(serializers.ModelSerializer):
    """
    Serializer for Technician model
    """
    team_groups = serializers.SerializerMethodField()
    
    class Meta:
        model = Technician
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number',
            'identification_number', 'specialization', 'experience_years',
            'is_active', 'team_groups', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_team_groups(self, obj):
        return [group.id for group in obj.team_groups.all()]


class TeamGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for TeamGroup model
    """
    technicians_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamGroup
        fields = [
            'id', 'name', 'description', 'technicians_count', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.technicians.count()


class TeamGroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for TeamGroup list views
    """
    technicians_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamGroup
        fields = [
            'id', 'name', 'description', 'technicians_count', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.technicians.count()


class EquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Equipment model
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Equipment
        fields = [
            'id', 'code', 'full_name', 'equipment_name', 'brand', 
            'model', 'specifications', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.brand} {obj.equipment_name}"


class ClientEquipmentSerializer(serializers.ModelSerializer):
    """
    Serializer for ClientEquipment model
    """
    equipment_name = serializers.CharField(source='equipment.equipment_name', read_only=True)
    equipment_brand = serializers.CharField(source='equipment.brand', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    site_title = serializers.CharField(source='site.title', read_only=True)
    
    class Meta:
        model = ClientEquipment
        fields = [
            'id', 'equipment', 'equipment_name', 'equipment_brand', 
            'client', 'client_name', 'site', 'site_title', 'serial_number',
            'year_of_facturation', 'warranty_expiry', 'installation_date',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TechnicianGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for TechnicianGroup model
    """
    technicians_count = serializers.SerializerMethodField()
    chef_technician_name = serializers.CharField(source='chef_technician.get_full_name', read_only=True)
    is_at_capacity = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    
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
        return obj.technicians.count()
    
    def get_is_at_capacity(self, obj):
        return obj.technicians.count() >= obj.max_capacity
    
    def get_available_slots(self, obj):
        return max(0, obj.max_capacity - obj.technicians.count())


class TechnicianGroupListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for TechnicianGroup list views
    """
    technicians_count = serializers.SerializerMethodField()
    chef_technician_name = serializers.CharField(source='chef_technician.get_full_name', read_only=True)
    is_at_capacity = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    
    class Meta:
        model = TechnicianGroup
        fields = [
            'id', 'name', 'specialty', 'specialty_display', 'description',
            'chef_technician_name', 'technicians_count', 'status', 'status_display',
            'max_capacity', 'is_at_capacity', 'available_slots', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_technicians_count(self, obj):
        return obj.technicians.count()
    
    def get_is_at_capacity(self, obj):
        return obj.technicians.count() >= obj.max_capacity
    
    def get_available_slots(self, obj):
        return max(0, obj.max_capacity - obj.technicians.count())


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
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()
    
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
    
    def get_sites_data(self, obj):
        """Get detailed sites data"""
        sites = obj.sites.all()
        return [{'id': site.id, 'title': site.title, 'address': site.address} for site in sites]
    
    def get_sites_count(self, obj):
        """Get number of sites"""
        return obj.sites.count()
    
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
