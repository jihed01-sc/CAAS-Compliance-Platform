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
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import json

from .models import (
    InformationSystem, Framework, Control,
    SystemControlStatus, Evidence, ControllerProfile, Notification,
    ControlCategory, EvidenceReview,Assessment,ComplianceReport,QuestionnaireResult
)
from .forms import (
    SystemCreationForm, ControlAssignmentForm, EvidenceUploadForm,
    EvidenceReviewForm, SystemControlStatusForm,FrameworkAssignmentForm,
)


from django.shortcuts import render
from django.views.decorators.csrf import get_token


@login_required
@login_required
def dashboard_view(request):
    """Main compliance dashboard with framework and control assignment"""
    user_systems = InformationSystem.objects.filter(owner=request.user).select_related('organization')
    frameworks = Framework.objects.all()

    # Handle framework assignment POST request
    if request.method == 'POST' and 'assign_framework' in request.POST:
        system_id = request.POST.get('system_id')
        system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

        form = FrameworkAssignmentForm(system=system, data=request.POST)
        if form.is_valid():
            framework = form.cleaned_data['framework']
            # Add framework to system using ManyToManyField
            if framework not in system.frameworks.all():
                system.frameworks.add(framework)
                messages.success(request, f'Framework "{framework.name}" assigned to system "{system.name}"')
            else:
                messages.info(request, f'Framework "{framework.name}" is already assigned to system "{system.name}"')
            return redirect('compliance:dashboard_view')
        else:
            messages.error(request, 'Error assigning framework. Please check your selection.')

    # Handle framework removal POST request
    elif request.method == 'POST' and 'remove_framework' in request.POST:
        system_id = request.POST.get('system_id')
        framework_id = request.POST.get('framework_id')
        system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)
        framework = get_object_or_404(Framework, id=framework_id)

        # Remove framework from system using ManyToManyField
        system.frameworks.remove(framework)
        # Also remove related control assignments
        SystemControlStatus.objects.filter(system=system, framework=framework).delete()

        messages.success(request, f'Framework "{framework.name}" removed from system "{system.name}"')
        return redirect('compliance:dashboard_view')

    # Handle control assignment POST request
    elif request.method == 'POST' and 'assign_controls' in request.POST:
        system_id = request.POST.get('system_id')
        framework_id = request.POST.get('framework_id')
        system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)
        framework = get_object_or_404(Framework, id=framework_id)

        form = ControlAssignmentForm(request.POST, framework=framework)
        if form.is_valid():
            controls = form.cleaned_data['controls']
            controller = form.cleaned_data['controller']
            previously_implemented = form.cleaned_data['previously_implemented']

            assigned_count = 0
            for control in controls:
                system_control, created = SystemControlStatus.objects.get_or_create(
                    system=system,
                    framework=framework,
                    control=control,
                    defaults={
                        'controller': controller,
                        'previously_implemented': previously_implemented,
                        'status': 'under_review',
                        'implementation_status': 'not_started'
                    }
                )

                if not created:
                    # Update existing assignment
                    system_control.controller = controller
                    system_control.previously_implemented = previously_implemented
                    system_control.save()

                assigned_count += 1

                # Create notification if controller assigned
                if controller:
                    Notification.objects.create(
                        user=controller.user,
                        notification_type='control_assigned',
                        title='New Control Assigned',
                        message=f'You have been assigned control {control.control_id} for system {system.name}',
                        system_control_status=system_control
                    )

            messages.success(request, f'Successfully assigned {assigned_count} controls')
            return redirect('compliance:dashboard_view')
        else:
            messages.error(request, 'Error assigning controls. Please check your selection.')

    # Get controller profile
    try:
        controller_profile = ControllerProfile.objects.get(user=request.user)
        assigned_controls = SystemControlStatus.objects.filter(
            controller=controller_profile
        ).select_related('system', 'framework', 'control', 'controller')
    except ControllerProfile.DoesNotExist:
        assigned_controls = SystemControlStatus.objects.none()

    # Build framework data - Fixed to properly handle all cases
    framework_data = []

    # Get all systems and ensure they're all displayed
    for system in user_systems:
        system_controls = SystemControlStatus.objects.filter(system=system).select_related('framework', 'control', 'controller__user')

        if system_controls.exists():
            # System has controls - add each control as a separate row
            for control_status in system_controls:
                framework_data.append({
                    'system_id': system.id,
                    'system_name': system.name,
                    'organization_name': system.organization.name if system.organization else '',
                    'framework_id': control_status.framework.id,
                    'framework_name': control_status.framework.name,
                    'controls': control_status.control.control_id,
                    'status': control_status.implementation_status,  # Fixed: use implementation_status
                    'progress': control_status.progress,
                    'control_status_id': control_status.id,
                    'controller': control_status.controller,
                    'deadline': control_status.deadline if hasattr(control_status, 'deadline') else None,
                    'previously_implemented': control_status.previously_implemented if hasattr(control_status, 'previously_implemented') else False,
                })
        else:
            # System has no controls - ALWAYS add it to ensure visibility
            system_frameworks = system.frameworks.all()
            if system_frameworks.exists():
                # Show each framework with "No Controls" status
                for framework in system_frameworks:
                    framework_data.append({
                        'system_id': system.id,
                        'system_name': system.name,
                        'organization_name': system.organization.name if system.organization else '',
                        'framework_id': framework.id,
                        'framework_name': framework.name,
                        'controls': 'No Controls Assigned',
                        'status': 'not_configured',
                        'progress': 0,
                        'control_status_id': None,
                        'controller': None,
                        'deadline': None,
                        'previously_implemented': False,
                    })
            else:
                # System has no frameworks at all - still show it
                framework_data.append({
                    'system_id': system.id,
                    'system_name': system.name,
                    'organization_name': system.organization.name if system.organization else '',
                    'framework_id': None,
                    'framework_name': 'No Framework Assigned',
                    'controls': 'No Controls',
                    'status': 'not_configured',
                    'progress': 0,
                    'control_status_id': None,
                    'controller': None,
                    'deadline': None,
                    'previously_implemented': False,
                })

    # Statistics - FIXED to count properly and update when systems/controls change
    total_systems = user_systems.count()

    # Get ALL controls for systems owned by the user
    all_user_controls = SystemControlStatus.objects.filter(
        system__owner=request.user
    ).select_related('system', 'framework', 'control', 'controller')

    total_assigned_controls = all_user_controls.count()
    compliant_controls = all_user_controls.filter(implementation_status='compliant').count()
    non_compliant_controls = all_user_controls.filter(implementation_status='non_compliant').count()
    partial_count = all_user_controls.filter(implementation_status='partially_compliant').count()
    pending_controls = all_user_controls.filter(implementation_status__in=['under_review', 'in_progress']).count()

    upcoming_deadlines = all_user_controls.filter(
        deadline__isnull=False,
        deadline__gte=timezone.now(),
        deadline__lte=timezone.now() + timezone.timedelta(days=7)
    ).order_by('deadline')[:5]

    overdue_items = all_user_controls.filter(
        deadline__isnull=False,
        deadline__lt=timezone.now(),
        status__in=['non_compliant', 'partially_compliant', 'under_review']
    ).order_by('deadline')[:5]

    recent_notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    # NEW: Get active frameworks for user systems
    active_frameworks = Framework.objects.filter(
        information_systems__in=user_systems
    ).distinct()

    # NEW: Calculate compliance journey progress
    journey_steps = {
        'diagnostic': {
            'completed': user_systems.exists(),
            'status': 'completed' if user_systems.exists() else 'pending',
            'progress': 100 if user_systems.exists() else 0
        },
        'gap_analysis': {
            'completed': total_assigned_controls > 0,
            'status': 'in_progress' if total_assigned_controls > 0 and compliant_controls < total_assigned_controls else 'completed' if total_assigned_controls > 0 else 'pending',
            'progress': (compliant_controls / total_assigned_controls * 100) if total_assigned_controls > 0 else 0
        },
        'recommendations': {
            'completed': compliant_controls > 0,
            'status': 'in_progress' if compliant_controls > 0 else 'pending',
            'progress': (compliant_controls / total_assigned_controls * 100) if total_assigned_controls > 0 else 0
        },
        're_evaluation': {
            'completed': compliant_controls >= total_assigned_controls * 0.8,  # 80% compliance threshold
            'status': 'completed' if compliant_controls >= total_assigned_controls * 0.8 else 'in_progress' if compliant_controls > 0 else 'pending',
            'progress': (compliant_controls / total_assigned_controls * 100) if total_assigned_controls > 0 else 0
        },
        'report_generation': {
            'completed': compliant_controls >= total_assigned_controls * 0.9,  # 90% compliance threshold
            'status': 'completed' if compliant_controls >= total_assigned_controls * 0.9 else 'pending',
            'progress': (compliant_controls / total_assigned_controls * 100) if total_assigned_controls > 0 else 0
        }
    }

    # NEW: Session parameters
    session_parameters = {
        'last_login': request.user.last_login,
        'session_start': timezone.now(),
        'active_frameworks_count': active_frameworks.count(),
        'active_systems_count': user_systems.count(),
        'total_controls': total_assigned_controls,
        'compliance_rate': (compliant_controls / total_assigned_controls * 100) if total_assigned_controls > 0 else 0
    }

    # NEW: Get questionnaire results if available
    try:
        latest_questionnaire = QuestionnaireResult.objects.filter(user=request.user).first()
    except:
        latest_questionnaire = None

    # Pagination
    paginator = Paginator(framework_data, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Prepare forms for each system
    framework_forms = {}
    control_forms = {}
    system_frameworks = {}

    for system in user_systems:
        # Framework assignment form
        framework_forms[system.id] = FrameworkAssignmentForm(system=system)

        # Get assigned frameworks for this system using ManyToManyField
        assigned_frameworks = system.frameworks.all()
        system_frameworks[system.id] = assigned_frameworks

        # Control assignment forms for each framework
        control_forms[system.id] = {}
        for framework in assigned_frameworks:
            control_forms[system.id][framework.id] = ControlAssignmentForm(
                framework=framework,
                prefix=f'system_{system.id}_framework_{framework.id}'
            )

    # Get CSRF token
    csrf_token = get_token(request)

    context = {
        'systems': user_systems,
        'user_systems': user_systems,  # Add explicit user_systems for template
        'frameworks': frameworks,  # Add frameworks to context
        'active_frameworks': active_frameworks,  # NEW: Active frameworks for the user
        'framework_data': framework_data,
        'total_systems': total_systems,
        'total_assigned_controls': total_assigned_controls,
        'compliant_controls': compliant_controls,
        'non_compliant_controls': non_compliant_controls,
        'partial_count': partial_count,
        'pending_controls': pending_controls,
        'upcoming_deadlines': upcoming_deadlines,
        'overdue_items': overdue_items,
        'recent_notifications': recent_notifications,
        'page_obj': page_obj,
        # New additions for framework and control assignment
        'framework_forms': framework_forms,
        'control_forms': control_forms,
        'system_frameworks': system_frameworks,
        # NEW: Session and journey data
        'session_parameters': session_parameters,
        'journey_steps': journey_steps,
        'latest_questionnaire': latest_questionnaire,
        'djangoData': {
            'csrfToken': csrf_token,
            'notificationsPartialUrl': '/api/notifications/partial/',
            'controllerOptionsUrl': '/api/controllers/__ID__/',
            'assignControllerUrl': '/api/assign/controller/__ID__/',
            'implementationStatusUrl': '/api/implementation/__ID__/',
            'evidenceRequirementsUrl': '/api/evidence/requirements/__ID__/',
            'uploadEvidenceUrl': '/api/upload/evidence/__ID__/',
            'editUrl': '/api/edit/framework/__ID__/',
            'deleteUrl': '/api/delete/framework/__ID__/',
            'addSystemUrl': '/api/add/system/',
            'refreshUrl': '/api/refresh/',
            'frameworkDetailsUrl': '/api/framework/details/__ID__/',
            'approveEvidenceUrl': '/api/approve/evidence/__ID__/',
            'rejectEvidenceUrl': '/api/reject/evidence/__ID__/',
            'compliant_controls': compliant_controls,
            'non_compliant_controls': non_compliant_controls,
            'partial_count': partial_count,
            'pending_controls': pending_controls,
        }
    }

    return render(request, 'compliance/dashboard_fixed.html', context)
# views.py
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json





from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def api_login_view(request):
    if request.method == "POST":
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
            else:
                username = request.POST.get('username')
                password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return JsonResponse({
                        'success': True,
                        'message': 'Login successful',
                        'user_id': user.id,
                        'username': user.username
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Account is disabled'
                    }, status=403)
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid credentials'
                }, status=401)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'success': False,
        'message': 'Only POST method allowed'
    }, status=405)


@csrf_exempt
# Alternative: AJAX API endpoint for framework assignment (if you prefer AJAX)
@csrf_exempt
@login_required
def assign_framework_api(request, system_id):
    """API endpoint for assigning framework to system via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

    try:
        data = json.loads(request.body)
        framework_id = data.get('framework_id')

        if not framework_id:
            return JsonResponse({'error': 'Framework ID is required'}, status=400)

        framework = get_object_or_404(Framework, id=framework_id)

        # Check if framework is already assigned
        if system.frameworks.filter(id=framework_id).exists():
            return JsonResponse({'error': 'Framework already assigned to this system'}, status=400)

        system.frameworks.add(framework)

        return JsonResponse({
            'success': True,
            'message': f'Framework "{framework.name}" assigned to system "{system.name}"',
            'framework': {
                'id': framework.id,
                'name': framework.name
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# API endpoint for removing framework from system
@csrf_exempt
@login_required
def remove_framework_api(request, system_id, framework_id):
    """API endpoint for removing framework from system"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)
    framework = get_object_or_404(Framework, id=framework_id)

    try:
        system.frameworks.remove(framework)

        return JsonResponse({
            'success': True,
            'message': f'Framework "{framework.name}" removed from system "{system.name}"'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def add_system(request):
    """Create a new information system with framework, controls, and controller assignment"""
    if request.method == 'POST':
        try:
            # Get basic system information
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            organization_id = request.POST.get('organization')

            # Get framework and control data
            framework_id = request.POST.get('framework')
            selected_controls = request.POST.getlist('controls')
            previously_implemented_value = request.POST.get('previously_implemented')
            previously_implemented = previously_implemented_value == 'yes'  # Convert "yes"/"no" to boolean

            # Get controller data
            controller_name = request.POST.get('controller_name', '').strip()
            job_title = request.POST.get('job_title', '').strip()
            employee_number = request.POST.get('employee_number', '').strip()
            email = request.POST.get('email', '').strip()
            assign_controller = request.POST.get('assign_controller') == 'on'

            # Validate required fields
            if not name:
                return JsonResponse({'success': False, 'message': 'System name is required'})

            if InformationSystem.objects.filter(name=name).exists():
                return JsonResponse({'success': False, 'message': 'A system with this name already exists'})

            if not framework_id:
                return JsonResponse({'success': False, 'message': 'Framework selection is required'})

            if not selected_controls:
                return JsonResponse({'success': False, 'message': 'At least one control must be selected'})

            # Validate controller data if assignment is requested
            if assign_controller and any(selected_controls):
                if not all([controller_name, job_title, employee_number, email]):
                    return JsonResponse({
                        'success': False,
                        'message': 'All controller fields are required when assigning a controller'
                    })

                # Validate email format
                try:
                    from django.core.validators import validate_email
                    validate_email(email)
                except ValidationError:
                    return JsonResponse({'success': False, 'message': 'Please enter a valid email address'})

            with transaction.atomic():
                # Create the system
                system = InformationSystem.objects.create(
                    name=name,
                    description=description,
                    owner=request.user
                )

                # Set organization if provided
                if organization_id:
                    try:
                        from .models import Organization
                        organization = Organization.objects.get(id=organization_id)
                        system.organization = organization
                        system.save()
                    except Organization.DoesNotExist:
                        pass

                # Get framework and assign it to system
                framework = get_object_or_404(Framework, id=framework_id)
                system.frameworks.add(framework)

                # Create or get controller if assignment is requested
                controller = None
                if assign_controller and controller_name:
                    # Create or get user first
                    user, user_created = User.objects.get_or_create(
                        email=email,
                        defaults={
                            'username': email,  # Use email as username
                            'first_name': controller_name.split()[0] if controller_name.split() else controller_name,
                            'last_name': ' '.join(controller_name.split()[1:]) if len(controller_name.split()) > 1 else '',
                            'is_active': True
                        }
                    )

                    # Update user info if needed
                    if not user_created:
                        user.first_name = controller_name.split()[0] if controller_name.split() else controller_name
                        user.last_name = ' '.join(controller_name.split()[1:]) if len(controller_name.split()) > 1 else ''
                        user.save()

                    # Create or get controller profile
                    controller, created = ControllerProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'department': job_title,  # Use job_title as department
                            'expertise_areas': f'Employee #{employee_number}',  # Store employee number in expertise
                            'is_active': True,
                        }
                    )

                    # Update existing controller info if needed
                    if not created:
                        controller.department = job_title
                        controller.expertise_areas = f'Employee #{employee_number}'
                        controller.save()

                # Create control assignments
                assigned_count = 0
                for control_id in selected_controls:
                    try:
                        control = Control.objects.get(id=control_id, framework=framework)

                        # Create system control status
                        system_control = SystemControlStatus.objects.create(
                            system=system,
                            framework=framework,
                            control=control,
                            controller=controller,
                            previously_implemented=previously_implemented,  # Now 'yes' or 'no'
                            status='under_review',
                            implementation_status='not_started'
                        )

                        assigned_count += 1

                        # Create notification if controller is assigned
                        if controller:
                            Notification.objects.create(
                                user=controller.user if hasattr(controller, 'user') else request.user,
                                notification_type='control_assigned',
                                title='New Control Assigned',
                                message=f'Control {control.control_id} assigned for system {system.name}',
                                system_control_status=system_control
                            )

                    except Control.DoesNotExist:
                        continue

                messages.success(request,
                    f'System "{system.name}" created successfully with {assigned_count} controls assigned!')

                return JsonResponse({
                    'success': True,
                    'system': {
                        'id': system.id,
                        'name': system.name,
                        'description': system.description,
                        'framework': framework.name,
                        'controls_count': assigned_count,
                        'controller': controller.user.get_full_name() if controller else None  # Fixed the error here
                    }
                })

        except Exception as e:
            logger.error(f"Error creating system: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error creating system: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
def edit_system(request, system_id):
    """
    Enhanced system editing with comprehensive audit trail, security impact assessment,
    and intelligent compliance recommendations - Enterprise Security Management Innovation
    """
    import json
    import re
    import logging
    from django.db import transaction
    from django.core.serializers.json import DjangoJSONEncoder
    from django.utils import timezone
    from datetime import datetime, timedelta

    logger = logging.getLogger(__name__)
    system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

    # Handle GET request - render the edit modal template
    if request.method == 'GET':
        # Get all organizations for the dropdown
        from .models import Organization
        organizations = Organization.objects.all()

        # Get all frameworks for the dropdown
        frameworks = Framework.objects.all()

        # Get system's current frameworks and controls for context
        system_frameworks = system.frameworks.all()
        system_controls = SystemControlStatus.objects.filter(system=system).select_related('control', 'framework')

        # Calculate current compliance metrics
        total_controls = system_controls.count()
        compliant_controls = system_controls.filter(implementation_status='compliant').count()
        compliance_rate = (compliant_controls / total_controls * 100) if total_controls > 0 else 0

        context = {
            'system': system,
            'organizations': organizations,
            'frameworks': frameworks,  # Add frameworks to context
            'system_frameworks': system_frameworks,
            'total_controls': total_controls,
            'compliant_controls': compliant_controls,
            'compliance_rate': round(compliance_rate, 1),
            'csrf_token': get_token(request)
        }

        return render(request, 'compliance/edit_system_modal.html', context)

    # Handle POST request - process the form submission
    elif request.method == 'POST':
        try:
            # 1. Store original system state for comprehensive audit trail
            original_state = {
                'name': system.name,
                'description': system.description,
                'organization_id': system.organization.id if system.organization else None,
                'organization_name': system.organization.name if system.organization else 'No Organization',
                'frameworks': list(system.frameworks.values_list('id', 'name')),
                'framework_count': system.frameworks.count(),
                'total_controls': SystemControlStatus.objects.filter(system=system).count(),
                'compliant_controls': SystemControlStatus.objects.filter(
                    system=system, implementation_status='compliant'
                ).count()
            }

            # 2. Enhanced validation and security checks
            validation_errors = []
            security_warnings = []

            # Advanced Name Validation with Security Context
            new_name = request.POST.get('name', '').strip()
            if not new_name:
                validation_errors.append('System name is required')
            elif len(new_name) < 3:
                validation_errors.append('System name must be at least 3 characters')
            elif len(new_name) > 255:
                validation_errors.append('System name must not exceed 255 characters')
            elif InformationSystem.objects.filter(name=new_name).exclude(id=system_id).exists():
                validation_errors.append('A system with this name already exists')

            # Security pattern validation
            if re.search(r'[<>"\'\(\)\{\}\[\]\\\/\*\?\|]', new_name):
                security_warnings.append('System name contains potentially unsafe characters')

            # Description validation
            new_description = request.POST.get('description', '').strip()
            if len(new_description) > 2000:
                validation_errors.append('Description must not exceed 2000 characters')

            # 3. Organization Change Impact Assessment
            new_org_id = request.POST.get('organization')
            organization_change_impact = None

            if str(new_org_id) != str(original_state['organization_id']):
                if new_org_id:
                    try:
                        from .models import Organization
                        new_org = Organization.objects.get(id=new_org_id)
                        organization_change_impact = {
                            'type': 'organization_change',
                            'from': original_state['organization_name'],
                            'to': new_org.name,
                            'risk_level': 'medium',
                            'affected_controls': original_state['total_controls'],
                            'recommendations': [
                                'Review organizational policies alignment',
                                'Update control ownership assignments'
                            ]
                        }
                    except:
                        validation_errors.append('Selected organization does not exist')
                else:
                    organization_change_impact = {
                        'type': 'organization_removal',
                        'from': original_state['organization_name'],
                        'to': 'No Organization',
                        'risk_level': 'high',
                        'warning': 'Removing organization may affect compliance scope'
                    }

            # Return validation errors if any
            if validation_errors:
                return JsonResponse({
                    'success': False,
                    'validation_errors': validation_errors,
                    'security_warnings': security_warnings
                })

            # 4. Intelligent Change Recommendations
            change_recommendations = []
            current_compliance_rate = (original_state['compliant_controls'] /
                                     original_state['total_controls'] * 100) if original_state['total_controls'] > 0 else 0

            if current_compliance_rate < 50:
                change_recommendations.append({
                    'type': 'compliance_improvement',
                    'priority': 'high',
                    'title': 'Low Compliance Rate Detected',
                    'description': f'Current compliance rate is {current_compliance_rate:.1f}%. Consider prioritizing critical controls.',
                    'action_items': [
                        'Review high-risk controls first',
                        'Assign dedicated controllers',
                        'Set aggressive deadlines for critical controls'
                    ]
                })

            if 'production' in new_name.lower() or 'prod' in new_name.lower():
                change_recommendations.append({
                    'type': 'production_security',
                    'priority': 'high',
                    'title': 'Production System Security Enhancement',
                    'description': 'Production system detected - enhanced security measures recommended',
                    'action_items': [
                        'Implement enhanced monitoring',
                        'Set up real-time alerting',
                        'Enable change management controls'
                    ]
                })

            # 5. Risk Scoring Algorithm
            risk_score = 0
            if organization_change_impact:
                risk_levels = {'high': 30, 'medium': 15, 'low': 5}
                risk_score += risk_levels.get(organization_change_impact.get('risk_level', 'low'), 5)

            if current_compliance_rate < 30:
                risk_score += 25
            elif current_compliance_rate < 50:
                risk_score += 15
            elif current_compliance_rate < 75:
                risk_score += 5

            if len(security_warnings) > 0:
                risk_score += len(security_warnings) * 10

            risk_score = min(risk_score, 100)

            # 6. Approval Requirements
            requires_approval = risk_score >= 50 or (organization_change_impact and organization_change_impact.get('risk_level') == 'high')

            # 7. Execute Changes with Transaction Support
            with transaction.atomic():
                # Create audit log entry
                audit_entry = {
                    'timestamp': timezone.now().isoformat(),
                    'change_id': f"SYS_EDIT_{system.id}_{int(timezone.now().timestamp())}",
                    'user': {
                        'id': request.user.id,
                        'username': request.user.username,
                        'email': request.user.email
                    },
                    'action': 'system_edit_enhanced',
                    'system_id': system.id,
                    'original_state': original_state,
                    'changes': {
                        'name': {'from': original_state['name'], 'to': new_name},
                        'description': {'from': original_state['description'], 'to': new_description},
                        'organization': organization_change_impact
                    },
                    'risk_assessment': {
                        'risk_score': risk_score,
                        'risk_level': 'high' if risk_score >= 70 else 'medium' if risk_score >= 40 else 'low',
                        'requires_approval': requires_approval,
                        'security_warnings': security_warnings
                    },
                    'recommendations': change_recommendations,
                    'client_info': {
                        'ip_address': request.META.get('REMOTE_ADDR'),
                        'user_agent': request.META.get('HTTP_USER_AGENT'),
                        'session_key': request.session.session_key
                    }
                }

                # Update system
                system.name = new_name
                system.description = new_description

                if new_org_id:
                    from .models import Organization
                    system.organization = Organization.objects.get(id=new_org_id)
                else:
                    system.organization = None

                system.save()

                # Store audit log in session
                if 'audit_logs' not in request.session:
                    request.session['audit_logs'] = []

                request.session['audit_logs'].append(audit_entry)
                request.session.modified = True

                # Generate post-change actions
                post_change_actions = []

                if organization_change_impact:
                    post_change_actions.append({
                        'type': 'compliance_revalidation',
                        'priority': 'medium',
                        'title': 'Revalidate Compliance Scope',
                        'description': 'Organization change may affect compliance scope',
                        'estimated_effort': '4-6 hours',
                        'next_steps': [
                            'Review organizational policies',
                            'Update control implementations',
                            'Verify regulatory requirements'
                        ]
                    })

                # Calculate updated metrics
                updated_metrics = {
                    'total_controls': original_state['total_controls'],
                    'compliant_controls': original_state['compliant_controls'],
                    'compliance_rate': current_compliance_rate,
                    'frameworks_count': system.frameworks.count(),
                    'last_updated': timezone.now().isoformat()
                }

                # Success response with comprehensive data
                return JsonResponse({
                    'success': True,
                    'system': {
                        'id': system.id,
                        'name': system.name,
                        'description': system.description,
                        'organization': system.organization.name if system.organization else None,
                        'updated_at': timezone.now().isoformat()
                    },
                    'audit_info': {
                        'change_id': audit_entry['change_id'],
                        'risk_score': risk_score,
                        'risk_level': audit_entry['risk_assessment']['risk_level'],
                        'requires_approval': requires_approval
                    },
                    'impact_summary': {
                        'organization_changed': organization_change_impact is not None,
                        'compliance_rate': current_compliance_rate,
                        'total_controls': original_state['total_controls']
                    },
                    'intelligence': {
                        'recommendations': change_recommendations,
                        'post_change_actions': post_change_actions,
                        'next_review_date': (timezone.now() + timedelta(days=30)).isoformat()
                    },
                    'security': {
                        'warnings': security_warnings,
                        'security_score': max(0, 100 - len(security_warnings) * 10)
                    },
                    'metrics': updated_metrics
                })

        except Exception as e:
            # Enhanced error logging
            error_context = {
                'error_id': f"ERR_{int(timezone.now().timestamp())}",
                'user_id': request.user.id,
                'system_id': system_id,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }

            logger.error(f"Enhanced system edit failed: {json.dumps(error_context, cls=DjangoJSONEncoder)}")

            return JsonResponse({
                'success': False,
                'error': 'System update failed',
                'error_id': error_context['error_id'],
                'support_message': f'Contact support with error ID: {error_context["error_id"]}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method',
        'timestamp': timezone.now().isoformat()
    })
@login_required
@require_POST
def delete_system(request, system_id):
    """Delete a system"""
    system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)
    system.delete()
    return JsonResponse({'success': True})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json


@csrf_exempt
@login_required
def assign_controls_api(request, system_id):
    """API endpoint for assigning controls to a system"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        selected_controls = data.get('controls', [])

        if not selected_controls:
            return JsonResponse({'error': 'No controls provided'}, status=400)

        assigned_controls = []
        errors = []

        with transaction.atomic():
            for control_data in selected_controls:
                control_id = control_data.get('control_id')
                controller_id = control_data.get('controller_id')
                previously_implemented = control_data.get('previously_implemented', False)

                if not control_id:
                    errors.append('Missing control_id in request data')
                    continue

                try:
                    control = Control.objects.get(id=control_id)
                except Control.DoesNotExist:
                    errors.append(f'Control with id {control_id} not found')
                    continue

                # Get or create system control status
                system_control, created = SystemControlStatus.objects.get_or_create(
                    system=system,
                    framework=control.framework,
                    control=control,
                    defaults={
                        'controller_id': controller_id if controller_id else None,
                        'previously_implemented': previously_implemented,
                        'status': 'under_review',
                        'implementation_status': 'not_started'
                    }
                )

                if not created:
                    # Update existing assignment
                    system_control.controller_id = controller_id if controller_id else None
                    system_control.previously_implemented = previously_implemented
                    system_control.save()

                # Create notification if controller assigned
                if controller_id:
                    try:
                        controller = ControllerProfile.objects.get(id=controller_id)
                        Notification.objects.create(
                            user=controller.user,
                            notification_type='control_assigned',
                            title='New Control Assigned',
                            message=f'You have been assigned control {control.control_id} for system {system.name}',
                            system_control_status=system_control
                        )
                    except ControllerProfile.DoesNotExist:
                        errors.append(f'Controller with id {controller_id} not found')

                assigned_controls.append({
                    'control_id': control.id,
                    'control_name': control.control_id,
                    'controller_id': controller_id,
                    'previously_implemented': previously_implemented,
                    'status': 'assigned'
                })

        response_data = {
            'success': True,
            'message': f'Successfully assigned {len(assigned_controls)} controls',
            'system_id': system.id,
            'assigned_controls': assigned_controls
        }

        if errors:
            response_data['warnings'] = errors

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def list_controls_api(request, system_id):
    """List all available controls for a system"""
    try:
        system = get_object_or_404(InformationSystem, id=system_id)

        # Get available controls for this system
        available_controls = Control.objects.filter(
            framework__in=system.frameworks.all()
        ).select_related('framework', 'category')

        controls_data = []
        for control in available_controls:
            controls_data.append({
                'id': control.id,
                'control_id': control.control_id,
                'title': control.title,
                'framework': control.framework.name,
                'category': control.category.name if control.category else None
            })

        return JsonResponse({
            'success': True,
            'system_id': system_id,
            'system_name': system.name,
            'total_controls': len(controls_data),
            'controls': controls_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
@login_required
def system_detail(request, system_id):
    """Detailed view of a system with all its controls"""
    system = get_object_or_404(InformationSystem, id=system_id)
    if system.owner != request.user and not SystemControlStatus.objects.filter(
        system=system, controller__user=request.user
    ).exists():
        messages.error(request, 'You do not have permission to view this system.')
        return redirect('dashboard_view')

    control_statuses = SystemControlStatus.objects.filter(
        system=system
    ).select_related('control', 'framework', 'controller__user').order_by('control__control_id')

    statuses_by_category = {}
    for status in control_statuses:
        category_path = status.control.category.get_full_path()
        if category_path not in statuses_by_category:
            statuses_by_category[category_path] = []
        statuses_by_category[category_path].append(status)

    total_controls = control_statuses.count()
    compliant_count = control_statuses.filter(status='compliant').count()
    non_compliant_count = control_statuses.filter(status='non_compliant').count()
    partial_count = control_statuses.filter(status='partially_compliant').count()
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
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Check permissions - handle None controller properly
    has_permission = False
    if control_status.system.owner == request.user:
        has_permission = True
    elif control_status.controller and control_status.controller.user == request.user:
        has_permission = True

    if not has_permission:
        messages.error(request, 'You do not have permission to view this control.')
        return redirect('compliance:dashboard_view')

    evidence_files = Evidence.objects.filter(
        system_control_status=control_status  # Fixed field name
    ).order_by('-uploaded_at')

    reviews = EvidenceReview.objects.filter(
        evidence__system_control_status=control_status  # Fixed field name
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

    # Check permissions - handle None controller properly
    has_permission = False
    if control_status.controller and hasattr(control_status.controller, 'user') and control_status.controller.user == request.user:
        has_permission = True
    elif hasattr(control_status.system, 'owner') and control_status.system.owner == request.user:
        has_permission = True

    if not has_permission:
        messages.error(request, 'You are not authorized to upload evidence for this control.')
        return redirect('control_detail', control_status_id=control_status_id)

    if request.method == 'POST':
        form = EvidenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.system_control_status = control_status
            evidence.uploaded_by = request.user
            evidence.save()

            # Create notification if system owner exists
            if hasattr(control_status.system, 'owner') and control_status.system.owner:
                Notification.objects.create(
                    user=control_status.system.owner,
                    notification_type='evidence_uploaded',
                    title='Evidence Uploaded',
                    message=f'Evidence uploaded for control {control_status.control.control_id} in system {control_status.system.name}',
                    system_control_status=control_status
                )

            messages.success(request, 'Evidence uploaded successfully! Status updated to pending review.')
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

    # Fixed field name
    if evidence.system_control_status.system.owner != request.user:
        messages.error(request, 'You are not authorized to review this evidence.')
        return redirect('compliance:dashboard_view')

    if request.method == 'POST':
        form = EvidenceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.evidence = evidence
            review.reviewer = request.user
            review.save()

            # Update evidence record
            evidence.approval_status = review.status
            evidence.reviewer_feedback = review.feedback
            evidence.reviewed_by = request.user
            evidence.reviewed_at = timezone.now()
            evidence.save() # This will trigger update_progress_on_evidence_upload()
            evidence.reviewed = True
            evidence.save()


            # Create notification
            notification_type = 'evidence_approved' if review.status == 'approved' else 'evidence_rejected'
            Notification.objects.create(
                user=evidence.system_control_status.controller.user,  # Fixed field name
                notification_type=notification_type,
                title=f'Evidence {review.status.title()}',
                message=f'Your evidence for control {evidence.system_control_status.control.control_id} has been {review.status}',
                system_control_status=evidence.system_control_status  # Fixed field name
            )

            messages.success(request, 'Evidence review completed!')
            return redirect('control_detail', control_status_id=evidence.system_control_status.id)  # Fixed field name
    else:
        form = EvidenceReviewForm()

    context = {
        'form': form,
        'evidence': evidence,
    }

    return render(request, 'compliance/review_evidence.html', context)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Control # Import your models

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import SystemControlStatus

@login_required
def my_assignments(request):
    """My assignments view with dark mode styling - FIXED to show all user assignments"""
    from django.db.models import Q

    # Get user's assignments through multiple paths:
    # 1. Controls where user is assigned as controller
    # 2. Controls for systems owned by the user
    # 3. Controls that need the user's attention
    assignments = SystemControlStatus.objects.filter(
        Q(controller__user=request.user) |  # User is assigned as controller
        Q(system__owner=request.user)       # User owns the system
    ).select_related(
        'control',
        'system',
        'control__category',
        'control__framework',
        'controller__user'
    ).distinct().order_by('-last_updated')

    # Calculate statistics
    compliant_count = assignments.filter(status='compliant').count()
    pending_count = assignments.filter(status='under_review').count()
    non_compliant_count = assignments.filter(status='non_compliant').count()
    partially_compliant_count = assignments.filter(status='partially_compliant').count()

    # Calculate overdue assignments
    today = timezone.now()
    overdue_count = assignments.filter(
        deadline__lt=today,
        status__in=['under_review', 'partially_compliant', 'non_compliant']
    ).count()

    # Get recent evidence uploads for user's assignments
    recent_evidence = Evidence.objects.filter(
        system_control_status__in=assignments
    ).order_by('-uploaded_at')[:5]

    context = {
        'assignments': assignments,
        'compliant_count': compliant_count,
        'pending_count': pending_count,
        'non_compliant_count': non_compliant_count,
        'partially_compliant_count': partially_compliant_count,
        'overdue_count': overdue_count,
        'recent_evidence': recent_evidence,
        'today': today,
        'total_assignments': assignments.count(),
    }

    return render(request, 'compliance/my_assignments.html', context)
@login_required
def update_control_status(request, control_status_id):
    """Update control implementation status"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)
    if control_status.controller.user != request.user:
        messages.error(request, 'You are not authorized to update this control.')
        return redirect('compliance:dashboard_view')

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
    """Enhanced notifications view with priority filtering and deadline alerts"""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('system_control_status__system', 'system_control_status__control').order_by('-created_at')

    # Filter by priority if requested
    priority_filter = request.GET.get('priority')
    if priority_filter:
        notifications = notifications.filter(priority=priority_filter)

    # Filter by notification type if requested
    type_filter = request.GET.get('type')
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)

    # Mark as read if requested
    if request.GET.get('mark_read'):
        notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')

    # Get counts for different priorities
    priority_counts = {
        'urgent': notifications.filter(priority='urgent', is_read=False).count(),
        'high': notifications.filter(priority='high', is_read=False).count(),
        'medium': notifications.filter(priority='medium', is_read=False).count(),
        'low': notifications.filter(priority='low', is_read=False).count(),
    }

    # Get counts for different types
    type_counts = {
        'deadline_overdue': notifications.filter(notification_type='deadline_overdue', is_read=False).count(),
        'deadline_warning': notifications.filter(notification_type='deadline_warning', is_read=False).count(),
        'evidence_uploaded': notifications.filter(notification_type='evidence_uploaded', is_read=False).count(),
        'control_assigned': notifications.filter(notification_type='control_assigned', is_read=False).count(),
    }

    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'priority_counts': priority_counts,
        'type_counts': type_counts,
        'current_priority_filter': priority_filter,
        'current_type_filter': type_filter,
        'total_unread': notifications.filter(is_read=False).count(),
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
def notifications_partial(request):
    """AJAX endpoint for recent notifications"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'notification_type': n.notification_type,
        'created_at': n.created_at.isoformat()
    } for n in notifications]
    return JsonResponse({'notifications': data})

@login_required
def deadline_countdown(request, control_status_id):
    """AJAX endpoint for deadline countdown"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)
    if control_status.system.owner != request.user and control_status.controller.user != request.user:
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
            'is_overdue': False
        }
    else:
        countdown_data = {
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'is_overdue': control_status.is_deadline_passed
        }
    return JsonResponse(countdown_data)

@login_required
@require_POST
def edit_framework(request, pk):
    """Edit a framework's control status"""
    control_status = get_object_or_404(SystemControlStatus, id=pk)
    if control_status.system.owner != request.user and control_status.controller.user != request.user:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    form = SystemControlStatusForm(request.POST, request.FILES, instance=control_status)
    if form.is_valid():
        control_status = form.save()
        return JsonResponse({
            'success': True,
            'framework': {
                'id': control_status.id,
                'name': control_status.framework.name,
                'controls': control_status.control.control_id,
                'status': control_status.status,
                'progress': control_status.progress
            }
        })
    return JsonResponse({'success': False, 'message': form.errors.as_json()})

@login_required
@require_POST
def delete_framework(request, pk):
    """Delete a framework's control status"""
    control_status = get_object_or_404(SystemControlStatus, id=pk)
    if control_status.system.owner != request.user:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    control_status.delete()
    return JsonResponse({'success': True})

@login_required
def refresh_frameworks(request):
    """Refresh framework data"""
    systems = InformationSystem.objects.filter(owner=request.user)
    framework_data = []
    for system in systems:
        for control_status in SystemControlStatus.objects.filter(system=system).select_related('framework', 'control'):
            framework_data.append({
                'id': control_status.id,
                'system_id': system.id,
                'system_name': system.name,
                'framework_id': control_status.framework.id,
                'framework_name': control_status.framework.name,
                'controls': control_status.control.control_id,
                'status': control_status.status,
                'progress': control_status.progress
            })
    return JsonResponse({'success': True, 'systems': [
        {'id': s.id, 'name': s.name, 'description': s.description} for s in systems
    ]})

@login_required
def framework_details(request, pk):
    """Detailed view of a framework's control status"""
    control_status = get_object_or_404(SystemControlStatus, id=pk)
    if control_status.system.owner != request.user and control_status.controller.user != request.user:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    data = {
        'id': control_status.id,
        'system': control_status.system.name,
        'framework': control_status.framework.name,
        'control': control_status.control.control_id,
        'status': control_status.status,
        'progress': control_status.progress,
        'deadline': control_status.deadline.isoformat() if control_status.deadline else None,
        'evidence': [{
            'id': e.id,
            'file': e.file.url,
            'uploaded_at': e.uploaded_at.isoformat(),
            'approval_status': e.approval_status
        } for e in control_status.evidence.all()]
    }
    return JsonResponse(data)

@login_required
def get_system_data(request):
    """API endpoint for system data"""
    systems = InformationSystem.objects.filter(owner=request.user)
    data = [{'id': s.id, 'name': s.name, 'description': s.description} for s in systems]
    return JsonResponse({'success': True, 'systems': data})

@login_required
def get_systems_for_filter(request):
    """API endpoint for system filter options"""
    systems = InformationSystem.objects.filter(owner=request.user)
    data = [{'id': s.id, 'name': s.name} for s in systems]
    return JsonResponse({'systems': data})

@login_required
def validate_system_name(request):
    """API endpoint to validate system name uniqueness"""
    name = request.GET.get('name', '').strip()
    exists = InformationSystem.objects.filter(name__iexact=name).exists()
    return JsonResponse({'valid': not exists, 'message': 'Name already taken' if exists else ''})


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import InformationSystem, SystemControlStatus, Evidence


@login_required
def reports_dashboard(request):
    """Enhanced reports and analytics dashboard"""
    user = request.user

    # Basic counts
    total_systems = InformationSystem.objects.filter(owner=user).count()
    total_controls = SystemControlStatus.objects.filter(system__owner=user).count()

    # Status counts with proper labels
    status_counts = SystemControlStatus.objects.filter(
        system__owner=user
    ).values('status').annotate(count=Count('id')).order_by('status')

    # Framework distribution
    framework_counts = InformationSystem.objects.filter(
        owner=user
    ).values('frameworks__name').annotate(count=Count('id')).exclude(
        frameworks__name__isnull=True
    ).order_by('-count')

    # Recent evidence with better selection
    recent_evidence = Evidence.objects.filter(
        system_control_status__system__owner=user
    ).select_related(
        'system_control_status__system',
        'system_control_status__control'
    ).order_by('-uploaded_at')[:10]

    # Compliance rate calculation
    implemented_count = SystemControlStatus.objects.filter(
        system__owner=user,
        status='implemented'
    ).count()

    compliance_rate = (implemented_count / total_controls * 100) if total_controls > 0 else 0

    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_activity = Evidence.objects.filter(
        system_control_status__system__owner=user,
        uploaded_at__gte=thirty_days_ago
    ).count()

    # Systems by framework
    systems_by_framework = InformationSystem.objects.filter(
        owner=user
    ).values('frameworks__name').annotate(
        system_count=Count('id')
    ).exclude(frameworks__name__isnull=True)

    # Controls by status for chart data
    status_chart_data = []
    for status in status_counts:
        status_chart_data.append({
            'status': status['status'],
            'count': status['count'],
            'label': status['status'].replace('_', ' ').title()
        })

    # Monthly evidence trend (last 6 months)
    monthly_evidence = []
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        count = Evidence.objects.filter(
            system_control_status__system__owner=user,
            uploaded_at__gte=month_start,
            uploaded_at__lt=month_end
        ).count()

        monthly_evidence.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })

    monthly_evidence.reverse()  # Show oldest to newest

    # Critical systems (systems with most non-compliant controls)
    critical_systems = InformationSystem.objects.filter(
        owner=user
    ).annotate(
        non_compliant_count=Count(
            'systemcontrolstatus',
            filter=Q(systemcontrolstatus__status='not_implemented')
        )
    ).filter(non_compliant_count__gt=0).order_by('-non_compliant_count')[:5]

    context = {
        'total_systems': total_systems,
        'total_controls': total_controls,
        'status_counts': status_counts,
        'framework_counts': framework_counts,
        'recent_evidence': recent_evidence,
        'compliance_rate': round(compliance_rate, 1),
        'recent_activity': recent_activity,
        'systems_by_framework': systems_by_framework,
        'status_chart_data': json.dumps(status_chart_data),
        'monthly_evidence': monthly_evidence,
        'critical_systems': critical_systems,
        'current_date': timezone.now(),
    }

    return render(request, 'compliance/reports_dashboard.html', context)


@login_required
def export_compliance_report(request):
    """Export comprehensive compliance report as CSV"""
    import csv
    from django.http import HttpResponse

    user = request.user

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response[
        'Content-Disposition'] = f'attachment; filename="compliance_report_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)

    # Write header
    writer.writerow(['System Name', 'Framework', 'Control Name', 'Status', 'Last Updated'])

    # Get all systems with their controls
    systems = InformationSystem.objects.filter(owner=user).prefetch_related(
        'frameworks', 'systemcontrolstatus_set__control'
    )

    # Write data rows
    for system in systems:
        for framework in system.frameworks.all():
            for control_status in system.systemcontrolstatus_set.all():
                writer.writerow([
                    system.name,
                    framework.name,
                    control_status.control.title,  # Fixed: changed from .name to .title
                    control_status.status,
                    control_status.updated_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(control_status,
                                                                                       'updated_at') else 'N/A'
                ])

    return response


@login_required
def compliance_metrics_api(request):
    """API endpoint for dashboard metrics (for AJAX updates)"""
    user = request.user

    # Real-time metrics
    metrics = {
        'total_systems': InformationSystem.objects.filter(owner=user).count(),
        'total_controls': SystemControlStatus.objects.filter(system__owner=user).count(),
        'compliance_rate': 0,
        'recent_evidence_count': Evidence.objects.filter(
            system_control_status__system__owner=user,
            uploaded_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }

    # Calculate compliance rate
    if metrics['total_controls'] > 0:
        implemented = SystemControlStatus.objects.filter(
            system__owner=user, status='implemented'
        ).count()
        metrics['compliance_rate'] = round((implemented / metrics['total_controls']) * 100, 1)

    return JsonResponse(metrics)
# Updated REST Framework ViewSets
from rest_framework import serializers

class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = ['id', 'name', 'description', 'version', 'created_at', 'updated_at']

class ControlCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlCategory
        fields = ['id', 'framework', 'name', 'code', 'description', 'parent_category']

class ComplianceControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = Control
        fields = ['id', 'framework', 'category', 'control_id', 'title', 'description', 'status', 'risk_level']

class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ['id', 'system_control_status', 'title', 'description', 'evidence_type', 'file_path', 'approval_status']

class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = ['id', 'control', 'assessor', 'status', 'findings', 'recommendations', 'assessment_date']

class ComplianceReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceReport
        fields = ['id', 'framework', 'title', 'report_type', 'generated_by', 'generated_at', 'date_from', 'date_to', 'report_data']

class SystemControlStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemControlStatus
        fields = ['id', 'system', 'framework', 'control', 'controller', 'status', 'progress', 'deadline']

class InformationSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformationSystem
        fields = ['id', 'name', 'description', 'owner', 'organization', 'frameworks', 'status', 'cached_progress']

class ComplianceFrameworkViewSet(viewsets.ModelViewSet):
    queryset = Framework.objects.all()
    serializer_class = ComplianceFrameworkSerializer
    permission_classes = [permissions.IsAuthenticated]

class ControlCategoryViewSet(viewsets.ModelViewSet):
    queryset = ControlCategory.objects.all()
    serializer_class = ControlCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class ComplianceControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.all()
    serializer_class = ComplianceControlSerializer
    permission_classes = [permissions.IsAuthenticated]

class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.IsAuthenticated]

class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class ComplianceReportViewSet(viewsets.ModelViewSet):
    queryset = ComplianceReport.objects.all()
    serializer_class = ComplianceReportSerializer
    permission_classes = [permissions.IsAuthenticated]

class SystemControlStatusViewSet(viewsets.ModelViewSet):
    queryset = SystemControlStatus.objects.all()
    serializer_class = SystemControlStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

class InformationSystemViewSet(viewsets.ModelViewSet):
    queryset = InformationSystem.objects.all()
    serializer_class = InformationSystemSerializer
    permission_classes = [permissions.IsAuthenticated]
# views.py
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

def custom_login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard_view')
        else:
            return render(request, 'registration/login.html', {'form': form})
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form}) # Changed from 'login.html' to 'registration/login.html'
from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout_view(request):
    """Proper logout view that works correctly - FIXED"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('custom_login_view')


# Add these views to your views.py file

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


# Evidence Management Views
@login_required
def upload_evidence_view(request):
    """View for uploading evidence files"""
    if request.method == 'POST':
        try:
            # Get the system_control_status_id from the form
            system_control_status_id = request.POST.get('system_control_status_id')
            system_control_status = get_object_or_404(SystemControlStatus, id=system_control_status_id)

            # Create the evidence record
            evidence = Evidence.objects.create(
                system_control_status=system_control_status,
                title=request.POST.get('title', 'Uploaded Evidence'),
                description=request.POST.get('description', ''),
                evidence_type=request.POST.get('evidence_type', 'document'),
                file_path=request.FILES.get('file'),
                uploaded_by=request.user
            )

            # The Evidence model's save() method will automatically:
            # 1. Set system_control_status.evidence_uploaded = True
            # 2. Call update_progress_on_evidence_upload() which will:
            #    - Set progress = 75
            #    - Set status = 'pending'
            #    - Set implementation_status = 'under_review'

            messages.success(request, 'Evidence uploaded successfully! Status updated to pending review.')
            return redirect('dashboard_view')

        except Exception as e:
            messages.error(request, f'Error uploading evidence: {str(e)}')

    return render(request, 'compliance/upload_evidence.html')

@login_required
def evidence_detail_view(request, evidence_id):
    """View for displaying evidence details"""
    # evidence = get_object_or_404(Evidence, id=evidence_id)
    # Replace with your actual Evidence model
    context = {
        'evidence_id': evidence_id,
        # 'evidence': evidence,
    }
    return render(request, 'compliance/evidence_detail.html', context)
# Updated Django view with CSRF and error handling fixes

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

# Controller Management Views
@login_required
@csrf_protect
def assign_controller_view(request, controller_id):
    """View for assigning controllers to controls"""

    # Get the control object first
    control = get_object_or_404(Control, id=controller_id)

    if request.method == 'POST':
        # Get form data
        controller_name = request.POST.get('controller_name', '').strip()
        job_title = request.POST.get('job_title', '').strip()
        employee_number = request.POST.get('employee_number', '').strip()
        email = request.POST.get('email', '').strip()

        # Validate required fields
        if not all([controller_name, job_title, employee_number, email]):
            messages.error(request, 'All fields are required.')
            return render(request, 'compliance/assign_controller.html', {
                'controller_id': controller_id,
                'control': control,
                'form_data': request.POST
            })

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'compliance/assign_controller.html', {
                'controller_id': controller_id,
                'control': control,
                'form_data': request.POST
            })

        try:
            # Get or create controller
            controller, created = ControllerProfile.objects.get_or_create(
                email=email,
                defaults={
                    'name': controller_name,
                    'job_title': job_title,
                    'employee_number': employee_number,
                }
            )

            # If controller exists but with different info, update it
            if not created:
                controller.name = controller_name
                controller.job_title = job_title
                controller.employee_number = employee_number
                controller.save()

            # Assign controller to control
            control.assigned_controller = controller
            control.save()

            # Log the assignment
            logger.info(
                f"Controller {controller_name} assigned to control {control.name} "
                f"by user {request.user.username}"
            )

            messages.success(request, f'Controller {controller_name} assigned successfully!')
            return redirect('dashboard_view')

        except Exception as e:
            logger.error(f"Error in assign_controller_view: {str(e)}")
            messages.error(request, f'Error assigning controller: {str(e)}')
            return render(request, 'compliance/assign_controller.html', {
                'controller_id': controller_id,
                'control': control,
                'form_data': request.POST
            })

    # GET request - show the form
    context = {
        'controller_id': controller_id,
        'control': control,
    }
    return render(request, 'compliance/assign_controller.html', context)


# Compliance Status Views
@login_required
def compliant_controls_view(request):
    """View for displaying compliant controls"""
    # Get compliant controls from your model
    # compliant_controls = SystemControlStatus.objects.filter(status='compliant')

    context = {
        # 'controls': compliant_controls,
        'status_type': 'compliant',
        'page_title': 'Compliant Controls'
    }
    return render(request, 'compliance/control_status.html', context)


@login_required
def non_compliant_controls_view(request):
    """View for displaying non-compliant controls"""
    # non_compliant_controls = SystemControlStatus.objects.filter(status='non_compliant')

    context = {
        # 'controls': non_compliant_controls,
        'status_type': 'non_compliant',
        'page_title': 'Non-Compliant Controls'
    }
    return render(request, 'compliance/control_status.html', context)


@login_required
def partial_controls_view(request):
    """View for displaying partially compliant controls"""
    # partial_controls = SystemControlStatus.objects.filter(status='partial')

    context = {
        # 'controls': partial_controls,
        'status_type': 'partial',
        'page_title': 'Partially Compliant Controls'
    }
    return render(request, 'compliance/control_status.html', context)


@login_required
def pending_controls_view(request):
    """View for displaying pending controls"""
    # pending_controls = SystemControlStatus.objects.filter(status='pending')

    context = {
        # 'controls': pending_controls,
        'status_type': 'pending',
        'page_title': 'Pending Controls'
    }
    return render(request, 'compliance/control_status.html', context)

# Fix the framework loading issue - Issue 3
@login_required
def get_framework_controls_api(request, framework_id):
    """API to get controls for a specific framework - FIXED"""
    try:
        framework = get_object_or_404(Framework, id=framework_id)
        controls = Control.objects.filter(framework=framework).select_related('category')

        controls_data = []
        for control in controls:
            controls_data.append({
                'id': control.id,
                'control_id': control.control_id,
                'title': control.title,
                'description': control.description,
                'category': control.category.name if control.category else 'No Category'
            })

        return JsonResponse({
            'success': True,
            'framework_name': framework.name,
            'controls': controls_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# Fix the delete control function - Issue 6
@login_required
@require_POST
def delete_control_status(request, control_status_id):
    """Delete a control status assignment - FIXED"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Check permission
    if control_status.system.owner != request.user:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    try:
        control_status.delete()
        return JsonResponse({'success': True, 'message': 'Control assignment deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
@csrf_exempt
def list_framework_controls_api(request, framework_id):
    """List all controls for a specific framework - used by the frontend modal"""
    try:
        framework = get_object_or_404(Framework, id=framework_id)

        # Get all controls for this framework
        controls = Control.objects.filter(framework=framework).select_related('category')

        controls_data = []
        for control in controls:
            controls_data.append({
                'id': control.id,
                'control_id': control.control_id,
                'title': control.title,
                'description': control.description[:100] + '...' if len(control.description) > 100 else control.description,
                'category': control.category.name if control.category else 'Uncategorized'
            })

        return JsonResponse({
            'success': True,
            'framework_id': framework_id,
            'framework_name': framework.name,
            'total_controls': len(controls_data),
            'controls': controls_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

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

@login_required
def questionnaire_view(request):
    """Redirect to ngrok questionnaire link with user tracking"""
    # Store user session info before redirect
    request.session['questionnaire_start_time'] = timezone.now().isoformat()
    request.session['questionnaire_user_id'] = request.user.id

    # Mark questionnaire as started for all user systems
    user_systems = InformationSystem.objects.filter(owner=request.user)
    for system in user_systems:
        request.session[f'questionnaire_started_{system.id}'] = True

    # Redirect users directly to the ngrok questionnaire
    return redirect('https://85e5f0c29084.ngrok-free.app')

@login_required
def questionnaire_completed_callback(request):
    """Callback endpoint when questionnaire is completed"""
    if request.method == 'POST':
        try:
            # Mark questionnaire as completed for all user systems
            user_systems = InformationSystem.objects.filter(owner=request.user)

            for system in user_systems:
                # Mark questionnaire as completed
                request.session[f'questionnaire_completed_{system.id}'] = True

                # Simulate deployment info if not exists (for questionnaire flow)
                if f'deployment_{system.id}' not in request.session:
                    import uuid
                    deployment_id = str(uuid.uuid4())
                    request.session[f'deployment_{system.id}'] = {
                        'deployment_id': deployment_id,
                        'ngrok_url': f"https://{deployment_id[:8]}.ngrok-free.app",
                        'deployed_at': timezone.now().isoformat(),
                        'status': 'questionnaire_completed',
                        'extract_ready': True
                    }

            # Store questionnaire completion timestamp
            request.session['questionnaire_completed_at'] = timezone.now().isoformat()

            return JsonResponse({
                'success': True,
                'message': 'Questionnaire completed successfully',
                'extract_ready': True
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error processing questionnaire completion: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def extract_results(request):
    """Extract and analyze results from ngrok deployment or questionnaire"""
    if request.method == 'POST':
        system_id = request.POST.get('system_id')
        deployment_id = request.POST.get('deployment_id')

        try:
            system = InformationSystem.objects.get(id=system_id, owner=request.user)

            # Get deployment info
            deployment_info = request.session.get(f'deployment_{system_id}')
            if not deployment_info:
                return JsonResponse({
                    'success': False,
                    'message': 'No deployment or questionnaire completion found'
                })

            # Check if questionnaire was completed
            questionnaire_completed = request.session.get(f'questionnaire_completed_{system_id}', False)

            # Get system's control statuses
            control_statuses = SystemControlStatus.objects.filter(
                system=system
            ).select_related('control', 'framework')

            results = []
            matched_controls = 0
            improved_controls = 0
            needs_attention = 0

            # Simulate analysis of each control (enhanced based on questionnaire completion)
            for control_status in control_statuses:
                import random

                # If questionnaire was completed, give better scores
                if questionnaire_completed:
                    deployment_score = random.randint(65, 95)  # Higher scores for questionnaire completion
                else:
                    deployment_score = random.randint(40, 85)  # Normal deployment scores

                current_status = control_status.implementation_status or 'not_started'

                # Determine deployment result based on score
                if deployment_score >= 80:
                    deployment_result = 'compliant'
                    match_status = 'matched'
                    matched_controls += 1
                    if current_status != 'compliant':
                        improved_controls += 1
                        # Update the control status
                        control_status.implementation_status = 'compliant'
                        control_status.status = 'compliant'
                        control_status.progress = 100
                        control_status.save()
                elif deployment_score >= 60:
                    deployment_result = 'partial'
                    match_status = 'partial_match'
                    # Update the control status
                    control_status.implementation_status = 'partially_compliant'
                    control_status.status = 'partially_compliant'
                    control_status.progress = 75
                    control_status.save()
                else:
                    deployment_result = 'non_compliant'
                    match_status = 'no_match'
                    needs_attention += 1

                results.append({
                    'control_id': control_status.control.control_id,
                    'control_title': control_status.control.title,
                    'current_status': current_status,
                    'deployment_result': deployment_result,
                    'deployment_score': deployment_score,
                    'match_status': match_status,
                    'control_status_id': control_status.id
                })

            # Calculate overall compliance score
            total_controls = len(results)
            compliance_score = (matched_controls / total_controls * 100) if total_controls > 0 else 0

            # Store results in session for later retrieval and journey progress
            extraction_results = {
                'extracted_at': timezone.now().isoformat(),
                'deployment_id': deployment_info.get('deployment_id'),
                'total_controls': total_controls,
                'matched_controls': matched_controls,
                'improved_controls': improved_controls,
                'needs_attention': needs_attention,
                'compliance_score': compliance_score,
                'questionnaire_completed': questionnaire_completed,
                'results': results,
                'system_name': system.name,
                'system_id': system.id
            }

            request.session[f'extraction_results_{system_id}'] = extraction_results

            # Update journey steps progress
            request.session['journey_progress_updated'] = True
            request.session['latest_compliance_score'] = compliance_score
            request.session['latest_extraction_date'] = timezone.now().isoformat()

            return JsonResponse({
                'success': True,
                'summary': {
                    'total_controls': total_controls,
                    'matched_controls': matched_controls,
                    'improved_controls': improved_controls,
                    'needs_attention': needs_attention
                },
                'complianceScore': compliance_score,
                'improvementPercentage': improved_controls,
                'questionnaireCompleted': questionnaire_completed,
                'results': {
                    'extracted_at': timezone.now().isoformat(),
                    'total_controls': total_controls,
                    'matched_controls': matched_controls,
                    'results': results
                }
            })

        except InformationSystem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'System not found or access denied'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Result extraction failed: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def api_questionnaire_status(request):
    """API endpoint to check questionnaire completion status"""
    user_systems = InformationSystem.objects.filter(owner=request.user)

    # Check if any system has completed questionnaire
    completed_systems = []
    for system in user_systems:
        if request.session.get(f'questionnaire_completed_{system.id}', False):
            completed_systems.append({
                'system_id': system.id,
                'system_name': system.name,
                'extract_ready': True
            })

    # Get latest extraction results if available
    latest_results = None
    latest_score = 0

    for system in user_systems:
        extraction_data = request.session.get(f'extraction_results_{system.id}')
        if extraction_data:
            if not latest_results or extraction_data['extracted_at'] > latest_results.get('extracted_at', ''):
                latest_results = extraction_data
                latest_score = extraction_data.get('compliance_score', 0)

    return JsonResponse({
        'completed': len(completed_systems) > 0,
        'completed_systems': completed_systems,
        'latest_score': latest_score,
        'results': {
            'totalQuestions': latest_results.get('total_controls', 0) if latest_results else 0,
            'correctAnswers': latest_results.get('matched_controls', 0) if latest_results else 0,
            'complianceScore': latest_score,
            'previousScore': 0,  # You can track this if needed
            'recommendations': [],
            'extracted_at': latest_results.get('extracted_at') if latest_results else None,
            'questionnaire_completed': any(request.session.get(f'questionnaire_completed_{s.id}', False) for s in user_systems)
        }
    })

@login_required
def organizations_api(request):
    """API endpoint for organizations dropdown"""
    from .models import Organization
    organizations = Organization.objects.all().values('id', 'name')
    return JsonResponse(list(organizations), safe=False)

@login_required
def frameworks_api(request):
    """API endpoint for frameworks dropdown"""
    try:
        frameworks = Framework.objects.all().values('id', 'name', 'description')
        return JsonResponse({
            'success': True,
            'frameworks': list(frameworks)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
