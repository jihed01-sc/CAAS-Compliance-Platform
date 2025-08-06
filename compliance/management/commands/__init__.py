from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.forms import formset_factory
from django.db import transaction
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.conf import settings

from compliance.models import (
    InformationSystem, Framework, Control,
    SystemControlStatus, Evidence, ControllerProfile, Notification,
    ControlCategory, EvidenceReview
)
from compliance.forms import (
    SystemCreationForm, ControlAssignmentForm, EvidenceUploadForm,
    EvidenceReviewForm, SystemControlStatusForm
)


@login_required
def dashboard(request):
    """Main compliance dashboard"""
    # Get systems owned by current user
    user_systems = InformationSystem.objects.filter(owner=request.user)

    # Get controls assigned to current user (if they're a controller)
    assigned_controls = SystemControlStatus.objects.filter(
        controller__user=request.user
    ).select_related('system', 'control', 'controller')

    # Statistics
    total_systems = user_systems.count()
    total_assigned_controls = assigned_controls.count()

    # Controls by status
    compliant_controls = assigned_controls.filter(status='compliant').count()
    non_compliant_controls = assigned_controls.filter(status='non_compliant').count()
    pending_controls = assigned_controls.filter(status='under_review').count()

    # Upcoming deadlines
    upcoming_deadlines = assigned_controls.filter(
        deadline__isnull=False,
        deadline__gte=timezone.now(),
        deadline__lte=timezone.now() + timezone.timedelta(days=7)
    ).order_by('deadline')[:5]

    # Overdue items
    overdue_items = assigned_controls.filter(
        deadline__isnull=False,
        deadline__lt=timezone.now(),
        status__in=['non_compliant', 'under_review']
    ).order_by('deadline')[:5]

    # Recent notifications
    recent_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    context = {
        'user_systems': user_systems,
        'assigned_controls': assigned_controls[:10],  # Recent 10
        'total_systems': total_systems,
        'total_assigned_controls': total_assigned_controls,
        'compliant_controls': compliant_controls,
        'non_compliant_controls': non_compliant_controls,
        'pending_controls': pending_controls,
        'upcoming_deadlines': upcoming_deadlines,
        'overdue_items': overdue_items,
        'recent_notifications': recent_notifications,
    }

    return render(request, 'compliance/dashboard.html', context)


@login_required
def create_system(request):
    """Create a new information system"""
    if request.method == 'POST':
        form = SystemCreationForm(request.POST)
        if form.is_valid():
            system = form.save(commit=False)
            system.owner = request.user
            system.save()
            form.save_m2m()  # Save many-to-many relationships

            messages.success(request, f'System "{system.name}" created successfully!')
            return redirect('assign_controls', system_id=system.id)
    else:
        form = SystemCreationForm()

    return render(request, 'compliance/create_system.html', {'form': form})


@login_required
def assign_controls(request, system_id):
    """Assign controls to a system and controllers"""
    system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

    # Get available controls for selected frameworks
    available_controls = Control.objects.filter(
        framework__in=system.frameworks.all()
    ).select_related('framework', 'category')

    # Get available controllers
    controllers = ControllerProfile.objects.filter(is_active=True).select_related('user')

    if request.method == 'POST':
        selected_controls = request.POST.getlist('controls')

        with transaction.atomic():
            for control_id in selected_controls:
                control = get_object_or_404(Control, id=control_id)
                controller_id = request.POST.get(f'controller_{control_id}')
                previously_implemented = request.POST.get(f'previously_implemented_{control_id}') == 'true'

                # Create or update SystemControlStatus
                system_control, created = SystemControlStatus.objects.get_or_create(
                    system=system,
                    control=control,
                    defaults={
                        'controller_id': controller_id if controller_id else None,
                        'previously_implemented': previously_implemented,
                        'status': 'under_review',
                        'implementation_status': 'not_started'
                    }
                )

                if not created:
                    # Update existing
                    system_control.controller_id = controller_id if controller_id else None
                    system_control.previously_implemented = previously_implemented
                    system_control.save()

                # Create notification for assigned controller
                if controller_id:
                    controller = ControllerProfile.objects.get(id=controller_id)
                    Notification.objects.create(
                        user=controller.user,
                        notification_type='control_assigned',
                        title='New Control Assigned',
                        message=f'You have been assigned control {control.control_id} for system {system.name}',
                        system_control_status=system_control
                    )

        messages.success(request, 'Controls assigned successfully!')
        return redirect('system_detail', system_id=system.id)

    # Group controls by category for better organization
    controls_by_category = {}
    for control in available_controls:
        category_path = control.category.get_full_path()
        if category_path not in controls_by_category:
            controls_by_category[category_path] = []
        controls_by_category[category_path].append(control)

    context = {
        'system': system,
        'controls_by_category': controls_by_category,
        'controllers': controllers,
    }

    return render(request, 'compliance/assign_controls.html', context)


@login_required
def system_detail(request, system_id):
    """Detailed view of a system with all its controls"""
    system = get_object_or_404(InformationSystem, id=system_id)

    # Check if user can view this system
    if system.owner != request.user:
        # Check if user is assigned as controller for any controls
        if not SystemControlStatus.objects.filter(
                system=system,
                controller__user=request.user
        ).exists():
            messages.error(request, 'You do not have permission to view this system.')
            return redirect('dashboard')

    # Get all control statuses for this system
    control_statuses = SystemControlStatus.objects.filter(
        system=system
    ).select_related('control', 'controller__user').order_by('control__control_id')

    # Group by category for hierarchical display
    statuses_by_category = {}
    for status in control_statuses:
        category_path = status.control.category.get_full_path()
        if category_path not in statuses_by_category:
            statuses_by_category[category_path] = []
        statuses_by_category[category_path].append(status)

    # Statistics
    total_controls = control_statuses.count()
    compliant_count = control_statuses.filter(status='compliant').count()
    non_compliant_count = control_statuses.filter(status='non_compliant').count()
    partial_count = control_statuses.filter(status='partially_compliant').count()

    # Progress calculation
    overall_progress = system.progress

    context = {
        'system': system,
        'statuses_by_category': statuses_by_category,
        'total_controls': total_controls,
        'compliant_count': compliant_count,
        'non_compliant_count': non_compliant_count,
        'partial_count': partial_count,
        'overall_progress': overall_progress,
    }

    return render(request, 'compliance/system_detail.html', context)


@login_required
def control_detail(request, control_status_id):
    """Detailed view of a specific control implementation"""
    control_status = get_object_or_404(
        SystemControlStatus,
        id=control_status_id
    )

    # Check permissions
    if (control_status.system.owner != request.user and
            control_status.controller.user != request.user):
        messages.error(request, 'You do not have permission to view this control.')
        return redirect('dashboard')

    # Get evidence files
    evidence_files = Evidence.objects.filter(
        system_control_status=control_status
    ).order_by('-uploaded_at')

    # Get review history
    reviews = EvidenceReview.objects.filter(
        evidence__system_control_status=control_status
    ).order_by('-reviewed_at')

    context = {
        'control_status': control_status,
        'evidence_files': evidence_files,
        'reviews': reviews,
    }

    return render(request, 'compliance/control_detail.html', context)


@login_required
def upload_evidence(request, control_status_id):
    """Upload evidence for a control"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Check if user is the assigned controller
    if control_status.controller.user != request.user:
        messages.error(request, 'You are not authorized to upload evidence for this control.')
        return redirect('control_detail', control_status_id=control_status_id)

    if request.method == 'POST':
        form = EvidenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.system_control_status = control_status
            evidence.uploaded_by = request.user
            evidence.save()

            # Create notification for system owner
            Notification.objects.create(
                user=control_status.system.owner,
                notification_type='evidence_uploaded',
                title='Evidence Uploaded',
                message=f'Evidence uploaded for control {control_status.control.control_id} in system {control_status.system.name}',
                system_control_status=control_status
            )

            messages.success(request, 'Evidence uploaded successfully!')
            return redirect('control_detail', control_status_id=control_status_id)
    else:
        form = EvidenceUploadForm()

    context = {
        'form': form,
        'control_status': control_status,
    }

    return render(request, 'compliance/upload_evidence.html', context)


@login_required
def review_evidence(request, evidence_id):
    """Review uploaded evidence"""
    evidence = get_object_or_404(Evidence, id=evidence_id)

    # Check if user is system owner or has review permissions
    if evidence.system_control_status.system.owner != request.user:
        messages.error(request, 'You are not authorized to review this evidence.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = EvidenceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.evidence = evidence
            review.reviewer = request.user
            review.save()

            # Update evidence status
            evidence.approval_status = review.status
            evidence.reviewer_feedback = review.feedback
            evidence.reviewed_by = request.user
            evidence.reviewed_at = timezone.now()
            evidence.save()

            # Create notification for controller
            notification_type = 'evidence_approved' if review.status == 'approved' else 'evidence_rejected'
            Notification.objects.create(
                user=evidence.system_control_status.controller.user,
                notification_type=notification_type,
                title=f'Evidence {review.status.title()}',
                message=f'Your evidence for control {evidence.system_control_status.control.control_id} has been {review.status}',
                system_control_status=evidence.system_control_status
            )

            messages.success(request, 'Evidence review completed!')
            return redirect('control_detail', control_status_id=evidence.system_control_status.id)
    else:
        form = EvidenceReviewForm()

    context = {
        'form': form,
        'evidence': evidence,
    }

    return render(request, 'compliance/review_evidence.html', context)


@login_required
def my_assignments(request):
    """View all controls assigned to current user"""
    try:
        controller_profile = ControllerProfile.objects.get(user=request.user)
    except ControllerProfile.DoesNotExist:
        messages.info(request, 'You are not registered as a controller.')
        return redirect('dashboard')

    # Get all assigned controls
    assigned_controls = SystemControlStatus.objects.filter(
        controller=controller_profile
    ).select_related('system', 'control').order_by('deadline')

    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        assigned_controls = assigned_controls.filter(status=status_filter)

    # Pagination
    paginator = Paginator(assigned_controls, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'controller_profile': controller_profile,
    }

    return render(request, 'compliance/my_assignments.html', context)


@login_required
def update_control_status(request, control_status_id):
    """Update control implementation status"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Check permissions
    if control_status.controller.user != request.user:
        messages.error(request, 'You are not authorized to update this control.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = SystemControlStatusForm(request.POST, instance=control_status)
        if form.is_valid():
            form.save()
            messages.success(request, 'Control status updated successfully!')
            return redirect('control_detail', control_status_id=control_status_id)
    else:
        form = SystemControlStatusForm(instance=control_status)

    context = {
        'form': form,
        'control_status': control_status,
    }

    return render(request, 'compliance/update_control_status.html', context)


@login_required
def notifications(request):
    """View all notifications for current user"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    # Mark as read if requested
    if request.GET.get('mark_read'):
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')

    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }

    return render(request, 'compliance/notifications.html', context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    return JsonResponse({'status': 'success'})


@login_required
def system_progress_api(request, system_id):
    """API endpoint for system progress data"""
    system = get_object_or_404(InformationSystem, id=system_id)

    # Check permissions
    if system.owner != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    control_statuses = SystemControlStatus.objects.filter(system=system)

    progress_data = {
        'overall_progress': system.progress,
        'total_controls': control_statuses.count(),
        'compliant': control_statuses.filter(status='compliant').count(),
        'non_compliant': control_statuses.filter(status='non_compliant').count(),
        'partially_compliant': control_statuses.filter(status='partially_compliant').count(),
        'under_review': control_statuses.filter(status='under_review').count(),
    }

    return JsonResponse(progress_data)


@login_required
def deadline_countdown_api(request, control_status_id):
    """API endpoint for deadline countdown"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Check permissions
    if (control_status.system.owner != request.user and
            control_status.controller.user != request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    time_remaining = control_status.time_remaining

    if time_remaining:
        days = time_remaining.days
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        countdown_data = {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'total_seconds': time_remaining.total_seconds(),
            'is_overdue': False
        }
    else:
        countdown_data = {
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'total_seconds': 0,
            'is_overdue': control_status.is_deadline_passed
        }

    return JsonResponse(countdown_data)


@login_required
def reports_dashboard(request):
    """Reports and analytics dashboard"""
    # Overall statistics
    total_systems = InformationSystem.objects.count()
    total_controls = SystemControlStatus.objects.count()

    # Status distribution
    status_counts = SystemControlStatus.objects.values('status').annotate(count=Count('id'))

    # Framework distribution
    framework_counts = InformationSystem.objects.values(
        'frameworks__name'
    ).annotate(count=Count('id'))

    # Recent activity
    recent_evidence = Evidence.objects.select_related(
        'system_control_status__system',
        'system_control_status__control'
    ).order_by('-uploaded_at')[:10]

    context = {
        'total_systems': total_systems,
        'total_controls': total_controls,
        'status_counts': status_counts,
        'framework_counts': framework_counts,
        'recent_evidence': recent_evidence,
    }

    return render(request, 'compliance/reports_dashboard.html', context)