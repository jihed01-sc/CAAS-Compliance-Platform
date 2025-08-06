import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

from compliance.models import SystemControlStatus, InformationSystem, Control, Framework

print("=== SYSTEM CONTROL STATUS RECORDS ===")
for status in SystemControlStatus.objects.all():
    print(f"ID: {status.id}")
    print(f"  System: {status.system.name if status.system else 'None'}")
    print(f"  Framework: {status.framework.name if status.framework else 'None'}")
    print(f"  Control: {status.control.control_id if status.control else 'None'}")
    print(f"  Status: {status.status}")
    print(f"  Implementation Status: {status.implementation_status}")
    print(f"  Progress: {status.progress}%")

    # Safe check for owner
    try:
        if status.system and status.system.owner:
            print(f"  Owner: {status.system.owner.username}")
        else:
            print(f"  Owner: No owner set")
    except AttributeError:
        print(f"  Owner: No owner field or None")

    print("  ---")

print("\n=== INFORMATION SYSTEMS ===")
for system in InformationSystem.objects.all():
    print(f"ID: {system.id}")
    print(f"  Name: {system.name}")
    try:
        print(f"  Owner: {system.owner.username if system.owner else 'No owner'}")
    except AttributeError:
        print(f"  Owner: No owner field")

    print(f"  Frameworks: {list(system.frameworks.all())}")
    print(f"  Framework count: {system.frameworks.count()}")
    print("  ---")

print("\n=== CONTROLS ===")
print(f"Total controls: {Control.objects.count()}")
if Control.objects.exists():
    print("Sample controls:")
    for control in Control.objects.all()[:5]:
        print(f"  ID: {control.id} | {control.control_id}: {control.title}")
        print(f"    Framework: {control.framework.name if control.framework else 'None'}")
else:
    print("No controls found in database")

print("\n=== FRAMEWORKS ===")
for framework in Framework.objects.all():
    print(f"  {framework.name}: {framework.controls.count()} controls")

print("\n=== DEBUGGING INFO ===")
print(f"Total Systems: {InformationSystem.objects.count()}")
print(f"Total Controls: {Control.objects.count()}")
print(f"Total Frameworks: {Framework.objects.count()}")
print(f"Total SystemControlStatus: {SystemControlStatus.objects.count()}")

# Check for systems without frameworks
systems_without_frameworks = InformationSystem.objects.filter(frameworks__isnull=True)
print(f"Systems without frameworks: {systems_without_frameworks.count()}")
if systems_without_frameworks.exists():
    for system in systems_without_frameworks:
        print(f"  - {system.name}")