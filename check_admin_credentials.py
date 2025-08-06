import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

from django.contrib.auth.models import User

print("Admin Credentials Check")
print("=" * 50)

# Get all superusers
superusers = User.objects.filter(is_superuser=True)

if superusers.exists():
    print(f"Found {superusers.count()} admin user(s):")
    print("-" * 30)

    for user in superusers:
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"First Name: {user.first_name}")
        print(f"Last Name: {user.last_name}")
        print(f"Is Active: {user.is_active}")
        print(f"Is Staff: {user.is_staff}")
        print(f"Is Superuser: {user.is_superuser}")
        print(f"Date Joined: {user.date_joined}")
        print(f"Last Login: {user.last_login}")
        print("-" * 30)
else:
    print("❌ No admin users found!")
    print("You may need to create a superuser with: python manage.py createsuperuser")

# Also check all users
print("\nAll Users in Database:")
print("=" * 50)
all_users = User.objects.all()

if all_users.exists():
    for user in all_users:
        status = "Admin" if user.is_superuser else "Staff" if user.is_staff else "Regular"
        print(f"Username: {user.username} | Email: {user.email} | Status: {status} | Active: {user.is_active}")
else:
    print("No users found in database!")
