import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

from django.test import Client
from django.urls import reverse

# Create a test client
client = Client()

print("Testing Password Reset System:")
print("=" * 50)

# Test 1: Check if the login page loads
try:
    login_response = client.get('/auth/login/')
    print(f"✅ Login page status: {login_response.status_code}")
except Exception as e:
    print(f"❌ Login page error: {e}")

# Test 2: Check if password reset page loads
try:
    reset_response = client.get('/auth/password-reset/')
    print(f"✅ Password reset page status: {reset_response.status_code}")
    if reset_response.status_code != 200:
        print(f"❌ Password reset page content: {reset_response.content[:500]}")
except Exception as e:
    print(f"❌ Password reset page error: {e}")

# Test 3: Check if the password reset view exists
try:
    from authentication.password_reset_views import PasswordResetRequestView
    print("✅ PasswordResetRequestView imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")

# Test 4: Test the URL reverse
try:
    url = reverse('password_reset_request')
    print(f"✅ URL reversal works: {url}")
except Exception as e:
    print(f"❌ URL reversal error: {e}")

print("\nIf you see any ❌ errors above, that's the issue!")
print("If all ✅ pass, the system should work - try again in browser.")
