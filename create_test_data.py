import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE','compliance_project.settings')  # Replace with your actual project name
django.setup()

from django.contrib.auth.models import User
from compliance.models import SystemControlStatus, InformationSystem, Framework, Control, ControllerProfile
from django.utils import timezone

# Get or create a user
try:
    user = User.objects.first()  # Get any existing user
    print(f"Using user: {user.username}")
except:
    user = User.objects.create_user(username='testuser', password='testpass')
    print(f"Created user: {user.username}")

# Get or create a ControllerProfile
try:
    controller = ControllerProfile.objects.first()
    if not controller:
        controller = ControllerProfile.objects.create(user=user)
    print(f"Using controller: {controller.user.username}")
except:
    print("ControllerProfile model not found, will create without controller")
    controller = None

# Use your existing data
system = InformationSystem.objects.get(id=1)  # production.si
framework = Framework.objects.get(id=8)  # NIS2
control = Control.objects.get(id=822)  # Annex I.1.a

print(f"Using System: {system.name} (ID: {system.id})")
print(f"Using Framework: {framework.name} (ID: {framework.id})")
print(f"Using Control: {control.control_id} (ID: {control.id})")

# Create SystemControlStatus records
try:
    # Test record 1 - Not Started
    status1 = SystemControlStatus.objects.create(
        system=system,
        framework=framework,
        control=control,
        controller=controller,
        status='non_compliant',  # Using Control.STATUS_CHOICES
        implementation_status='not_started',
        progress=0,
        previously_implemented=False,
        notes='Test record for API testing'
    )
    print(f"Created SystemControlStatus ID: {status1.id} (not_started)")

    # Test record 2 - In Progress
    status2 = SystemControlStatus.objects.create(
        system=InformationSystem.objects.get(id=2),  # sys 1
        framework=Framework.objects.get(id=9),  # IEC62443
        control=Control.objects.get(id=823),  # Annex I.1.b
        controller=controller,
        status='partially_compliant',
        implementation_status='in_progress',
        progress=50,
        previously_implemented=True,
        notes='Test record in progress'
    )
    print(f"Created SystemControlStatus ID: {status2.id} (in_progress)")

    # Test record 3 - Completed
    status3 = SystemControlStatus.objects.create(
        system=InformationSystem.objects.get(id=3),  # sfa
        framework=Framework.objects.get(id=10),  # ISO27001
        control=Control.objects.get(id=824),  # Annex I.1.c
        controller=controller,
        status='compliant',
        implementation_status='completed',
        progress=100,
        previously_implemented=False,
        evidence_uploaded=True,
        evidence_approved=True,
        completed_at=timezone.now(),
        notes='Test record completed'
    )
    print(f"Created SystemControlStatus ID: {status3.id} (completed)")

    print(f"\nSystemControlStatus records created successfully!")
    print(f"You can now use these IDs in your Postman tests:")
    print(f"  - ID {status1.id} for testing not_started status")
    print(f"  - ID {status2.id} for testing in_progress status")
    print(f"  - ID {status3.id} for testing completed status")

except Exception as e:
    print(f"Error creating SystemControlStatus: {e}")
    print("This might be due to unique_together constraint or missing related models")