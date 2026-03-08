"""
Quick test script to verify Django server is accessible
Run this to test if the server responds
"""
import requests
import sys

def test_connection(ip="192.168.8.102", port=8000):
    url = f"http://{ip}:{port}/api/"
    try:
        response = requests.get(url, timeout=5)
        print(f"✅ SUCCESS! Server is accessible at {url}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR: Cannot reach {url}")
        print("Possible causes:")
        print("  - Windows Firewall is blocking the connection")
        print("  - Server is not running on 0.0.0.0:8000")
        print("  - Network isolation (AP isolation) is enabled on router")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT: Server at {url} is not responding")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing Django server connection...")
    print("=" * 50)
    test_connection()


