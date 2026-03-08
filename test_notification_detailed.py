"""
Detailed test to check notification sending and token format
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'airconditioning_system.settings')
django.setup()

from core.models import DeviceToken
from firebase_admin import messaging

def test_token_format():
    """Check token format and try sending"""
    device_token = DeviceToken.objects.filter(id=1).first()
    if not device_token:
        print("No device token found")
        return
    
    token = device_token.token
    print(f"Token: {token}")
    print(f"Token length: {len(token)}")
    print(f"Token starts with: {token[:20]}")
    
    # Check if it looks like an FCM token
    # FCM tokens are typically long strings without special prefixes
    if ':' in token:
        parts = token.split(':')
        print(f"Token has {len(parts)} parts separated by ':'")
        print(f"First part: {parts[0]}")
        print(f"Second part (FCM part?): {parts[1][:50]}...")
        
        # Try with just the FCM part
        fcm_token = parts[1] if len(parts) > 1 else token
        print(f"\nTrying with FCM token part: {fcm_token[:50]}...")
        
        try:
            message = messaging.Message(
                token=fcm_token,
                notification=messaging.Notification(
                    title="Test with FCM Token",
                    body="Testing with extracted FCM token"
                ),
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        title="Test with FCM Token",
                        body="Testing with extracted FCM token"
                    )
                )
            )
            response = messaging.send(message)
            print(f"✅ Success! Message ID: {response}")
        except Exception as e:
            print(f"❌ Error with FCM token: {str(e)}")
    
    # Also try with full token
    print(f"\nTrying with full token...")
    try:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title="Test with Full Token",
                body="Testing with full token as-is"
            ),
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title="Test with Full Token",
                    body="Testing with full token as-is"
                )
            )
        )
        response = messaging.send(message)
        print(f"✅ Success with full token! Message ID: {response}")
    except Exception as e:
        print(f"❌ Error with full token: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    test_token_format()

