#!/usr/bin/env python3
"""
Test script to check contract API endpoints
"""
import os
import sys
import django
import requests
import json

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'airconditioning_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import Contract

User = get_user_model()

def get_auth_token():
    """Get authentication token for testing"""
    try:
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'ADMIN',
                'is_active': True
            }
        )
        
        # Generate token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        print(f"✅ Generated token for user: {user.username}")
        return access_token
    except Exception as e:
        print(f"❌ Error generating token: {e}")
        return None

def test_contracts_list():
    """Test the contracts list endpoint"""
    print("\n🔍 Testing contracts list endpoint...")
    
    token = get_auth_token()
    if not token:
        return False
    
    try:
        response = requests.get(
            'http://127.0.0.1:8000/api/contracts/',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Contracts list successful!")
            print(f"Number of contracts: {len(data.get('results', []))}")
            
            # Show first contract if available
            if data.get('results'):
                first_contract = data['results'][0]
                print(f"First contract ID: {first_contract.get('id')}")
                print(f"First contract code: {first_contract.get('code')}")
                return first_contract.get('id')
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return None

def test_contract_detail(contract_id):
    """Test the contract detail endpoint"""
    print(f"\n🔍 Testing contract detail endpoint for ID: {contract_id}...")
    
    token = get_auth_token()
    if not token:
        return False
    
    try:
        response = requests.get(
            f'http://127.0.0.1:8000/api/contracts/{contract_id}/',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Contract detail successful!")
            print(f"Contract ID: {data.get('id')}")
            print(f"Contract Code: {data.get('code')}")
            print(f"Client Name: {data.get('client_name')}")
            print(f"Site Title: {data.get('site_title')}")
            print(f"Status: {data.get('status')}")
            print(f"Equipment Count: {data.get('equipment_count')}")
            print(f"Actions Count: {data.get('actions_count')}")
            print(f"Total Price: {data.get('total_price')}")
            print(f"Equipment Data: {len(data.get('equipment_data', []))} items")
            
            # Check if actions_count is working
            if 'actions_count' in data:
                print(f"✅ actions_count field is present: {data['actions_count']}")
            else:
                print(f"❌ actions_count field is missing!")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

def test_actions_endpoint(contract_id):
    """Test the actions endpoint for a contract"""
    print(f"\n🔍 Testing actions endpoint for contract ID: {contract_id}...")
    
    token = get_auth_token()
    if not token:
        return False
    
    try:
        response = requests.get(
            f'http://127.0.0.1:8000/api/actions/?contract_id={contract_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Actions endpoint successful!")
            print(f"Number of actions: {len(data.get('results', []))}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

def test_team_groups_endpoint():
    """Test the team groups endpoint"""
    print(f"\n🔍 Testing team groups endpoint...")
    
    token = get_auth_token()
    if not token:
        return False
    
    try:
        response = requests.get(
            'http://127.0.0.1:8000/api/team-groups/',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Team groups endpoint successful!")
            print(f"Number of team groups: {len(data.get('results', []))}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return False

def main():
    """Main test function"""
    print("🚀 Starting Contract API Tests...")
    print("=" * 50)
    
    # Test 1: Contracts list
    contract_id = test_contracts_list()
    
    if contract_id:
        # Test 2: Contract detail
        test_contract_detail(contract_id)
        
        # Test 3: Actions endpoint
        test_actions_endpoint(contract_id)
    
    # Test 4: Team groups
    test_team_groups_endpoint()
    
    print("\n" + "=" * 50)
    print("🏁 Testing completed!")

if __name__ == '__main__':
    main()
