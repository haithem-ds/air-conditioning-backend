"""
Simple script to test Firebase configuration
Run this script to verify Firebase Admin SDK is properly configured

Usage:
    python manage.py shell < test_firebase_config.py
    OR
    python test_firebase_config.py (if run from backend directory)
"""

import os
import sys
import django

# Setup Django environment
if __name__ == "__main__":
    # Add the backend directory to the path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'airconditioning_system.settings')
    django.setup()

from django.conf import settings
from core.notifications import _firebase_app, _initialize_firebase

def test_firebase_config():
    """Test Firebase configuration"""
    print("=" * 60)
    print("Testing Firebase Configuration")
    print("=" * 60)
    
    # Check if service account key file exists
    service_account_key = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY', None)
    print(f"\n1. Checking service account key path...")
    if service_account_key:
        print(f"   [OK] FIREBASE_SERVICE_ACCOUNT_KEY is set: {service_account_key}")
        if os.path.exists(service_account_key):
            print(f"   [OK] Service account key file exists")
        else:
            print(f"   [ERROR] Service account key file NOT found at: {service_account_key}")
            return False
    else:
        print(f"   [WARNING] FIREBASE_SERVICE_ACCOUNT_KEY not set in settings")
        env_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
        if env_key:
            print(f"   [OK] Found in environment variable: {env_key}")
        else:
            print(f"   [WARNING] Not found in environment variable either")
    
    # Check if firebase-admin is installed
    print(f"\n2. Checking firebase-admin package...")
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        print(f"   [OK] firebase-admin is installed (version: {firebase_admin.__version__ if hasattr(firebase_admin, '__version__') else 'unknown'})")
    except ImportError:
        print(f"   [ERROR] firebase-admin package not installed")
        print(f"   Install it with: pip install firebase-admin")
        return False
    
    # Test Firebase initialization
    print(f"\n3. Testing Firebase initialization...")
    try:
        # Re-initialize to test
        app = _initialize_firebase()
        if app:
            print(f"   [OK] Firebase Admin SDK initialized successfully")
            print(f"   [OK] Project ID: {app.project_id if hasattr(app, 'project_id') else 'N/A'}")
            return True
        else:
            print(f"   [ERROR] Firebase Admin SDK initialization failed")
            return False
    except Exception as e:
        print(f"   [ERROR] Error initializing Firebase: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_firebase_config()
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Firebase configuration test PASSED")
        print("Push notifications should work correctly!")
    else:
        print("[FAILED] Firebase configuration test FAILED")
        print("Please check the configuration and try again.")
    print("=" * 60)
    sys.exit(0 if success else 1)

