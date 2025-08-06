import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

# Check if you have other related models with data
try:
    from compliance.models import InformationSystem

    systems_count = InformationSystem.objects.count()
    print(f"InformationSystem records: {systems_count}")

    if systems_count > 0:
        print("Systems found:")
        for system in InformationSystem.objects.all():
            print(f"  - ID: {system.id}, Name: {system.name}")
except Exception as e:
    print(f"Error checking InformationSystem: {e}")

try:
    from compliance.models import Framework

    frameworks_count = Framework.objects.count()
    print(f"Framework records: {frameworks_count}")

    if frameworks_count > 0:
        print("Frameworks found:")
        for framework in Framework.objects.all():
            print(f"  - ID: {framework.id}, Name: {framework.name}")
except Exception as e:
    print(f"Error checking Framework: {e}")

try:
    from compliance.models import Control

    controls_count = Control.objects.count()
    print(f"Control records: {controls_count}")

    if controls_count > 0:
        print("Controls found:")
        for control in Control.objects.all()[:5]:  # Show first 5
            print(f"  - ID: {control.id}, Control ID: {control.control_id}")
except Exception as e:
    print(f"Error checking Control: {e}")