"""
Test script to send a push notification directly
Run this to test if notifications are working
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'airconditioning_system.settings')
django.setup()

from core.models import Technician, DeviceToken
from core.notifications import send_push_notification, _firebase_app

def test_send_notification():
    """Test sending a notification"""
    print("=" * 60)
    print("Testing Push Notification")
    print("=" * 60)
    
    # Check Firebase initialization
    print(f"\n1. Checking Firebase initialization...")
    if _firebase_app is None:
        print("   [ERROR] Firebase Admin SDK not initialized!")
        return False
    else:
        print(f"   [OK] Firebase Admin SDK is initialized")
        print(f"   [OK] Project ID: {_firebase_app.project_id if hasattr(_firebase_app, 'project_id') else 'N/A'}")
    
    # Get technician ID 5 (hammia abdou)
    print(f"\n2. Getting technician and device token...")
    try:
        technician = Technician.objects.get(id=5)
        print(f"   [OK] Found technician: {technician.first_name} {technician.last_name}")
        
        device_token = DeviceToken.objects.filter(technician=technician, is_active=True).first()
        if device_token:
            print(f"   [OK] Found active device token: {device_token.token[:50]}...")
        else:
            print(f"   [ERROR] No active device token found for technician {technician.id}")
            return False
    except Technician.DoesNotExist:
        print(f"   [ERROR] Technician with ID 5 not found")
        return False
    
    # Send test notification
    print(f"\n3. Sending test notification...")
    try:
        result = send_push_notification(
            tokens=[device_token.token],
            title="Test Notification",
            body="This is a test push notification from the backend!",
            data={
                "type": "test",
                "message": "Testing push notifications"
            }
        )
        
        if result:
            print(f"   [OK] Notification sent successfully!")
            print(f"   [INFO] Check your device for the notification")
            return True
        else:
            print(f"   [ERROR] Failed to send notification")
            return False
    except Exception as e:
        print(f"   [ERROR] Exception while sending notification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_send_notification()
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Test notification sent!")
    else:
        print("[FAILED] Test notification failed!")
    print("=" * 60)
    sys.exit(0 if success else 1)

