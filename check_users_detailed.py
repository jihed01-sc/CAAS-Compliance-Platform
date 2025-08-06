import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

from django.contrib.auth.models import User
from compliance.models import SystemControlStatus, InformationSystem, Control, Framework, Evidence
from datetime import datetime

print("=" * 50)
print("DETAILED USER ANALYSIS WITH PASSWORD HASHES")
print("=" * 50)

# Check all users in the system
print("\n=== ALL USERS IN DATABASE ===")
users = User.objects.all()
for user in users:
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"First Name: {user.first_name}")
    print(f"Last Name: {user.last_name}")
    print(f"Password Hash: {user.password}")
    print(f"Date Joined: {user.date_joined}")
    print(f"Last Login: {user.last_login}")
    print(f"Is Staff: {user.is_staff}")
    print(f"Is Superuser: {user.is_superuser}")
    print(f"Is Active: {user.is_active}")
    print("-" * 50)

print(f"\nTotal Users: {users.count()}")

# Additional information about password hashing
print("\n" + "=" * 50)
print("PASSWORD SECURITY INFO")
print("=" * 50)
print("Note: Django stores passwords as hashed values for security.")
print("The password hashes shown above use Django's PBKDF2 algorithm by default.")
print("These cannot be reversed to get the original passwords.")
print("If you need to reset a password, use Django's management commands or admin interface.")

print("\n" + "=" * 50)
print("WHAT EACH USER CREATED")
print("=" * 50)

for user in users:
    print(f"\n>>> USER: {user.username} <<<")

    # Systems created by this user
    user_systems = InformationSystem.objects.filter(owner=user)
    print(f"\nSystems Created ({user_systems.count()}):")
    for system in user_systems:
        print(f"  - {system.name}")
        print(f"    ID: {system.id}")
        if hasattr(system, 'created_at'):
            print(f"    Created: {system.created_at}")
        frameworks = system.frameworks.all()
        print(f"    Frameworks: {[f.name for f in frameworks]}")

    # System Control Status records created/assigned to this user
    user_controls = SystemControlStatus.objects.filter(system__owner=user)
    print(f"\nControl Implementations ({user_controls.count()}):")
    for control in user_controls:
        print(f"  - System: {control.system.name}")
        print(f"    Framework: {control.framework.name}")
        print(f"    Control: {control.control.control_id}")
        print(f"    Status: {control.status}")
        print(f"    Progress: {control.progress}%")
        print(f"    Implementation Status: {control.implementation_status}")

    # Evidence uploaded by this user (if evidence model has user field)
    try:
        user_evidence = Evidence.objects.filter(uploaded_by=user)
        print(f"\nEvidence Uploaded ({user_evidence.count()}):")
        for evidence in user_evidence:
            print(f"  - File: {evidence.file.name if evidence.file else 'No file'}")
            print(f"    Description: {evidence.description}")
            if hasattr(evidence, 'uploaded_at'):
                print(f"    Uploaded: {evidence.uploaded_at}")
    except:
        print(f"\nEvidence: Cannot access evidence data for this user")

    print("-" * 50)

# Summary statistics
print(f"\n=== SUMMARY STATISTICS ===")
print(f"Total Users: {User.objects.count()}")
print(f"Active Users: {User.objects.filter(is_active=True).count()}")
print(f"Staff Users: {User.objects.filter(is_staff=True).count()}")
print(f"Superusers: {User.objects.filter(is_superuser=True).count()}")

print(f"\nTotal Information Systems: {InformationSystem.objects.count()}")
print(f"Systems with Owners: {InformationSystem.objects.exclude(owner=None).count()}")
print(f"Systems without Owners: {InformationSystem.objects.filter(owner=None).count()}")

print(f"\nTotal Control Implementations: {SystemControlStatus.objects.count()}")
print(f"Implementations with System Owners: {SystemControlStatus.objects.exclude(system__owner=None).count()}")

# Show which users own which systems
print(f"\n=== SYSTEM OWNERSHIP BREAKDOWN ===")
systems_with_owners = InformationSystem.objects.exclude(owner=None)
for system in systems_with_owners:
    print(f"System: {system.name} -> Owner: {system.owner.username}")

# Recent activity (if timestamps are available)
print(f"\n=== RECENT USER ACTIVITY ===")
recent_users = User.objects.filter(last_login__isnull=False).order_by('-last_login')[:5]
for user in recent_users:
    print(f"{user.username} - Last login: {user.last_login}")
