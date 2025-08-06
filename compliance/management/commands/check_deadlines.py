"""
Django management command to check deadlines and send notifications
Run this command periodically (e.g., daily via cron job)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from compliance.models import SystemControlStatus, Notification
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Check deadlines and send notifications for overdue and approaching deadlines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--warning-days',
            type=int,
            default=3,
            help='Days before deadline to send warning notifications (default: 3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually sending notifications'
        )

    def handle(self, *args, **options):
        warning_days = options['warning_days']
        dry_run = options['dry_run']
        
        self.stdout.write(f"Checking deadlines with {warning_days} day warning period...")
        
        now = timezone.now()
        warning_threshold = now + timedelta(days=warning_days)
        
        # Get all active control statuses with deadlines
        controls_with_deadlines = SystemControlStatus.objects.filter(
            deadline__isnull=False,
            status__in=['under_review', 'not_started', 'in_progress']
        ).select_related('system', 'control', 'controller__user', 'framework')
        
        warning_count = 0
        overdue_count = 0
        email_count = 0
        
        for control_status in controls_with_deadlines:
            # Check if deadline is overdue
            if control_status.deadline < now:
                overdue_count += self.handle_overdue_deadline(control_status, dry_run)
                email_count += self.send_overdue_email(control_status, dry_run)
            
            # Check if deadline is approaching (warning)
            elif control_status.deadline <= warning_threshold:
                warning_count += self.send_warning_notification(control_status, dry_run)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Deadline check completed:\n"
                f"- Warning notifications: {warning_count}\n"
                f"- Overdue items processed: {overdue_count}\n"
                f"- Email alerts sent: {email_count}\n"
                f"- Dry run: {dry_run}"
            )
        )

    def handle_overdue_deadline(self, control_status, dry_run=False):
        """Handle overdue deadlines by updating status and creating notifications"""
        if control_status.status != 'pending':
            if not dry_run:
                # Update status to pending for overdue items
                control_status.status = 'pending'
                control_status.save()
                
                # Create overdue notification
                Notification.objects.create(
                    user=control_status.system.owner,
                    notification_type='deadline_overdue',
                    title='🚨 Deadline Overdue',
                    message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is overdue. Status updated to pending.',
                    system_control_status=control_status,
                    priority='high'
                )
                
                # Also notify the controller if assigned
                if control_status.controller:
                    Notification.objects.create(
                        user=control_status.controller.user,
                        notification_type='deadline_overdue',
                        title='🚨 Your Assigned Control is Overdue',
                        message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is overdue.',
                        system_control_status=control_status,
                        priority='high'
                    )
            
            self.stdout.write(
                self.style.ERROR(
                    f"{'[DRY RUN] ' if dry_run else ''}Overdue: {control_status.control.control_id} "
                    f"in {control_status.system.name} (deadline: {control_status.deadline})"
                )
            )
            return 1
        return 0

    def send_warning_notification(self, control_status, dry_run=False):
        """Send warning notification for approaching deadlines"""
        days_until_deadline = (control_status.deadline - timezone.now()).days
        
        # Check if we already sent a warning for this deadline
        existing_warning = Notification.objects.filter(
            system_control_status=control_status,
            notification_type='deadline_warning',
            created_at__gte=timezone.now() - timedelta(days=1)
        ).exists()
        
        if not existing_warning:
            if not dry_run:
                # Create warning notification for system owner
                Notification.objects.create(
                    user=control_status.system.owner,
                    notification_type='deadline_warning',
                    title='⚠️ Deadline Approaching',
                    message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is due in {days_until_deadline} day(s).',
                    system_control_status=control_status,
                    priority='medium'
                )
                
                # Also notify the controller if assigned
                if control_status.controller:
                    Notification.objects.create(
                        user=control_status.controller.user,
                        notification_type='deadline_warning',
                        title='⚠️ Your Assignment Due Soon',
                        message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is due in {days_until_deadline} day(s).',
                        system_control_status=control_status,
                        priority='medium'
                    )
            
            self.stdout.write(
                self.style.WARNING(
                    f"{'[DRY RUN] ' if dry_run else ''}Warning: {control_status.control.control_id} "
                    f"in {control_status.system.name} due in {days_until_deadline} day(s)"
                )
            )
            return 1
        return 0

    def send_overdue_email(self, control_status, dry_run=False):
        """Send email alert for overdue deadlines"""
        if not control_status.controller or not control_status.controller.user.email:
            return 0
        
        # Check if we already sent an overdue email today
        existing_email_notification = Notification.objects.filter(
            system_control_status=control_status,
            notification_type='email_sent',
            created_at__gte=timezone.now() - timedelta(days=1)
        ).exists()
        
        if not existing_email_notification:
            recipient_email = control_status.controller.user.email
            
            if not dry_run:
                try:
                    # Prepare email context
                    context = {
                        'control_status': control_status,
                        'controller_name': control_status.controller.user.get_full_name() or control_status.controller.user.username,
                        'days_overdue': (timezone.now() - control_status.deadline).days,
                        'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}/"
                    }
                    
                    # Send email
                    send_mail(
                        subject=f'🚨 URGENT: Overdue Compliance Control - {control_status.control.control_id}',
                        message=f'''
Dear {context['controller_name']},

This is an urgent alert regarding an overdue compliance control assigned to you.

Control Details:
- Control ID: {control_status.control.control_id}
- Control Title: {control_status.control.title}
- System: {control_status.system.name}
- Framework: {control_status.framework.name}
- Original Deadline: {control_status.deadline.strftime('%Y-%m-%d %H:%M')}
- Days Overdue: {context['days_overdue']}

Action Required:
The status has been automatically updated to "PENDING" due to the missed deadline. 
Please log into the compliance system immediately to:
1. Upload evidence if available
2. Update the implementation status
3. Contact the system owner if you need an extension

Access the system: {context['dashboard_url']}

This is an automated alert. Please do not reply to this email.

Best regards,
CAAS Compliance System
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=False,
                    )
                    
                    # Record that we sent the email
                    Notification.objects.create(
                        user=control_status.controller.user,
                        notification_type='email_sent',
                        title='📧 Overdue Email Alert Sent',
                        message=f'Email alert sent for overdue control {control_status.control.control_id}',
                        system_control_status=control_status
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Email sent to {recipient_email} for overdue control {control_status.control.control_id}"
                        )
                    )
                    return 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to send email to {recipient_email}: {str(e)}"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[DRY RUN] Would send email to {recipient_email} for overdue control {control_status.control.control_id}"
                    )
                )
                return 1
        return 0
