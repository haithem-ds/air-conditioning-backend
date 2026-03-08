from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserViewSet, ClientViewSet, SiteViewSet, TechnicianViewSet,
    TeamGroupViewSet, EquipmentViewSet, ClientEquipmentViewSet, 
    TechnicianGroupViewSet, ContractViewSet, ProjectInstallationViewSet, TraveauxViewSet, 
    ProjectMaintenanceViewSet, MaintenanceTraveauxViewSet, CustomTokenObtainPairView,
    DeviceTokenViewSet
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'sites', SiteViewSet, basename='site')
router.register(r'technicians', TechnicianViewSet, basename='technician')
router.register(r'team-groups', TeamGroupViewSet, basename='teamgroup')
router.register(r'technician-groups', TechnicianGroupViewSet, basename='techniciangroup')
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'client-equipment', ClientEquipmentViewSet, basename='clientequipment')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'project-installations', ProjectInstallationViewSet, basename='projectinstallation')
router.register(r'traveaux', TraveauxViewSet, basename='traveaux')
router.register(r'project-maintenances', ProjectMaintenanceViewSet, basename='projectmaintenance')
router.register(r'maintenance-traveaux', MaintenanceTraveauxViewSet, basename='maintenancetraveaux')
router.register(r'device-tokens', DeviceTokenViewSet, basename='devicetoken')

urlpatterns = [
    # JWT Authentication URLs
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints
    path('', include(router.urls)),
]