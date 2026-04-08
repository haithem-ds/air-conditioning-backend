from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models

from .document_uploads import DOCUMENT_UPLOAD_EXTENSIONS


class User(AbstractUser):
    """
    Custom User model with role-based access control
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('CLIENT', 'Client'),
        ('TECHNICIAN', 'Technician'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CLIENT',
        help_text="User role in the system"
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="User's phone number"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


class Client(models.Model):
    """
    Client model representing companies that use the air conditioning service
    """
    STATUS_JURIDIQUE_CHOICES = [
        ('SNC', 'SNC (Société en Nom Collectif)'),
        ('SARL', 'SARL (Société à Responsabilité Limitée)'),
        ('EURL', 'EURL (Entreprise Unipersonnelle à Responsabilité Limitée)'),
        ('SA', 'SA (Société Anonyme)'),
        ('SPA', 'SPA (Société par Actions)'),
    ]
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the company"
    )
    code_client = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique client code"
    )
    telephone1 = models.CharField(
        max_length=20,
        default='0000000000',
        help_text="Primary phone number"
    )
    telephone2 = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Secondary phone number"
    )
    website = models.URLField(
        blank=True,
        null=True,
        help_text="Client's website"
    )
    logo = models.ImageField(
        upload_to='client_logos/',
        blank=True,
        null=True,
        help_text="Logo of the company"
    )
    social_media_link = models.URLField(
        blank=True,
        null=True,
        help_text="Link to client's social media page(s)"
    )
    nif = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Fiscal identification number (optional)"
    )
    nis = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Statistical identification number (optional)"
    )
    rc = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Commercial register number (optional)"
    )
    status_juridique = models.CharField(
        max_length=10,
        choices=STATUS_JURIDIQUE_CHOICES,
        default='SNC',
        help_text="Type of company"
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        help_text="Date when the client account was created"
    )
    email = models.EmailField(
        unique=True,
        blank=True,
        null=True,
        help_text="Client's email address for login"
    )
    password = models.CharField(
        max_length=255,
        default='password123',
        help_text="Client's password for login"
    )
    token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Authentication token for client login"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client_profile',
        blank=True,
        null=True,
        help_text="User account for login access"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Generate unique code_client if not provided
        if not self.code_client:
            import uuid
            self.code_client = f"CLIENT_{str(uuid.uuid4())[:8].upper()}"
        
        # Generate token if not provided
        if not self.token:
            import uuid
            self.token = f"TOKEN_{str(uuid.uuid4()).replace('-', '').upper()}"
        
        super().save(*args, **kwargs)
    
    def set_password(self, raw_password):
        """
        Set the password for the client (hash it)
        """
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """
        Check if the provided password matches the client's password
        """
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['name']


class Site(models.Model):
    """
    Site model representing physical locations where air conditioning services are provided
    """
    WORKERS_CHOICES = [
        ('<10', 'Less than 10 workers'),
        ('20-50', '20 to 50 workers'),
        ('>50', 'More than 50 workers'),
    ]
    
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='sites'
    )
    title = models.CharField(
        max_length=255,
        default='Site Title',
        help_text="Name/title of the site"
    )
    city = models.CharField(
        max_length=100,
        default='Algiers',
        help_text="City"
    )
    wilaya = models.CharField(
        max_length=100,
        default='Algiers',
        help_text="Region/province"
    )
    country = models.CharField(
        max_length=100,
        default='Algeria',
        help_text="Country"
    )
    postal_code = models.CharField(
        max_length=20,
        default='16000',
        help_text="Postal code"
    )
    region = models.CharField(
        max_length=100,
        default='North',
        help_text="Region"
    )
    sector = models.CharField(
        max_length=100,
        default='Commercial',
        help_text="Sector"
    )
    address = models.TextField(
        default='Address not specified',
        help_text="Physical address of the site"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text="Longitude coordinate"
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text="Latitude coordinate"
    )
    number_of_workers = models.CharField(
        max_length=10,
        choices=WORKERS_CHOICES,
        default='<10',
        help_text="Number of workers at this site"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.client.name}"
    
    class Meta:
        verbose_name = "Site"
        verbose_name_plural = "Sites"
        ordering = ['title']


class Technician(models.Model):
    """
    Technician model representing service technicians
    """
    STATUS_CHOICES = [
        ('FREE', 'Free'),
        ('BUSY', 'Busy'),
        ('ON_BREAK', 'On Break'),
        ('NOT_WORKING', 'Not Working'),
    ]
    
    first_name = models.CharField(
        max_length=150,
        help_text="Technician's first name"
    )
    last_name = models.CharField(
        max_length=150,
        help_text="Technician's last name"
    )
    identification_number = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text="National or company ID"
    )
    picture = models.ImageField(
        upload_to='technician_photos/',
        blank=True,
        null=True,
        help_text="Technician's profile photo"
    )
    date_of_enrollment = models.DateField(
        default='2024-01-01',
        help_text="Date they joined the company"
    )
    speciality = models.CharField(
        max_length=255,
        default='General Maintenance',
        help_text="Area of expertise (e.g., installation, maintenance, electrical, refrigeration)"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='FREE',
        help_text="Current status of the technician"
    )
    phone_number = models.CharField(
        max_length=20,
        default='0000000000',
        help_text="Technician's phone number"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Technician's email address"
    )
    password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='123',
        help_text="Technician's password for login (default: 123)"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='technician_profile',
        blank=True,
        null=True,
        help_text="User account for login access"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.identification_number})"
    
    def set_password(self, raw_password):
        """Set the password for the technician (hash it)"""
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check if the provided password matches the technician's password"""
        from django.contrib.auth.hashers import check_password
        if not self.password:
            return False
        return check_password(raw_password, self.password)
    
    def save(self, *args, **kwargs):
        # Generate unique identification_number if not provided
        if not self.identification_number:
            import uuid
            # Generate a unique ID like TECH_A1B2C3D4
            self.identification_number = f"TECH_{str(uuid.uuid4())[:8].upper()}"
        
        # Set default password if not set
        if not self.password:
            self.set_password('123')
        elif not self.password.startswith('pbkdf2_'):  # If password is not hashed
            self.set_password(self.password)
        
        # Save first to get ID
        super().save(*args, **kwargs)
        
        # Create or update User account for this technician
        if not self.user:
            # Generate username for user account
            if self.id:
                username = f"tech_{self.id}"
            elif self.email:
                username = f"tech_{self.email.split('@')[0]}"
            elif self.identification_number:
                username = f"tech_{self.identification_number}"
            else:
                import uuid
                username = f"tech_{str(uuid.uuid4())[:8].lower()}"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': self.email or f"tech{self.id}@pika.local",
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'role': 'TECHNICIAN',
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            if created:
                user.set_password(self.password if self.password else '123')
                user.save()
            self.user = user
            super().save(*args, **kwargs)  # Save again to link user
        else:
            # Update existing user
            self.user.email = self.email or self.user.email
            self.user.first_name = self.first_name
            self.user.last_name = self.last_name
            self.user.role = 'TECHNICIAN'
            self.user.is_active = True
            # Only update password if it changed (not default)
            if self.password and self.password.startswith('pbkdf2_'):
                # Password is already hashed, update user if needed
                pass
            self.user.save()
    
    class Meta:
        verbose_name = "Technician"
        verbose_name_plural = "Technicians"
        ordering = ['first_name', 'last_name']


class TechnicianGroup(models.Model):
    """
    Technician Group model representing groups of technicians working together
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BUSY', 'Busy - Working on Assignment'),
        ('ON_BREAK', 'On Break'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Under Maintenance'),
    ]
    
    SPECIALTY_CHOICES = [
        ('INSTALLATION', 'Installation'),
        ('MAINTENANCE', 'Maintenance'),
        ('REPAIR', 'Repair'),
        ('ELECTRICAL', 'Electrical'),
        ('REFRIGERATION', 'Refrigeration'),
        ('HVAC', 'HVAC Systems'),
        ('GENERAL', 'General Service'),
        ('EMERGENCY', 'Emergency Response'),
    ]
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the technician group"
    )
    specialty = models.CharField(
        max_length=50,
        choices=SPECIALTY_CHOICES,
        default='GENERAL',
        help_text="Specialty focus of this group"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the group's purpose and responsibilities"
    )
    chef_technician = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_groups',
        help_text="Lead technician/chef of this group"
    )
    technicians = models.ManyToManyField(
        Technician,
        related_name='technician_groups',
        blank=True,
        help_text="Technicians belonging to this group"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        help_text="Current status of the group"
    )
    max_capacity = models.PositiveIntegerField(
        default=5,
        help_text="Maximum number of technicians allowed in this group"
    )
    current_assignment = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Current assignment or project the group is working on"
    )
    equipment_specialization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Types of equipment this group specializes in"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_specialty_display()})"
    
    def get_technicians_count(self):
        return self.technicians.count()
    
    def is_at_capacity(self):
        return self.technicians.count() >= self.max_capacity
    
    def get_available_slots(self):
        return max(0, self.max_capacity - self.technicians.count())
    
    class Meta:
        verbose_name = "Technician Group"
        verbose_name_plural = "Technician Groups"
        ordering = ['name']


class Equipment(models.Model):
    """
    Equipment catalog model - defines types of equipment that can be owned by clients
    """
    full_name = models.CharField(
        max_length=255,
        help_text="Full descriptive name (e.g., 'Split AC Samsung 18000 BTU')"
    )
    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique equipment type code"
    )
    brand = models.CharField(
        max_length=100,
        help_text="Manufacturer/brand (e.g., Samsung, LG, Daikin)"
    )
    model_number = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Manufacturer model code"
    )
    image = models.ImageField(
        upload_to='equipment_images/',
        blank=True,
        null=True,
        help_text="Equipment photo"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the equipment"
    )
    specifications = models.JSONField(
        blank=True,
        null=True,
        help_text="Technical specifications (JSON format)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this equipment type is available"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.brand} {self.full_name} ({self.code})"
    
    class Meta:
        verbose_name = "Equipment Type"
        verbose_name_plural = "Equipment Types"
        ordering = ['brand', 'full_name']


class ClientEquipment(models.Model):
    """
    Client-owned equipment instances - specific equipment owned by clients
    """
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='client_equipment',
        help_text="Client who owns this equipment instance"
    )
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='client_instances',
        help_text="Type of equipment"
    )
    serial_number = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique serial number (important for maintenance tracking)"
    )
    year_of_facturation = models.PositiveIntegerField(
        help_text="Year the equipment was purchased/invoiced"
    )
    warranty_expiry = models.DateField(
        help_text="Date when warranty ends"
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='equipment',
        help_text="Site where this equipment is installed"
    )
    installation_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when equipment was installed"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about this equipment instance"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this equipment instance is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.equipment.full_name} - {self.client.name} ({self.serial_number})"
    
    def save(self, *args, **kwargs):
        # Generate unique serial_number if not provided
        if not self.serial_number:
            import uuid
            self.serial_number = f"SN_{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Client Equipment"
        verbose_name_plural = "Client Equipment"
        ordering = ['client__name', 'equipment__brand', 'equipment__full_name']
        unique_together = ['client', 'serial_number']


class Contract(models.Model):
    """
    Contract model representing service contracts between the company and clients
    """
    CONTRACT_TYPE_CHOICES = [
        ('INSTALLATION', 'Installation'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('PROCESSED', 'Processed'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
        ('SCHEDULED', 'Scheduled'),
        ('FINISHED', 'Finished'),
    ]
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique contract code number"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contracts',
        help_text="Client this contract belongs to"
    )
    sites = models.ManyToManyField(
        Site,
        related_name='contracts',
        blank=True,
        help_text="Sites this contract covers"
    )
    description = models.TextField(
        help_text="Description of the contract"
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Date when the contract was created"
    )
    starting_date = models.DateField(
        help_text="Date when the contract starts"
    )
    ending_date = models.DateField(
        help_text="Date when the contract ends"
    )
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_TYPE_CHOICES,
        help_text="Type of contract (Installation or Maintenance)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='CREATED',
        help_text="Current status of the contract"
    )
    equipment = models.ManyToManyField(
        ClientEquipment,
        related_name='contracts',
        blank=True,
        help_text="Equipment covered by this contract"
    )
    prix_ht = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Prix HT (Price excluding tax)"
    )
    prix_ttc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix TTC (Price including tax)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the contract is active"
    )
    pdf_document = models.FileField(
        upload_to='contract_pdfs/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Contract attachment: PDF, CSV, Excel, or Word",
    )
    # Maintenance-specific fields
    contract_duration_years = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Duration of the contract in years (for maintenance contracts)"
    )
    maintenance_frequency_per_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of maintenance visits per year (for maintenance contracts)"
    )
    create_project_maintenance_automatically = models.BooleanField(
        default=False,
        help_text="Automatically create maintenance projects when contract is created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Contract {self.code} - {self.client.name}"
    
    def save(self, *args, **kwargs):
        # Generate unique contract code if not provided
        if not self.code:
            import uuid
            self.code = f"CONT_{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    
    def get_equipment_count(self):
        return self.equipment.count()
    
    def is_expired(self):
        from django.utils import timezone
        if self.ending_date is None:
            return False
        return timezone.now().date() > self.ending_date
    
    def days_until_expiry(self):
        from django.utils import timezone
        if self.ending_date is None:
            return None
        delta = self.ending_date - timezone.now().date()
        return delta.days
    
    class Meta:
        verbose_name = "Contract"
        verbose_name_plural = "Contracts"
        ordering = ['-creation_date']


class TeamGroup(models.Model):
    """
    Team Group model for organizing technicians into teams
    """
    name = models.CharField(
        max_length=255,
        help_text="Name of the team group"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the team group"
    )
    technicians = models.ManyToManyField(
        Technician,
        related_name='team_groups',
        blank=True,
        help_text="Technicians belonging to this team"
    )
    team_lead = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        related_name='led_teams',
        blank=True,
        null=True,
        help_text="Team lead technician"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the team group is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Team Group"
        verbose_name_plural = "Team Groups"


class ProjectInstallation(models.Model):
    """
    Project Installation model for managing installation projects
    """
    COMPLEXITY_CHOICES = [
        ('SIMPLE', 'Simple'),
        ('NORMAL', 'Normal'),
        ('COMPLEX', 'Complex'),
    ]
    
    project_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique project code"
    )
    project_name = models.CharField(
        max_length=255,
        help_text="Name of the installation project"
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installation_projects',
        help_text="Associated contract (optional)"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='installation_projects',
        help_text="Client for this project"
    )
    description = models.TextField(
        help_text="Detailed description of the project"
    )
    date_creation = models.DateField(
        auto_now_add=True,
        help_text="Date when project was created"
    )
    start_date = models.DateField(
        help_text="Project start date"
    )
    finish_date = models.DateField(
        help_text="Project finish date"
    )
    sites = models.ManyToManyField(
        Site,
        related_name='installation_projects',
        blank=True,
        help_text="Sites for this project"
    )
    equipment = models.ManyToManyField(
        ClientEquipment,
        related_name='installation_projects',
        blank=True,
        help_text="Equipment for this project"
    )
    technician_group = models.ForeignKey(
        TechnicianGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='installation_projects',
        help_text="Technician group responsible for this project"
    )
    complexity = models.CharField(
        max_length=10,
        choices=COMPLEXITY_CHOICES,
        default='NORMAL',
        help_text="Project complexity level"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the project is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.project_code} - {self.project_name}"
    
    def save(self, *args, **kwargs):
        if not self.project_code:
            import uuid
            self.project_code = f"PROJ_{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Project Installation"
        verbose_name_plural = "Project Installations"
        ordering = ['-created_at']


class ProjectInstallationPDF(models.Model):
    """
    Model for storing multiple PDFs for a project installation
    """
    project = models.ForeignKey(
        ProjectInstallation,
        on_delete=models.CASCADE,
        related_name='pdf_documents',
        help_text="Project this PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_installation_pdfs/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Project document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - {self.title}"
    
    class Meta:
        verbose_name = "Project Installation PDF"
        verbose_name_plural = "Project Installation PDFs"
        ordering = ['-uploaded_at']


class ProjectInstallationFacture(models.Model):
    """
    Model for storing Facture PDFs for a project installation
    """
    project = models.ForeignKey(
        ProjectInstallation,
        on_delete=models.CASCADE,
        related_name='facture_pdfs',
        help_text="Project this facture PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_installation_factures/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Facture document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this facture PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - Facture: {self.title}"
    
    class Meta:
        verbose_name = "Project Installation Facture"
        verbose_name_plural = "Project Installation Factures"
        ordering = ['-uploaded_at']


class ProjectInstallationPV(models.Model):
    """
    Model for storing PV (Procès-Verbal) PDFs for a project installation
    """
    project = models.ForeignKey(
        ProjectInstallation,
        on_delete=models.CASCADE,
        related_name='pv_pdfs',
        help_text="Project this PV PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_installation_pvs/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="PV document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this PV PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - PV: {self.title}"
    
    class Meta:
        verbose_name = "Project Installation PV"
        verbose_name_plural = "Project Installation PVs"
        ordering = ['-uploaded_at']


class ProjectInstallationQuote(models.Model):
    """
    Model for storing Quote PDFs for a project installation
    """
    project = models.ForeignKey(
        ProjectInstallation,
        on_delete=models.CASCADE,
        related_name='quote_pdfs',
        help_text="Project this quote PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_installation_quotes/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Quote document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this quote PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - Quote: {self.title}"
    
    class Meta:
        verbose_name = "Project Installation Quote"
        verbose_name_plural = "Project Installation Quotes"
        ordering = ['-uploaded_at']


class ProjectMaintenance(models.Model):
    """
    Project Maintenance model for managing maintenance projects
    """
    COMPLEXITY_CHOICES = [
        ('SIMPLE', 'Simple'),
        ('NORMAL', 'Normal'),
        ('COMPLEX', 'Complex'),
    ]
    
    project_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique project code"
    )
    project_name = models.CharField(
        max_length=255,
        help_text="Name of the maintenance project"
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_projects',
        help_text="Associated maintenance contract (optional)"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='maintenance_projects',
        help_text="Client for this project"
    )
    description = models.TextField(
        help_text="Detailed description of the project"
    )
    date_creation = models.DateField(
        auto_now_add=True,
        help_text="Date when project was created"
    )
    start_date = models.DateField(
        help_text="Project start date"
    )
    finish_date = models.DateField(
        help_text="Project finish date"
    )
    sites = models.ManyToManyField(
        Site,
        related_name='maintenance_projects',
        blank=True,
        help_text="Sites for this project"
    )
    equipment = models.ManyToManyField(
        ClientEquipment,
        related_name='maintenance_projects',
        blank=True,
        help_text="Equipment for this project"
    )
    technician_group = models.ForeignKey(
        TechnicianGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_projects',
        help_text="Technician group responsible for this project"
    )
    complexity = models.CharField(
        max_length=10,
        choices=COMPLEXITY_CHOICES,
        default='NORMAL',
        help_text="Project complexity level"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the project is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.project_code} - {self.project_name}"
    
    def save(self, *args, **kwargs):
        if not self.project_code:
            import uuid
            self.project_code = f"MAINT_{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Project Maintenance"
        verbose_name_plural = "Project Maintenances"
        ordering = ['-created_at']


class ProjectMaintenancePDF(models.Model):
    """
    Model for storing multiple PDFs for a project maintenance
    """
    project = models.ForeignKey(
        ProjectMaintenance,
        on_delete=models.CASCADE,
        related_name='pdf_documents',
        help_text="Project this PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_maintenance_pdfs/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Project document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - {self.title}"
    
    class Meta:
        verbose_name = "Project Maintenance PDF"
        verbose_name_plural = "Project Maintenance PDFs"
        ordering = ['-uploaded_at']


class ProjectMaintenanceFacture(models.Model):
    """
    Model for storing Facture PDFs for a project maintenance
    """
    project = models.ForeignKey(
        ProjectMaintenance,
        on_delete=models.CASCADE,
        related_name='facture_pdfs',
        help_text="Project this facture PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_maintenance_factures/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Facture document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this facture PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - Facture: {self.title}"
    
    class Meta:
        verbose_name = "Project Maintenance Facture"
        verbose_name_plural = "Project Maintenance Factures"
        ordering = ['-uploaded_at']


class ProjectMaintenancePV(models.Model):
    """
    Model for storing PV (Procès-Verbal) PDFs for a project maintenance
    """
    project = models.ForeignKey(
        ProjectMaintenance,
        on_delete=models.CASCADE,
        related_name='pv_pdfs',
        help_text="Project this PV PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_maintenance_pvs/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="PV document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this PV PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - PV: {self.title}"
    
    class Meta:
        verbose_name = "Project Maintenance PV"
        verbose_name_plural = "Project Maintenance PVs"
        ordering = ['-uploaded_at']


class ProjectMaintenanceQuote(models.Model):
    """
    Model for storing Quote PDFs for a project maintenance
    """
    project = models.ForeignKey(
        ProjectMaintenance,
        on_delete=models.CASCADE,
        related_name='quote_pdfs',
        help_text="Project this quote PDF belongs to"
    )
    pdf_file = models.FileField(
        upload_to='project_maintenance_quotes/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Quote document (PDF, CSV, Excel, or Word)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Title/description of this quote PDF"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.project.project_code} - Quote: {self.title}"
    
    class Meta:
        verbose_name = "Project Maintenance Quote"
        verbose_name_plural = "Project Maintenance Quotes"
        ordering = ['-uploaded_at']


class MaintenanceTraveaux(models.Model):
    """
    MaintenanceTraveaux model representing work tasks/actions for maintenance projects
    """
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('ONGOING', 'Ongoing'),
        ('FINISHED', 'Finished'),
    ]
    
    project = models.ForeignKey(
        ProjectMaintenance,
        on_delete=models.CASCADE,
        related_name='maintenance_traveaux',
        help_text="Project this traveaux belongs to"
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the traveaux"
    )
    description = models.TextField(
        help_text="Detailed description of the traveaux"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Total quantity to be completed"
    )
    quantity_completed = models.PositiveIntegerField(
        default=0,
        help_text="Quantity that has been completed"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='CREATED',
        help_text="Current status of the traveaux"
    )
    estimated_time = models.DurationField(
        help_text="Estimated time to complete this traveaux"
    )
    sites = models.ManyToManyField(
        Site,
        related_name='maintenance_traveaux',
        blank=True,
        help_text="Sites where this traveaux will be performed"
    )
    scheduled_dates = models.JSONField(
        blank=True,
        null=True,
        help_text="Scheduled dates for this traveaux (JSON array of dates)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.project.project_code}"
    
    @property
    def progress_percentage(self):
        """
        Calculate work progress percentage based on completed quantity
        """
        if self.quantity == 0:
            return 0
        return round((self.quantity_completed / self.quantity) * 100, 2)
    
    @property
    def is_completed(self):
        """
        Check if the traveaux is fully completed
        """
        return self.quantity_completed >= self.quantity
    
    def update_status(self):
        """
        Automatically update status based on progress
        """
        if self.quantity_completed >= self.quantity:
            self.status = 'FINISHED'
        elif self.quantity_completed > 0:
            self.status = 'ONGOING'
        else:
            self.status = 'CREATED'
        self.save()
    
    class Meta:
        verbose_name = "Maintenance Traveaux"
        verbose_name_plural = "Maintenance Traveaux"
        ordering = ['-created_at']


class MaintenanceTraveauxReport(models.Model):
    """
    Report attachments for maintenance traveaux (multiple PDFs per task)
    """
    traveaux = models.ForeignKey(
        MaintenanceTraveaux,
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="Maintenance traveaux this report belongs to"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional title for the report"
    )
    report_file = models.FileField(
        upload_to='maintenance_traveaux_reports/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Report attachment (PDF, CSV, Excel, or Word)",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.title:
            original_name = self.report_file.name.rsplit('/', 1)[-1]
            self.title = original_name.rsplit('.', 1)[0]
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} ({self.traveaux.title})"
    
    class Meta:
        verbose_name = "Maintenance Traveaux Report"
        verbose_name_plural = "Maintenance Traveaux Reports"
        ordering = ['-uploaded_at']


class DeviceToken(models.Model):
    """
    Model to store push notification device tokens for technicians
    """
    technician = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        help_text="Technician this device token belongs to"
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        help_text="Expo push notification token"
    )
    device_type = models.CharField(
        max_length=20,
        choices=[('IOS', 'iOS'), ('ANDROID', 'Android'), ('WEB', 'Web')],
        default='ANDROID',
        help_text="Type of device"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this token is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.technician.first_name} {self.technician.last_name} - {self.device_type}"
    
    class Meta:
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"
        ordering = ['-created_at']
        unique_together = ['technician', 'token']


class Traveaux(models.Model):
    """
    Traveaux model representing work tasks/actions for installation projects
    """
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('ONGOING', 'Ongoing'),
        ('FINISHED', 'Finished'),
    ]
    
    project = models.ForeignKey(
        ProjectInstallation,
        on_delete=models.CASCADE,
        related_name='traveaux',
        help_text="Project this traveaux belongs to"
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the traveaux"
    )
    description = models.TextField(
        help_text="Detailed description of the traveaux"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Total quantity to be completed"
    )
    quantity_completed = models.PositiveIntegerField(
        default=0,
        help_text="Quantity that has been completed"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='CREATED',
        help_text="Current status of the traveaux"
    )
    estimated_time = models.DurationField(
        help_text="Estimated time to complete this traveaux"
    )
    sites = models.ManyToManyField(
        Site,
        related_name='traveaux',
        blank=True,
        help_text="Sites where this traveaux will be performed"
    )
    scheduled_dates = models.JSONField(
        blank=True,
        null=True,
        help_text="Scheduled dates for this traveaux (JSON array of dates)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.project.project_code}"
    
    @property
    def progress_percentage(self):
        """
        Calculate work progress percentage based on completed quantity
        """
        if self.quantity == 0:
            return 0
        return round((self.quantity_completed / self.quantity) * 100, 2)
    
    @property
    def is_completed(self):
        """
        Check if the traveaux is fully completed
        """
        return self.quantity_completed >= self.quantity
    
    def update_status(self):
        """
        Automatically update status based on progress
        """
        if self.quantity_completed >= self.quantity:
            self.status = 'FINISHED'
        elif self.quantity_completed > 0:
            self.status = 'ONGOING'
        else:
            self.status = 'CREATED'
        self.save()
    
    class Meta:
        verbose_name = "Traveaux"
        verbose_name_plural = "Traveaux"
        ordering = ['-created_at']


class TraveauxReport(models.Model):
    """
    Report attachments for individual traveaux (multiple PDFs per task)
    """
    traveaux = models.ForeignKey(
        Traveaux,
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="Traveaux this report belongs to"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional title for the report"
    )
    report_file = models.FileField(
        upload_to='traveaux_reports/',
        validators=[FileExtensionValidator(list(DOCUMENT_UPLOAD_EXTENSIONS))],
        help_text="Report attachment (PDF, CSV, Excel, or Word)",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.title:
            original_name = self.report_file.name.rsplit('/', 1)[-1]
            self.title = original_name.rsplit('.', 1)[0]
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} ({self.traveaux.title})"
    
    class Meta:
        verbose_name = "Traveaux Report"
        verbose_name_plural = "Traveaux Reports"
        ordering = ['-uploaded_at']

