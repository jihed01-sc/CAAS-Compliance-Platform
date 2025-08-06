from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta
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
import logging
import requests
import json
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)

from .models import (
    InformationSystem, Framework, Control,
    SystemControlStatus, Evidence, ControllerProfile, Notification,
    ControlCategory, EvidenceReview, Assessment, ComplianceReport
)
from .forms import (
    SystemCreationForm, ControlAssignmentForm, EvidenceUploadForm,
    EvidenceReviewForm, SystemControlStatusForm, FrameworkAssignmentForm,
)

from django.shortcuts import render
from django.views.decorators.csrf import get_token

# Fix the my_assignments view - Issue 1
@login_required
def my_assignments(request):
    """My assignments view with dark mode styling - FIXED"""

    # Get user's assignments through SystemControlStatus - Fixed field name
    assignments = SystemControlStatus.objects.filter(
        controller__user=request.user
    ).select_related('control', 'system', 'control__category', 'control__framework').order_by('-last_updated')

    # Calculate statistics
    compliant_count = assignments.filter(status='compliant').count()
    pending_count = assignments.filter(status='under_review').count()
    non_compliant_count = assignments.filter(status='non_compliant').count()

    # Calculate overdue assignments - Fixed field name
    today = timezone.now()
    overdue_count = assignments.filter(
        deadline__lt=today,
        status__in=['under_review', 'partially_compliant', 'non_compliant']
    ).count()

    context = {
        'assignments': assignments,
        'compliant_count': compliant_count,
        'pending_count': pending_count,
        'non_compliant_count': non_compliant_count,
        'overdue_count': overdue_count,
        'today': today,
    }

    return render(request, 'compliance/my_assignments.html', context)

# Fix the logout view - Issue 2
from django.contrib.auth import logout

@login_required
def custom_logout_view(request):
    """Proper logout view that works correctly"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('custom_login_view')

# Fix the framework loading issue - Issue 3
@login_required
def get_framework_controls_api(request, framework_id):
    """API to get controls for a specific framework"""
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

# Fix the control detail view permission issue - Issue 4
@login_required
def control_detail(request, control_status_id):
    """Enhanced detailed view of a specific control implementation with audit framework context"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Fixed permission check
    has_permission = (
        control_status.system.owner == request.user or
        (control_status.controller and control_status.controller.user == request.user)
    )

    if not has_permission:
        messages.error(request, 'You do not have permission to view this control.')
        return redirect('dashboard_view')

    evidence_files = Evidence.objects.filter(
        system_control_status=control_status
    ).order_by('-uploaded_at')

    reviews = EvidenceReview.objects.filter(
        evidence__system_control_status=control_status
    ).order_by('-reviewed_at')

    # Extract audit framework metadata from system description
    audit_framework_metadata = None
    try:
        import json
        system_description = control_status.system.description
        if system_description and "--- AUDIT FRAMEWORK METADATA ---" in system_description:
            # Extract JSON metadata from description
            metadata_start = system_description.find("--- AUDIT FRAMEWORK METADATA ---")
            if metadata_start != -1:
                json_start = system_description.find("{", metadata_start)
                if json_start != -1:
                    json_str = system_description[json_start:]
                    try:
                        audit_framework_metadata = json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    # Process metadata for template display
    client_profile = audit_framework_metadata.get('client_profile', {}) if audit_framework_metadata else {}
    compliance_standards = audit_framework_metadata.get('compliance_standards', {}) if audit_framework_metadata else {}
    audit_focus = audit_framework_metadata.get('audit_focus', {}) if audit_framework_metadata else {}
    risk_assessment = audit_framework_metadata.get('risk_assessment', {}) if audit_framework_metadata else {}
    remediation_roadmap = audit_framework_metadata.get('remediation_roadmap', {}) if audit_framework_metadata else {}
    branding_config = audit_framework_metadata.get('branding_config', {}) if audit_framework_metadata else {}

    context = {
        'control_status': control_status,
        'evidence_files': evidence_files,
        'reviews': reviews,
        'audit_framework_metadata': audit_framework_metadata,
        'client_profile': client_profile,
        'compliance_standards': compliance_standards,
        'audit_focus': audit_focus,
        'risk_assessment': risk_assessment,
        'remediation_roadmap': remediation_roadmap,
        'branding_config': branding_config,
    }

    return render(request, 'compliance/control_detail.html', context)

# Fix the upload evidence view - Issue 5
@login_required
def upload_evidence(request, control_status_id):
    """Upload evidence for a control - FIXED"""
    control_status = get_object_or_404(SystemControlStatus, id=control_status_id)

    # Fixed permission check
    has_permission = (
        control_status.system.owner == request.user or
        (control_status.controller and control_status.controller.user == request.user)
    )

    if not has_permission:
        messages.error(request, 'You are not authorized to upload evidence for this control.')
        return redirect('compliance:control_detail', control_status_id=control_status_id)

    if request.method == 'POST':
        form = EvidenceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.system_control_status = control_status
            evidence.uploaded_by = request.user
            evidence.save()

            # Update control status
            control_status.evidence_uploaded = True
            control_status.progress = 75
            control_status.status = 'under_review'
            control_status.implementation_status = 'pending_evidence'
            control_status.save()

            # Create notification
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

# Fix the add system view to handle framework selection properly - Issue 7
@login_required
def add_system(request):
    """
    Enhanced Cybersecurity Compliance Audit Framework Creation
    Supports ISO/IEC 27001:2022, IEC 62443, NIS2 Directive with comprehensive client profiling
    """
    if request.method == 'POST':
        try:
            # ===== BASIC SYSTEM INFORMATION =====
            system_name = request.POST.get('name')
            description = request.POST.get('description', '')
            organization_id = request.POST.get('organization')

            # ===== CLIENT DETAILS SECTION =====
            client_company_name = request.POST.get('client_company_name', '').strip()
            client_sector = request.POST.get('client_sector', 'technology')  # Default: technology
            organization_size = request.POST.get('organization_size', 'smb')  # SMB, mid-market, enterprise
            operational_scope = request.POST.get('operational_scope', 'it')  # IT, OT, IT_OT_convergence

            # Branding and customization
            client_logo_url = request.POST.get('client_logo_url', '').strip()
            branding_preferences = request.POST.get('branding_preferences', '').strip()
            use_client_branding = request.POST.get('use_client_branding') == 'on'

            # Geographical and regulatory context
            geographical_location = request.POST.get('geographical_location', '').strip()
            regulatory_jurisdiction = request.POST.get('regulatory_jurisdiction', 'eu')  # EU, US, APAC, etc.
            business_criticality = request.POST.get('business_criticality', 'high')  # high, medium, low

            # ===== COMPLIANCE STANDARDS SELECTION =====
            # Multi-standard framework selection
            compliance_standards = request.POST.getlist('compliance_standards')
            unified_framework = request.POST.get('unified_framework') == 'on'

            # ISO/IEC 27001:2022 Configuration
            iso27001_scope = request.POST.get('iso27001_scope', 'full')  # full, partial, annex_a_only
            iso27001_annexes = request.POST.getlist('iso27001_annexes')  # A.5, A.6, A.7, etc.

            # IEC 62443 Industrial Security Configuration
            iec62443_sections = request.POST.getlist('iec62443_sections')  # 2-1, 2-4, 3-2, 3-3, 4-2
            iec62443_security_levels = request.POST.getlist('iec62443_security_levels')  # SL1, SL2, SL3, SL4
            industrial_zones = request.POST.getlist('industrial_zones')  # Manufacturing, SCADA, HMI, etc.

            # NIS2 Directive Configuration
            nis2_applicable_entities = request.POST.getlist('nis2_applicable_entities')  # Essential, Important
            nis2_sectors = request.POST.getlist('nis2_sectors')  # Energy, Transport, Banking, etc.
            incident_reporting_required = request.POST.get('incident_reporting_required') == 'on'

            # ===== AUDIT FOCUS AREAS =====
            # Functional modules selection (IAM, governance, logging, patching, etc.)
            audit_modules = request.POST.getlist('audit_modules')
            technical_domains = request.POST.getlist('technical_domains')

            # Identity and Access Management (IAM) specifics
            iam_scope = request.POST.getlist('iam_scope')  # SSO, MFA, RBAC, PAM
            governance_frameworks = request.POST.getlist('governance_frameworks')  # COBIT, ITIL, TOGAF

            # Logging and monitoring
            logging_requirements = request.POST.getlist('logging_requirements')  # SIEM, SOAR, Log retention
            security_monitoring = request.POST.getlist('security_monitoring')  # 24/7 SOC, threat hunting

            # Patch management and vulnerability assessment
            patching_strategy = request.POST.get('patching_strategy', 'risk_based')  # automated, manual, risk_based
            vulnerability_scanning = request.POST.get('vulnerability_scanning', 'quarterly')

            # ===== RISK ASSESSMENT METHODOLOGY =====
            risk_methodology = request.POST.get('risk_methodology', 'iso31000')  # ISO 31000, NIST, FAIR
            threat_modeling_approach = request.POST.get('threat_modeling_approach', 'stride')  # STRIDE, PASTA, OCTAVE
            risk_appetite = request.POST.get('risk_appetite', 'medium')  # low, medium, high
            risk_tolerance_level = request.POST.get('risk_tolerance_level', 'moderate')

            # Business impact analysis
            business_impact_categories = request.POST.getlist('business_impact_categories')
            rto_requirements = request.POST.get('rto_requirements', '4_hours')  # 1_hour, 4_hours, 24_hours
            rpo_requirements = request.POST.get('rpo_requirements', '1_hour')

            # ===== GAP ANALYSIS AND REMEDIATION ROADMAP =====
            gap_analysis_depth = request.POST.get('gap_analysis_depth', 'comprehensive')  # basic, detailed, comprehensive
            remediation_priority = request.POST.get('remediation_priority', 'risk_based')  # risk_based, cost_based, timeline_based
            timeline_constraints = request.POST.get('timeline_constraints', '12_months')
            budget_constraints = request.POST.get('budget_constraints', 'medium')

            # Implementation approach
            implementation_methodology = request.POST.get('implementation_methodology', 'agile')  # agile, waterfall, hybrid
            phased_approach = request.POST.get('phased_approach') == 'on'
            pilot_system_required = request.POST.get('pilot_system_required') == 'on'

            # ===== ORIGINAL SYSTEM CREATION PARAMETERS =====
            framework_id = request.POST.get('framework')
            controls = request.POST.getlist('controls')
            previously_implemented = request.POST.get('previously_implemented') == 'on'

            # Enhanced controller assignment
            controller_name = request.POST.get('controller_name', '').strip()
            controller_email = request.POST.get('controller_email', '').strip()
            controller_department = request.POST.get('controller_department', '').strip()
            controller_certifications = request.POST.getlist('controller_certifications')
            security_clearance_level = request.POST.get('security_clearance_level', 'standard')
            assign_controller = request.POST.get('assign_controller') == 'on'

            # ===== VALIDATION WITH COMPLIANCE CONTEXT =====
            if not system_name or not framework_id:
                return JsonResponse({
                    'success': False,
                    'message': 'System name and framework are required'
                })

            # Fix: Convert single framework to compliance standards format
            try:
                framework = Framework.objects.get(id=framework_id)
                compliance_standards = [framework.name.lower().replace(' ', '').replace('-', '')]
            except Framework.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected compliance framework does not exist'
                })

            # Validate framework selection (fixed validation)
            if not framework_id:
                return JsonResponse({
                    'success': False,
                    'message': 'At least one compliance framework must be selected'
                })

            if not client_company_name:
                return JsonResponse({
                    'success': False,
                    'message': 'Client company name is required for audit framework configuration'
                })

            if not compliance_standards:
                return JsonResponse({
                    'success': False,
                    'message': 'At least one compliance standard (ISO 27001, IEC 62443, or NIS2) must be selected'
                })

            if not audit_modules:
                return JsonResponse({
                    'success': False,
                    'message': 'At least one audit focus area must be selected (IAM, governance, logging, etc.)'
                })

            # Validate IEC 62443 specific requirements for industrial systems
            if 'iec62443' in compliance_standards:
                if operational_scope in ['ot', 'it_ot_convergence'] and not iec62443_sections:
                    return JsonResponse({
                        'success': False,
                        'message': 'IEC 62443 sections must be selected for OT/Industrial environments'
                    })

            # Validate NIS2 specific requirements
            if 'nis2' in compliance_standards and not nis2_applicable_entities:
                return JsonResponse({
                    'success': False,
                    'message': 'NIS2 entity classification (Essential/Important) is required'
                })

            # ===== ENHANCED SYSTEM CREATION WITH AUDIT FRAMEWORK =====
            with transaction.atomic():
                # Create the compliance audit system
                system = InformationSystem.objects.create(
                    name=system_name,
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

                # ===== COMPREHENSIVE AUDIT METADATA STORAGE =====
                audit_framework_metadata = {
                    'client_profile': {
                        'company_name': client_company_name,
                        'sector': client_sector,
                        'organization_size': organization_size,
                        'operational_scope': operational_scope,
                        'geographical_location': geographical_location,
                        'regulatory_jurisdiction': regulatory_jurisdiction,
                        'business_criticality': business_criticality
                    },
                    'branding_config': {
                        'logo_url': client_logo_url,
                        'preferences': branding_preferences,
                        'use_client_branding': use_client_branding
                    },
                    'compliance_standards': {
                        'selected_standards': compliance_standards,
                        'unified_framework': unified_framework,
                        'iso27001': {
                            'scope': iso27001_scope,
                            'annexes': iso27001_annexes
                        },
                        'iec62443': {
                            'sections': iec62443_sections,
                            'security_levels': iec62443_security_levels,
                            'industrial_zones': industrial_zones
                        },
                        'nis2': {
                            'applicable_entities': nis2_applicable_entities,
                            'sectors': nis2_sectors,
                            'incident_reporting': incident_reporting_required
                        }
                    },
                    'audit_focus': {
                        'modules': audit_modules,
                        'technical_domains': technical_domains,
                        'iam_scope': iam_scope,
                        'governance_frameworks': governance_frameworks,
                        'logging_requirements': logging_requirements,
                        'security_monitoring': security_monitoring,
                        'patching_strategy': patching_strategy,
                        'vulnerability_scanning': vulnerability_scanning
                    },
                    'risk_assessment': {
                        'methodology': risk_methodology,
                        'threat_modeling': threat_modeling_approach,
                        'risk_appetite': risk_appetite,
                        'risk_tolerance': risk_tolerance_level,
                        'business_impact_categories': business_impact_categories,
                        'rto_requirements': rto_requirements,
                        'rpo_requirements': rpo_requirements
                    },
                    'remediation_roadmap': {
                        'gap_analysis_depth': gap_analysis_depth,
                        'remediation_priority': remediation_priority,
                        'timeline_constraints': timeline_constraints,
                        'budget_constraints': budget_constraints,
                        'implementation_methodology': implementation_methodology,
                        'phased_approach': phased_approach,
                        'pilot_system_required': pilot_system_required
                    },
                    'audit_created': timezone.now().isoformat(),
                    'framework_version': '2.0',
                    'compliance_officer': request.user.username,
                    'last_updated': timezone.now().isoformat()
                }

                # Store comprehensive metadata
                import json
                system.description = f"{description}\n\n--- AUDIT FRAMEWORK METADATA ---\n{json.dumps(audit_framework_metadata, indent=2)}"
                system.save()

                # Add primary framework to system
                framework = get_object_or_404(Framework, id=framework_id)
                system.frameworks.add(framework)

                # Add additional frameworks based on compliance standards
                for standard in compliance_standards:
                    try:
                        if standard == 'iso27001' and 'ISO 27001' not in framework.name:
                            iso_framework = Framework.objects.filter(name__icontains='ISO 27001').first()
                            if iso_framework:
                                system.frameworks.add(iso_framework)
                        elif standard == 'iec62443' and 'IEC 62443' not in framework.name:
                            iec_framework = Framework.objects.filter(name__icontains='IEC 62443').first()
                            if iec_framework:
                                system.frameworks.add(iec_framework)
                        elif standard == 'nis2' and 'NIS2' not in framework.name:
                            nis2_framework = Framework.objects.filter(name__icontains='NIS2').first()
                            if nis2_framework:
                                system.frameworks.add(nis2_framework)
                    except Exception:
                        pass  # Framework might not exist yet

                # ===== ENHANCED CONTROLLER ASSIGNMENT =====
                controller = None
                if assign_controller and controller_name and controller_email:
                    try:
                        # Create enhanced controller profile
                        user, user_created = User.objects.get_or_create(
                            email=controller_email,
                            defaults={
                                'username': controller_email,
                                'first_name': controller_name.split()[0] if controller_name.split() else controller_name,
                                'last_name': ' '.join(controller_name.split()[1:]) if len(controller_name.split()) > 1 else '',
                                'is_active': True
                            }
                        )

                        # Create or update controller profile with compliance expertise
                        controller, created = ControllerProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'department': controller_department or 'Compliance & Security',
                                'expertise_areas': f'Certifications: {", ".join(controller_certifications) if controller_certifications else "None"} | Security Clearance: {security_clearance_level}',
                                'is_active': True,
                            }
                        )

                        if not created:
                            controller.department = controller_department or 'Compliance & Security'
                            controller.expertise_areas = f'Certifications: {", ".join(controller_certifications) if controller_certifications else "None"} | Security Clearance: {security_clearance_level}'
                            controller.save()

                    except Exception as e:
                        pass  # Continue without controller if creation fails

                # ===== ENHANCED CONTROL ASSIGNMENTS WITH AUDIT CONTEXT =====
                assigned_count = 0
                for control_id in controls:
                    try:
                        control = Control.objects.get(id=control_id)

                        # Enhanced status determination based on compliance standards and implementation
                        if previously_implemented:
                            if 'iec62443' in compliance_standards and operational_scope in ['ot', 'it_ot_convergence']:
                                status = 'partially_compliant'
                                progress = 60  # Higher baseline for industrial systems
                                deadline = timezone.now() + timezone.timedelta(days=14)
                            else:
                                status = 'partially_compliant'
                                progress = 50
                                deadline = timezone.now() + timezone.timedelta(days=7)
                        else:
                            status = 'non_compliant'
                            progress = 0
                            # Adjust deadlines based on business criticality
                            if business_criticality == 'high':
                                deadline = timezone.now() + timezone.timedelta(days=5)
                            elif business_criticality == 'medium':
                                deadline = timezone.now() + timezone.timedelta(days=7)
                            else:
                                deadline = timezone.now() + timezone.timedelta(days=14)

                        # Create enhanced system control status
                        system_control = SystemControlStatus.objects.create(
                            system=system,
                            framework=framework,
                            control=control,
                            controller=controller,
                            previously_implemented=previously_implemented,
                            status=status,
                            progress=progress,
                            deadline=deadline,
                            implementation_status='non_compliant'
                        )

                        assigned_count += 1

                        # Enhanced notification with compliance context
                        if controller:
                            Notification.objects.create(
                                user=controller.user,
                                notification_type='control_assigned',
                                title=f'🔐 Compliance Control Assigned - {client_company_name}',
                                message=f'Control {control.control_id} assigned for {", ".join(compliance_standards)} compliance audit in system {system.name}. Priority: {business_criticality.upper()}',
                                system_control_status=system_control
                            )

                    except Control.DoesNotExist:
                        continue

                # ===== AUDIT INITIALIZATION NOTIFICATIONS =====
                # Create audit kickoff notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='audit_initialized',
                    title=f'🎯 Compliance Audit Framework Initialized - {client_company_name}',
                    message=f'Audit framework created for {organization_size.upper()} organization in {client_sector} sector. Standards: {", ".join(compliance_standards)}. Controls: {assigned_count}. Timeline: {timeline_constraints}.',
                )

                # Enhanced success message with comprehensive audit details
                success_message = (
                    f'🎯 Compliance Audit Framework Successfully Created!\n'
                    f'Client: {client_company_name} ({organization_size.upper()} {client_sector})\n'
                    f'Standards: {", ".join(compliance_standards)}\n'
                    f'Scope: {operational_scope.replace("_", " ").title()}\n'
                    f'Controls: {assigned_count} assigned\n'
                    f'Timeline: {timeline_constraints}\n'
                    f'Risk Methodology: {risk_methodology.upper()}'
                )

                messages.success(request, success_message)

                return JsonResponse({
                    'success': True,
                    'audit_framework': {
                        'system_id': system.id,
                        'system_name': system.name,
                        'client_company': client_company_name,
                        'client_sector': client_sector,
                        'organization_size': organization_size,
                        'operational_scope': operational_scope,
                        'compliance_standards': compliance_standards,
                        'unified_framework': unified_framework,
                        'audit_modules': audit_modules,
                        'risk_methodology': risk_methodology,
                        'gap_analysis_depth': gap_analysis_depth,
                        'timeline_constraints': timeline_constraints,
                        'controls_assigned': assigned_count,
                        'controller': controller.user.get_full_name() if controller else None,
                        'business_criticality': business_criticality,
                        'regulatory_jurisdiction': regulatory_jurisdiction,
                        'framework_version': '2.0',
                        'audit_status': 'initialized',
                        'created_date': timezone.now().isoformat()
                    }
                })

        except Exception as e:
            import traceback
            logger.error(f"Error creating compliance audit framework: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'message': f'Error creating compliance audit framework: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid method'})

# ===== DEPLOYMENT AND RESULT EXTRACTION FUNCTIONALITY =====

@login_required
def deploy_to_ngrok(request):
    """Deploy system to ngrok and handle result extraction"""
    if request.method == 'POST':
        try:
            system_id = request.POST.get('system_id')
            deployment_type = request.POST.get('deployment_type', 'test')

            if not system_id:
                return JsonResponse({
                    'success': False,
                    'message': 'System ID is required for deployment'
                })

            system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

            # Prepare deployment data
            deployment_data = {
                'system_id': system.id,
                'system_name': system.name,
                'deployment_type': deployment_type,
                'timestamp': datetime.now().isoformat(),
                'user': request.user.username,
                'controls_count': SystemControlStatus.objects.filter(system=system).count(),
                'compliance_frameworks': [fw.name for fw in system.frameworks.all()]
            }

            # Deploy to ngrok endpoint
            ngrok_url = "https://49c2d6331e8c.ngrok-free.app"
            response = requests.post(
                f"{ngrok_url}/api/deploy",
                json=deployment_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                deployment_result = response.json()

                # Store deployment info in system description
                deployment_info = {
                    'deployment_id': deployment_result.get('deployment_id'),
                    'ngrok_url': ngrok_url,
                    'deployed_at': datetime.now().isoformat(),
                    'status': 'deployed'
                }

                # Update system with deployment info
                import json
                current_description = system.description
                if "--- DEPLOYMENT INFO ---" not in current_description:
                    system.description = f"{current_description}\n\n--- DEPLOYMENT INFO ---\n{json.dumps(deployment_info, indent=2)}"
                    system.save()

                return JsonResponse({
                    'success': True,
                    'deployment_id': deployment_result.get('deployment_id'),
                    'ngrok_url': ngrok_url,
                    'message': 'System deployed successfully to ngrok'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'Deployment failed: {response.text}'
                })

        except requests.RequestException as e:
            return JsonResponse({
                'success': False,
                'message': f'Connection error: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Deployment error: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
def extract_deployment_results(request):
    """Extract and match results from ngrok deployment"""
    if request.method == 'POST':
        try:
            system_id = request.POST.get('system_id')
            deployment_id = request.POST.get('deployment_id')

            if not system_id or not deployment_id:
                return JsonResponse({
                    'success': False,
                    'message': 'System ID and Deployment ID are required'
                })

            system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

            # Extract results from ngrok
            ngrok_url = "https://49c2d6331e8c.ngrok-free.app"
            response = requests.get(
                f"{ngrok_url}/api/results/{deployment_id}",
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()

                # Match results with current controls
                matched_results = []
                system_controls = SystemControlStatus.objects.filter(system=system)

                for control_status in system_controls:
                    control_id = control_status.control.control_id

                    # Look for matching results
                    for result in results.get('control_results', []):
                        if result.get('control_id') == control_id:
                            matched_result = {
                                'control_id': control_id,
                                'control_title': control_status.control.title,
                                'current_status': control_status.status,
                                'deployment_result': result.get('status'),
                                'deployment_score': result.get('score', 0),
                                'recommendations': result.get('recommendations', []),
                                'evidence_found': result.get('evidence_found', False),
                                'match_status': 'matched'
                            }
                            matched_results.append(matched_result)
                            break
                    else:
                        # No match found
                        matched_results.append({
                            'control_id': control_id,
                            'control_title': control_status.control.title,
                            'current_status': control_status.status,
                            'deployment_result': 'not_tested',
                            'deployment_score': 0,
                            'recommendations': [],
                            'evidence_found': False,
                            'match_status': 'no_match'
                        })

                # Store results
                results_data = {
                    'extracted_at': datetime.now().isoformat(),
                    'deployment_id': deployment_id,
                    'total_controls': len(matched_results),
                    'matched_controls': len([r for r in matched_results if r['match_status'] == 'matched']),
                    'results': matched_results
                }

                return JsonResponse({
                    'success': True,
                    'results': results_data,
                    'summary': {
                        'total_controls': len(matched_results),
                        'matched_controls': len([r for r in matched_results if r['match_status'] == 'matched']),
                        'improved_controls': len([r for r in matched_results if r['deployment_score'] > 70]),
                        'needs_attention': len([r for r in matched_results if r['deployment_score'] < 50])
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': f'Failed to extract results: {response.text}'
                })

        except requests.RequestException as e:
            return JsonResponse({
                'success': False,
                'message': f'Connection error: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Extraction error: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid method'})

@login_required
def check_deployment_status(request, system_id):
    """Check the current deployment status of a system"""
    try:
        system = get_object_or_404(InformationSystem, id=system_id, owner=request.user)

        # Extract deployment info from system description
        deployment_info = None
        if "--- DEPLOYMENT INFO ---" in system.description:
            import json
            info_start = system.description.find("--- DEPLOYMENT INFO ---")
            if info_start != -1:
                json_start = system.description.find("{", info_start)
                if json_start != -1:
                    json_str = system.description[json_start:]
                    try:
                        deployment_info = json.loads(json_str)
                    except json.JSONDecodeError:
                        pass

        if deployment_info:
            return JsonResponse({
                'success': True,
                'deployed': True,
                'deployment_info': deployment_info
            })
        else:
            return JsonResponse({
                'success': True,
                'deployed': False,
                'message': 'System not deployed'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error checking deployment status: {str(e)}'
        })

# Continue with rest of existing views...
