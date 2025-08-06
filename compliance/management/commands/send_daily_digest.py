
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from datetime import timedelta
import logging

from compliance.models import SystemControlStatus, Evidence, Notification

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send daily digest emails to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        yesterday = now - timedelta(days=1)

        self.stdout.write(f'Generating daily digest for {now.date()}')

        # Get all users who have assignments or own systems
        users_with_assignments = User.objects.filter(
            controller_profile__systemcontrolstatus__isnull=False
        ).distinct() | User.objects.filter(
            owned_systems__isnull=False
        ).distinct()

        for user in users_with_assignments:
            self.send_user_digest(user, now, yesterday, dry_run)

        self.stdout.write(self.style.SUCCESS('Daily digest processing completed'))

    def send_user_digest(self, user, now, yesterday, dry_run):
        """Send a daily digest email to a single user"""
        # Collect data for the digest
        approaching_deadlines = SystemControlStatus.objects.filter(
            controller__user=user,
            deadline__gte=now,
            deadline__lte=now + timedelta(days=3),
            status__in=['non_compliant', 'partially_compliant', 'under_review']
        ).order_by('deadline')

        overdue_controls = SystemControlStatus.objects.filter(
            controller__user=user,
            deadline__lt=now,
            status__in=['non_compliant', 'partially_compliant', 'under_review']
        )

        evidence_uploads = Evidence.objects.filter(
            uploaded_by=user,
            uploaded_at__gte=yesterday,
            uploaded_at__lte=now
        )

        notifications = Notification.objects.filter(
            user=user,
            created_at__gte=yesterday,
            created_at__lte=now
        ).order_by('-created_at')

        # Skip users with no relevant activity
        if not (approaching_deadlines.exists() or overdue_controls.exists() or
                evidence_uploads.exists() or notifications.exists()):
            self.stdout.write(f'No digest content for {user.username}')
            return

        context = {
            'user': user,
            'approaching_deadlines': approaching_deadlines,
            'overdue_controls': overdue_controls,
            'evidence_uploads': evidence_uploads,
            'notifications': notifications,
            'date': now.date()
        }

        subject = f'Compliance Dashboard Daily Digest - {now.date()}'
        template = 'compliance/emails/daily_digest.html'

        if dry_run:
            self.stdout.write(
                f'DRY RUN: Would send digest to {user.username} '
                f'({approaching_deadlines.count()} approaching, '
                f'{overdue_controls.count()} overdue, '
                f'{evidence_uploads.count()} evidence, '
                f'{notifications.count()} notifications)'
            )
            return

        try:
            html_message = render_to_string(template, context)
            send_mail(
                subject=subject,
                message='',  # Plain text version
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            self.stdout.write(f'Sent digest to {user.email}')
        except Exception as e:
            logger.error(f'Failed to send digest to {user.email}: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Failed to send digest to {user.email}: {str(e)}'))
