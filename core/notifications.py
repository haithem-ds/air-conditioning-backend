"""
Push notification service for sending notifications to technicians using Firebase Cloud Messaging (FCM)
"""
import logging
import os
from typing import List, Optional
from django.conf import settings
from .models import DeviceToken, Technician, TechnicianGroup, ProjectInstallation, ProjectMaintenance, Traveaux, MaintenanceTraveaux

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_app = None

def _initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        
        # Check if Firebase is already initialized
        try:
            _firebase_app = firebase_admin.get_app()
            logger.info("Firebase Admin SDK already initialized")
            return _firebase_app
        except ValueError:
            # Firebase not initialized yet
            pass
        
        # Get Firebase service account key path from settings
        # You can set FIREBASE_SERVICE_ACCOUNT_KEY in settings or environment variable
        service_account_key = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY', None)
        
        if not service_account_key:
            # Try environment variable
            service_account_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        
        if service_account_key and os.path.exists(service_account_key):
            # Initialize with service account key file
            cred = credentials.Certificate(service_account_key)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with service account key")
        else:
            # Try to use default credentials (for production with GOOGLE_APPLICATION_CREDENTIALS)
            try:
                _firebase_app = firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized with default credentials")
            except Exception as e:
                logger.warning(f"Firebase Admin SDK initialization failed: {str(e)}")
                logger.warning("To enable push notifications, set FIREBASE_SERVICE_ACCOUNT_KEY in settings.py")
                logger.warning("Or set GOOGLE_APPLICATION_CREDENTIALS environment variable")
                return None
        
        return _firebase_app
    except ImportError:
        logger.error("firebase-admin package not installed. Install it with: pip install firebase-admin")
        return None
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
        return None

# Initialize Firebase on module import
_initialize_firebase()


def send_push_notification(
    tokens: List[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
    sound: str = "default",
    priority: str = "high"
) -> bool:
    """
    Send push notification to multiple FCM tokens using Firebase Cloud Messaging
    
    Args:
        tokens: List of FCM push notification tokens
        title: Notification title
        body: Notification body/message
        data: Optional data payload (should be dict with string keys and string values)
        sound: Notification sound (default: "default")
        priority: Notification priority - "high" or "normal" (default: "high")
    
    Returns:
        bool: True if notification was sent successfully to at least one device, False otherwise
    """
    if not tokens:
        logger.warning("No tokens provided for push notification")
        return False
    
    # Ensure Firebase is initialized
    if _firebase_app is None:
        logger.error("Firebase Admin SDK not initialized. Cannot send push notifications.")
        return False
    
    try:
        from firebase_admin import messaging
        
        # Convert data to string format (FCM requires string values)
        notification_data = {}
        if data:
            notification_data = {str(k): str(v) for k, v in data.items()}
        
        # Set Android notification priority (use string values)
        android_priority_str = "high" if priority == "high" else "normal"
        
        # Build the message
        messages = []
        for token in tokens:
            # Handle token format
            # Try both full token and extracted FCM token if it contains ':'
            fcm_token = token
            if ':' in token:
                # This might be Expo format, but we'll try the full token first
                # If that fails, we can try extracting the FCM part
                fcm_token = token  # Use full token first
                logger.debug(f"Using full token (contains ':'): {fcm_token[:50]}...")
            # Create Android notification config
            # Enable sound and vibration
            # Note: sound and vibration are controlled by the notification channel in the app
            # Setting them here ensures they work even if channel settings change
            android_notification = messaging.AndroidNotification(
                title=title,
                body=body,
                channel_id="default",  # Match the channel ID set in the app
                vibrate_timings_millis=[0, 250, 250, 250],  # Vibration pattern: wait 0ms, vibrate 250ms, pause 250ms, vibrate 250ms
                priority="high"  # High priority for sound and vibration
            )
            # Don't set sound here - let the notification channel handle it
            # The channel is configured with sound: 'default' in the app
            
            android_config = messaging.AndroidConfig(
                priority=android_priority_str,
                notification=android_notification
            )
            
            # Create the message
            # For Expo apps, we need to send data-only messages or use both notification and data
            message = messaging.Message(
                token=fcm_token,
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=notification_data if notification_data else {},
                android=android_config,
                apns=None,  # Not needed for Android
                webpush=None  # Not needed for Android
            )
            messages.append(message)
        
        # Send messages individually (FCM send method)
        success_count = 0
        total_sent = len(messages)
        
        for idx, message in enumerate(messages):
            try:
                response = messaging.send(message)
                success_count += 1
                logger.debug(f"Successfully sent notification {idx + 1}/{total_sent}: {response}")
            except Exception as e:
                logger.warning(f"Failed to send notification {idx + 1} to token: {str(e)}")
                # Continue with next message
        
        logger.info(f"Sent {success_count}/{total_sent} push notifications successfully")
        return success_count > 0
    
    except ImportError:
        logger.error("firebase-admin package not installed. Install it with: pip install firebase-admin")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending push notification: {str(e)}")
        return False


def get_technician_tokens(technician: Technician) -> List[str]:
    """
    Get all active push notification tokens for a technician
    
    Args:
        technician: Technician instance
    
    Returns:
        List of active push notification tokens
    """
    tokens = DeviceToken.objects.filter(
        technician=technician,
        is_active=True
    ).values_list('token', flat=True)
    return list(tokens)


def get_technician_group_tokens(technician_group: TechnicianGroup) -> List[str]:
    """
    Get all active push notification tokens for all technicians in a group
    
    Args:
        technician_group: TechnicianGroup instance
    
    Returns:
        List of active push notification tokens
    """
    technicians = technician_group.technicians.filter(device_tokens__is_active=True).distinct()
    tokens = DeviceToken.objects.filter(
        technician__in=technicians,
        is_active=True
    ).values_list('token', flat=True)
    return list(tokens)


def notify_technicians_new_project(
    project: ProjectInstallation | ProjectMaintenance,
    technician_group: TechnicianGroup
):
    """
    Send notification to all technicians in a group when they are assigned to a new project
    
    Args:
        project: ProjectInstallation or ProjectMaintenance instance
        technician_group: TechnicianGroup assigned to the project
    """
    tokens = get_technician_group_tokens(technician_group)
    
    if not tokens:
        logger.info(f"No active device tokens found for technician group {technician_group.id}")
        return
    
    project_type = "Installation" if isinstance(project, ProjectInstallation) else "Maintenance"
    
    title = f"New {project_type} Project Assigned"
    body = f"Your team has been assigned to project: {project.project_code} - {project.project_name}"
    
    data = {
        "type": "new_project",
        "project_id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "project_type": project_type.lower()
    }
    
    send_push_notification(tokens, title, body, data)


def notify_technicians_new_task(
    task: Traveaux | MaintenanceTraveaux,
    project: ProjectInstallation | ProjectMaintenance
):
    """
    Send notification to all technicians in a project's technician group when a new task is created
    
    Args:
        task: Traveaux or MaintenanceTraveaux instance
        project: ProjectInstallation or ProjectMaintenance instance
    """
    if not project.technician_group:
        logger.info(f"Project {project.id} has no technician group assigned")
        return
    
    tokens = get_technician_group_tokens(project.technician_group)
    
    if not tokens:
        logger.info(f"No active device tokens found for technician group {project.technician_group.id}")
        return
    
    project_type = "Installation" if isinstance(project, ProjectInstallation) else "Maintenance"
    task_type = "Traveaux" if isinstance(task, Traveaux) else "Maintenance Traveaux"
    
    title = f"New Task: {task.title}"
    body = f"A new {task_type.lower()} has been added to project {project.project_code}"
    
    data = {
        "type": "new_task",
        "task_id": task.id,
        "task_title": task.title,
        "project_id": project.id,
        "project_code": project.project_code,
        "project_name": project.project_name,
        "project_type": project_type.lower()
    }
    
    send_push_notification(tokens, title, body, data)

