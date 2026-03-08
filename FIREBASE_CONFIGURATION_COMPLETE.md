# Firebase Push Notification Configuration - Complete ✅

## Summary

Firebase Cloud Messaging (FCM) has been successfully configured for push notifications in the backend.

## What Was Configured

### 1. Firebase Service Account Key
- ✅ Fixed file name: `firebase-service-account-key.json` (removed double `.json` extension)
- ✅ File location: `backend/firebase-service-account-key.json`
- ✅ File is protected in `.gitignore` (will not be committed to Git)

### 2. Django Settings
- ✅ Updated `backend/airconditioning_system/settings.py`
- ✅ Uncommented and configured `FIREBASE_SERVICE_ACCOUNT_KEY` setting
- ✅ Path points to: `backend/firebase-service-account-key.json`

### 3. Firebase Admin SDK
- ✅ Already installed: `firebase-admin>=7.0.0` (version 7.1.0 confirmed)
- ✅ Initialization code in `backend/core/notifications.py` is working correctly
- ✅ Project ID: `pika-notification`

## How It Works

### Automatic Notifications

The system automatically sends push notifications when:

1. **New Project Created**
   - When a `ProjectInstallation` or `ProjectMaintenance` is created with a `technician_group`
   - All technicians in the assigned group receive a notification

2. **New Task Created**
   - When a `Traveaux` or `MaintenanceTraveaux` is created
   - All technicians in the project's `technician_group` receive a notification

### Notification Functions

Located in `backend/core/notifications.py`:

- `send_push_notification()` - Sends notifications to FCM tokens
- `notify_technicians_new_project()` - Notifies technicians about new projects
- `notify_technicians_new_task()` - Notifies technicians about new tasks
- `get_technician_tokens()` - Gets all active tokens for a technician
- `get_technician_group_tokens()` - Gets all active tokens for a technician group

## Testing

A test script is available to verify the configuration:

```bash
cd backend
python test_firebase_config.py
```

Expected output:
```
[SUCCESS] Firebase configuration test PASSED
Push notifications should work correctly!
```

## Verification

To verify Firebase is working:

1. **Check Django logs** when starting the server:
   ```
   Firebase Admin SDK initialized with service account key
   ```

2. **Test notification sending**:
   - Create a new project with a technician group assigned
   - Create a new task in a project with a technician group
   - Check backend logs for notification sending status

3. **Check device tokens**:
   - Ensure technicians have registered their device tokens via the mobile app
   - Device tokens are stored in the `DeviceToken` model
   - Only active tokens (`is_active=True`) will receive notifications

## Mobile App Requirements

For push notifications to work:

1. **Android App**:
   - Must have `google-services.json` in `android/app/` directory ✅ (already present)
   - Must be a development build (not Expo Go) for testing
   - Technicians must register their FCM tokens via the app

2. **Device Token Registration**:
   - The mobile app should call the device token registration endpoint
   - Tokens are stored in the `DeviceToken` model linked to technicians

## Troubleshooting

### Notifications Not Sending

1. **Check Firebase initialization**:
   ```bash
   python backend/test_firebase_config.py
   ```

2. **Check Django logs** for errors:
   - Look for "Firebase Admin SDK initialization failed"
   - Check for import errors or file path issues

3. **Verify device tokens exist**:
   - Check Django admin: `/admin/core/devicetoken/`
   - Ensure tokens are active (`is_active=True`)

4. **Check technician group assignment**:
   - Projects must have a `technician_group` assigned
   - Technicians must be members of that group

### Common Issues

- **"Firebase Admin SDK not initialized"**: Check that `firebase-service-account-key.json` exists and path is correct
- **"No active device tokens found"**: Ensure technicians have registered their device tokens via the mobile app
- **"Project has no technician group assigned"**: Assign a technician group to the project

## Security Notes

⚠️ **Important**: 
- The `firebase-service-account-key.json` file contains sensitive credentials
- It is already in `.gitignore` and should NEVER be committed to Git
- For production, consider using environment variables instead of file paths

## Next Steps

1. ✅ Firebase configuration is complete
2. ✅ Test script created and verified
3. ⏭️ Test with actual device tokens from the mobile app
4. ⏭️ Monitor notification delivery in production

## Files Modified

- `backend/firebase-service-account-key.json` - Created (fixed name)
- `backend/firebase-service-account-key.json.json` - Deleted (incorrect name)
- `backend/airconditioning_system/settings.py` - Updated Firebase configuration
- `backend/test_firebase_config.py` - Created test script

## Files Already Configured (No Changes Needed)

- `backend/core/notifications.py` - Firebase initialization and notification functions
- `backend/core/views.py` - Notification calls in project/task creation
- `backend/requirements.txt` - firebase-admin already included
- `backend/.gitignore` - Firebase key file already protected

---

**Status**: ✅ Configuration Complete and Tested
**Date**: Configuration completed successfully
**Test Result**: PASSED ✅

