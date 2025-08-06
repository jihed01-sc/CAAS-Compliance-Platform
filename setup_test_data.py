#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('C:\\Users\\Jihed\\PycharmProjects\\CAAS_App')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'compliance_project.settings')
django.setup()

from django.contrib.auth.models import User
from compliance.models import (
    Framework, ControlCategory, Control, Organization,
    ControllerProfile, InformationSystem
)

def create_test_data():
    print("🚀 Creating test data for CAAS compliance system...")

    # Create test user if doesn't exist
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@caas.com',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print("✅ Created test user: testuser / testpass123")
    else:
        print("✅ Test user already exists: testuser")

    # Create Organization
    org, created = Organization.objects.get_or_create(
        name='Test Organization',
        defaults={'description': 'Test organization for compliance testing'}
    )
    print(f"✅ {'Created' if created else 'Found'} organization: {org.name}")

    # Create Frameworks
    frameworks_data = [
        {
            'name': 'ISO 27001',
            'description': 'Information Security Management System',
            'version': '2022'
        },
        {
            'name': 'NIS 2.0',
            'description': 'Network and Information Systems Directive',
            'version': '2.0'
        },
        {
            'name': 'IEC 62443',
            'description': 'Industrial Automation and Control Systems Security',
            'version': '2018'
        },
        {
            'name': 'IAM',
            'description': 'Identity and Access Management',
            'version': '1.0'
        }
    ]

    created_frameworks = []
    for fw_data in frameworks_data:
        fw, created = Framework.objects.get_or_create(
            name=fw_data['name'],
            defaults=fw_data
        )
        created_frameworks.append(fw)
        print(f"✅ {'Created' if created else 'Found'} framework: {fw.name}")

    # Create Control Categories for each framework
    categories_data = {
        'ISO 27001': [
            {'code': 'AC', 'name': 'Access Control'},
            {'code': 'IA', 'name': 'Identification and Authentication'},
            {'code': 'SC', 'name': 'System and Communications Protection'},
            {'code': 'CM', 'name': 'Configuration Management'},
        ],
        'NIS 2.0': [
            {'code': 'GOV', 'name': 'Governance'},
            {'code': 'RM', 'name': 'Risk Management'},
            {'code': 'SEC', 'name': 'Security Measures'},
            {'code': 'INC', 'name': 'Incident Response'},
        ],
        'IEC 62443': [
            {'code': 'FR', 'name': 'Foundational Requirements'},
            {'code': 'CR', 'name': 'Core Requirements'},
            {'code': 'PR', 'name': 'Protection Requirements'},
            {'code': 'MR', 'name': 'Monitoring Requirements'},
        ],
        'IAM': [
            {'code': 'ID', 'name': 'Identity Management'},
            {'code': 'AM', 'name': 'Access Management'},
            {'code': 'PM', 'name': 'Privilege Management'},
            {'code': 'CM', 'name': 'Credential Management'},
        ]
    }

    created_categories = {}
    for framework in created_frameworks:
        created_categories[framework.name] = []
        if framework.name in categories_data:
            for cat_data in categories_data[framework.name]:
                category, created = ControlCategory.objects.get_or_create(
                    framework=framework,
                    code=cat_data['code'],
                    defaults={
                        'name': cat_data['name'],
                        'description': f'{cat_data["name"]} controls for {framework.name}'
                    }
                )
                created_categories[framework.name].append(category)
                print(f"✅ {'Created' if created else 'Found'} category: {framework.name} - {category.name}")

    # Create Controls for each category
    controls_data = {
        'ISO 27001': {
            'AC': [
                {'id': 'AC-1', 'title': 'Access Control Policy and Procedures'},
                {'id': 'AC-2', 'title': 'Account Management'},
                {'id': 'AC-3', 'title': 'Access Enforcement'},
                {'id': 'AC-4', 'title': 'Information Flow Enforcement'},
            ],
            'IA': [
                {'id': 'IA-1', 'title': 'Identification and Authentication Policy'},
                {'id': 'IA-2', 'title': 'User Identification and Authentication'},
                {'id': 'IA-3', 'title': 'Device Identification and Authentication'},
            ],
            'SC': [
                {'id': 'SC-1', 'title': 'System and Communications Protection Policy'},
                {'id': 'SC-2', 'title': 'Application Partitioning'},
                {'id': 'SC-3', 'title': 'Security Function Isolation'},
            ],
            'CM': [
                {'id': 'CM-1', 'title': 'Configuration Management Policy'},
                {'id': 'CM-2', 'title': 'Baseline Configuration'},
                {'id': 'CM-3', 'title': 'Configuration Change Control'},
            ]
        },
        'NIS 2.0': {
            'GOV': [
                {'id': 'GOV-1', 'title': 'Cybersecurity Governance'},
                {'id': 'GOV-2', 'title': 'Risk Management Framework'},
            ],
            'RM': [
                {'id': 'RM-1', 'title': 'Risk Assessment'},
                {'id': 'RM-2', 'title': 'Risk Treatment'},
            ],
            'SEC': [
                {'id': 'SEC-1', 'title': 'Security Measures Implementation'},
                {'id': 'SEC-2', 'title': 'Network Security'},
            ],
            'INC': [
                {'id': 'INC-1', 'title': 'Incident Response Plan'},
                {'id': 'INC-2', 'title': 'Incident Reporting'},
            ]
        },
        'IEC 62443': {
            'FR': [
                {'id': 'FR-1', 'title': 'Identification and Authentication Control'},
                {'id': 'FR-2', 'title': 'Use Control'},
            ],
            'CR': [
                {'id': 'CR-1', 'title': 'Audit Trail'},
                {'id': 'CR-2', 'title': 'Communication Integrity'},
            ]
        },
        'IAM': {
            'ID': [
                {'id': 'ID-1', 'title': 'Identity Lifecycle Management'},
                {'id': 'ID-2', 'title': 'Identity Verification'},
            ],
            'AM': [
                {'id': 'AM-1', 'title': 'Access Request Process'},
                {'id': 'AM-2', 'title': 'Access Review'},
            ]
        }
    }

    for framework in created_frameworks:
        if framework.name in controls_data:
            for category in created_categories[framework.name]:
                if category.code in controls_data[framework.name]:
                    for control_data in controls_data[framework.name][category.code]:
                        control, created = Control.objects.get_or_create(
                            framework=framework,
                            control_id=control_data['id'],
                            defaults={
                                'category': category,
                                'title': control_data['title'],
                                'description': f'Implementation guidance for {control_data["title"]}',
                                'implementation_guidance': f'Detailed steps to implement {control_data["title"]} control.',
                                'risk_level': 'medium',
                                'status': 'under_review'
                            }
                        )
                        print(f"✅ {'Created' if created else 'Found'} control: {control.control_id} - {control.title}")

    # Create a Controller Profile for the test user
    controller_profile, created = ControllerProfile.objects.get_or_create(
        user=test_user,
        defaults={
            'department': 'IT Security',
            'expertise_areas': 'ISO 27001, Risk Management, Security Controls',
            'phone': '+1-555-0123',
            'is_active': True
        }
    )
    print(f"✅ {'Created' if created else 'Found'} controller profile for {test_user.username}")

    print("\n🎯 Test Data Summary:")
    print(f"   📊 Frameworks: {Framework.objects.count()}")
    print(f"   📋 Categories: {ControlCategory.objects.count()}")
    print(f"   🔧 Controls: {Control.objects.count()}")
    print(f"   🏢 Organizations: {Organization.objects.count()}")
    print(f"   👤 Users: {User.objects.count()}")
    print(f"   🎮 Controllers: {ControllerProfile.objects.count()}")

    print("\n🔑 Login Credentials:")
    print("   Username: testuser")
    print("   Password: testpass123")

    print("\n✨ Ready to test! Your compliance system is loaded with test data.")
    print("   You can now log in and test the complete user workflow.")

if __name__ == "__main__":
    create_test_data()
