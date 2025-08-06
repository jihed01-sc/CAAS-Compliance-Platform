"""
Real-time deadline monitoring API endpoint
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from compliance.models import SystemControlStatus, Notification


@login_required
def check_deadlines_api(request):
    """
    API endpoint to check deadlines and create notifications in real-time
    This can be called via AJAX periodically from the frontend
    """
    now = timezone.now()
    warning_threshold = now + timedelta(days=3)  # 3 days warning

    # Get user's controls with deadlines
    user_controls = SystemControlStatus.objects.filter(
        system__owner=request.user,
        deadline__isnull=False,
        status__in=['under_review', 'not_started', 'in_progress', 'pending_evidence']
    ).select_related('system', 'control', 'controller__user', 'framework')

    notifications_created = 0
    warnings_created = 0
    overdue_updated = 0

    for control_status in user_controls:
        # Check if overdue
        if control_status.deadline < now:
            # Update status to pending if not already
            if control_status.status != 'pending':
                control_status.status = 'pending'
                control_status.save()
                overdue_updated += 1

                # Create overdue notification (only if not created today)
                existing_overdue = Notification.objects.filter(
                    user=request.user,
                    system_control_status=control_status,
                    notification_type='deadline_overdue',
                    created_at__date=now.date()
                ).exists()

                if not existing_overdue:
                    Notification.objects.create(
                        user=request.user,
                        notification_type='deadline_overdue',
                        title='🚨 Deadline Overdue',
                        message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is overdue.',
                        system_control_status=control_status,
                        priority='urgent'
                    )
                    notifications_created += 1

                    # Also notify controller if assigned
                    if control_status.controller:
                        Notification.objects.create(
                            user=control_status.controller.user,
                            notification_type='deadline_overdue',
                            title='🚨 Your Assignment is Overdue',
                            message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is overdue.',
                            system_control_status=control_status,
                            priority='urgent'
                        )

        # Check if approaching deadline (warning)
        elif control_status.deadline <= warning_threshold:
            # Create warning notification (only if not created today)
            existing_warning = Notification.objects.filter(
                user=request.user,
                system_control_status=control_status,
                notification_type='deadline_warning',
                created_at__date=now.date()
            ).exists()

            if not existing_warning:
                days_remaining = (control_status.deadline - now).days
                Notification.objects.create(
                    user=request.user,
                    notification_type='deadline_warning',
                    title='⚠️ Deadline Approaching',
                    message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is due in {days_remaining} day(s).',
                    system_control_status=control_status,
                    priority='high' if days_remaining <= 1 else 'medium'
                )
                warnings_created += 1

                # Also notify controller if assigned
                if control_status.controller:
                    Notification.objects.create(
                        user=control_status.controller.user,
                        notification_type='deadline_warning',
                        title='⚠️ Your Assignment Due Soon',
                        message=f'Control {control_status.control.control_id} in system "{control_status.system.name}" is due in {days_remaining} day(s).',
                        system_control_status=control_status,
                        priority='high' if days_remaining <= 1 else 'medium'
                    )

    # Get updated notification counts
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    urgent_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False,
        priority='urgent'
    ).count()

    return JsonResponse({
        'success': True,
        'notifications_created': notifications_created,
        'warnings_created': warnings_created,
        'overdue_updated': overdue_updated,
        'unread_count': unread_notifications,
        'urgent_count': urgent_notifications,
        'checked_at': now.isoformat()
    })
