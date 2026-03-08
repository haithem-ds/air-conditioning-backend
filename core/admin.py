from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import (
    Client, Site, Technician, TeamGroup, Equipment, ClientEquipment, 
    TechnicianGroup, Contract, ProjectInstallation, ProjectInstallationPDF, 
    TraveauxReport, MaintenanceTraveauxReport, DeviceToken
)
from .forms import ClientChangeForm, ClientPasswordChangeForm

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User Admin with role field
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number')}),
    )


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Client Admin
    """
    form = ClientChangeForm
    list_display = ('name', 'code_client', 'email', 'telephone1', 'status_juridique', 'date_creation', 'created_at')
    list_filter = ('status_juridique', 'date_creation', 'created_at')
    search_fields = ('name', 'code_client', 'email', 'telephone1', 'telephone2')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code_client', 'status_juridique')
        }),
        ('Login Credentials', {
            'fields': ('email', 'password', 'token'),
            'description': 'Email and password for client login. Token is auto-generated.'
        }),
        ('Contact Information', {
            'fields': ('telephone1', 'telephone2', 'website')
        }),
        ('Company Details', {
            'fields': ('logo', 'social_media_link')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed system fields'
        }),
    )
    
    readonly_fields = ('token', 'created_at', 'updated_at')


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """
    Site Admin
    """
    list_display = ('title', 'client', 'city', 'wilaya', 'number_of_workers', 'created_at')
    list_filter = ('number_of_workers', 'wilaya', 'client', 'created_at')
    search_fields = ('title', 'address', 'city', 'wilaya', 'client__name')
    ordering = ('title',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('client', 'title', 'address')
        }),
        ('Location', {
            'fields': ('city', 'wilaya', 'country', 'postal_code', 'region', 'sector')
        }),
        ('Coordinates', {
            'fields': ('longitude', 'latitude'),
            'classes': ('collapse',)
        }),
        ('Legal Information', {
            'fields': ('nif', 'nis', 'rc')
        }),
        ('Workforce', {
            'fields': ('number_of_workers',)
        }),
    )


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    """
    Technician Admin
    """
    list_display = ('first_name', 'last_name', 'identification_number', 'email', 'speciality', 'status', 'date_of_enrollment', 'created_at')
    list_filter = ('status', 'speciality', 'date_of_enrollment', 'created_at')
    search_fields = ('first_name', 'last_name', 'identification_number', 'speciality', 'phone_number', 'email')
    ordering = ('first_name', 'last_name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'identification_number', 'picture')
        }),
        ('Login Credentials', {
            'fields': ('email', 'password'),
            'description': 'Email and password for technician login. Default password is "123". Leave password empty to keep current password.'
        }),
        ('Contact Information', {
            'fields': ('phone_number',)
        }),
        ('Professional Information', {
            'fields': ('speciality', 'date_of_enrollment', 'status')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Handle password update
        if 'password' in form.changed_data:
            password = form.cleaned_data.get('password')
            if password:
                obj.set_password(password)
            # If password is empty and it was changed, don't update it (keep existing)
        super().save_model(request, obj, form, change)


@admin.register(TeamGroup)
class TeamGroupAdmin(admin.ModelAdmin):
    """
    Team Group Admin
    """
    list_display = ('name', 'team_lead', 'technicians_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'team_lead__first_name', 'team_lead__last_name')
    ordering = ('name',)
    filter_horizontal = ('technicians',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Team Members', {
            'fields': ('technicians', 'team_lead')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def technicians_count(self, obj):
        return obj.technicians.count()
    technicians_count.short_description = 'Technicians Count'


@admin.register(TechnicianGroup)
class TechnicianGroupAdmin(admin.ModelAdmin):
    """
    Technician Group Admin
    """
    list_display = ('name', 'specialty', 'chef_technician', 'technicians_count', 'status', 'max_capacity', 'created_at')
    list_filter = ('specialty', 'status', 'created_at')
    search_fields = ('name', 'description', 'chef_technician__first_name', 'chef_technician__last_name', 'current_assignment')
    ordering = ('name',)
    filter_horizontal = ('technicians',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'specialty', 'description')
        }),
        ('Leadership', {
            'fields': ('chef_technician',)
        }),
        ('Group Members', {
            'fields': ('technicians', 'max_capacity')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'current_assignment', 'equipment_specialization')
        }),
    )
    
    def technicians_count(self, obj):
        return obj.get_technicians_count()
    technicians_count.short_description = 'Technicians Count'


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """
    Equipment Types Admin - Catalog of equipment types
    """
    list_display = ('full_name', 'code', 'brand', 'model_number', 'is_active', 'created_at')
    list_filter = ('brand', 'is_active', 'created_at')
    search_fields = ('full_name', 'code', 'brand', 'model_number', 'description')
    ordering = ('brand', 'full_name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'code', 'brand', 'model_number', 'image')
        }),
        ('Description & Specifications', {
            'fields': ('description', 'specifications')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ClientEquipment)
class ClientEquipmentAdmin(admin.ModelAdmin):
    """
    Client Equipment Admin - Equipment instances owned by clients
    """
    list_display = ('equipment', 'client', 'serial_number', 'site', 'year_of_facturation', 'warranty_expiry', 'is_active', 'created_at')
    list_filter = ('equipment__brand', 'year_of_facturation', 'client', 'is_active', 'created_at')
    search_fields = ('equipment__full_name', 'equipment__brand', 'serial_number', 'client__name', 'site__title')
    ordering = ('client__name', 'equipment__brand', 'equipment__full_name')
    
    fieldsets = (
        ('Equipment Information', {
            'fields': ('client', 'equipment', 'serial_number')
        }),
        ('Purchase & Installation', {
            'fields': ('year_of_facturation', 'warranty_expiry', 'site', 'installation_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'is_active')
        }),
    )


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """
    Contract Admin - Service contracts between company and clients
    """
    list_display = ('code', 'client', 'sites_count', 'contract_type', 'prix_ht', 'prix_ttc', 'starting_date', 'ending_date', 'equipment_count', 'is_active', 'creation_date')
    list_filter = ('contract_type', 'is_active', 'creation_date', 'starting_date', 'ending_date', 'client')
    search_fields = ('code', 'client__name', 'sites__title', 'description')
    ordering = ('-creation_date',)
    filter_horizontal = ('sites', 'equipment')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'client', 'description')
        }),
        ('Sites', {
            'fields': ('sites',),
            'description': 'Select sites covered by this contract'
        }),
        ('Contract Details', {
            'fields': ('contract_type', 'starting_date', 'ending_date', 'prix_ht', 'prix_ttc')
        }),
        ('Equipment', {
            'fields': ('equipment',),
            'description': 'Select equipment covered by this contract'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('creation_date', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed system fields'
        }),
    )
    
    readonly_fields = ('creation_date', 'created_at', 'updated_at')
    
    def sites_count(self, obj):
        return obj.sites.count()
    sites_count.short_description = 'Sites Count'
    
    def equipment_count(self, obj):
        return obj.get_equipment_count()
    equipment_count.short_description = 'Equipment Count'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client').prefetch_related('sites', 'equipment')


@admin.register(ProjectInstallationPDF)
class ProjectInstallationPDFAdmin(admin.ModelAdmin):
    """
    ProjectInstallationPDF Admin - PDF documents for projects
    """
    list_display = ('project', 'title', 'uploaded_at')
    list_filter = ('uploaded_at', 'project__project_code')
    search_fields = ('project__project_code', 'project__project_name', 'title')
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at',)

    fieldsets = (
        ('PDF Information', {
            'fields': ('project', 'title', 'pdf_file')
        }),
        ('System Information', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',),
            'description': 'Automatically managed system fields'
        }),
    )


class ProjectInstallationPDFInline(admin.TabularInline):
    """
    Inline admin for PDF documents in ProjectInstallation
    """
    model = ProjectInstallationPDF
    extra = 1
    fields = ('title', 'pdf_file')
    readonly_fields = ('uploaded_at',)


@admin.register(ProjectInstallation)
class ProjectInstallationAdmin(admin.ModelAdmin):
    """
    ProjectInstallation Admin - Installation projects
    """
    list_display = ('project_code', 'project_name', 'client', 'contract', 'technician_group', 'complexity', 'start_date', 'finish_date', 'sites_count', 'equipment_count', 'is_active', 'date_creation')
    list_filter = ('complexity', 'is_active', 'date_creation', 'start_date', 'finish_date', 'client', 'contract', 'technician_group')
    search_fields = ('project_code', 'project_name', 'client__name', 'contract__code', 'description')
    ordering = ('-date_creation',)
    filter_horizontal = ('sites', 'equipment')

    fieldsets = (
        ('Basic Information', {
            'fields': ('project_code', 'project_name', 'client', 'contract', 'description')
        }),
        ('Project Details', {
            'fields': ('start_date', 'finish_date', 'complexity', 'technician_group')
        }),
        ('Sites', {
            'fields': ('sites',),
            'description': 'Select sites for this project'
        }),
        ('Equipment', {
            'fields': ('equipment',),
            'description': 'Select equipment for this project'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('date_creation', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed system fields'
        }),
    )

    readonly_fields = ('project_code', 'date_creation', 'created_at', 'updated_at')
    inlines = [ProjectInstallationPDFInline]

    def sites_count(self, obj):
        return obj.sites.count()
    sites_count.short_description = 'Sites Count'

    def equipment_count(self, obj):
        return obj.equipment.count()
    equipment_count.short_description = 'Equipment Count'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client', 'contract').prefetch_related('sites', 'equipment', 'pdf_documents')


@admin.register(TraveauxReport)
class TraveauxReportAdmin(admin.ModelAdmin):
    """
    Admin interface for uploaded traveaux reports
    """
    list_display = ('title', 'traveaux', 'uploaded_at')
    list_filter = ('uploaded_at', 'traveaux__project__project_code')
    search_fields = ('title', 'traveaux__title', 'traveaux__project__project_code')
    readonly_fields = ('uploaded_at',)


@admin.register(MaintenanceTraveauxReport)
class MaintenanceTraveauxReportAdmin(admin.ModelAdmin):
    """
    Admin interface for maintenance traveaux reports
    """
    list_display = ('title', 'traveaux', 'uploaded_at')
    list_filter = ('uploaded_at', 'traveaux__project__project_code')
    search_fields = ('title', 'traveaux__title', 'traveaux__project__project_code')
    readonly_fields = ('uploaded_at',)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for device tokens (push notifications)
    """
    list_display = ('technician', 'device_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('technician__first_name', 'technician__last_name', 'technician__identification_number', 'token')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Device Information', {
            'fields': ('technician', 'token', 'device_type')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
