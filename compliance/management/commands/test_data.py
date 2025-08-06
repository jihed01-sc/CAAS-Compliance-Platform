# management/commands/create_test_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from compliance.models import Framework, Control, InformationSystem


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Create test user
        user, created = User.objects.get_or_create(
            username='jihedpp',
            defaults={'email': 'test@example.com'}
        )
        if created:
            user.set_password('511')
            user.save()

        # Create test framework
        framework, created = Framework.objects.get_or_create(
            name='ISO 27001',
            defaults={'description': 'Test framework'}
        )

        self.stdout.write('Test data created successfully')