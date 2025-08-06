from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_fixed
from .landing_views import landing_view, home_redirect

# Create a router for API endpoints
router = DefaultRouter()
router.register(r'frameworks', views.ComplianceFrameworkViewSet)
router.register(r'controls', views.ComplianceControlViewSet)
router.register(r'evidence', views.EvidenceViewSet)
router.register(r'assessments', views.AssessmentViewSet)
router.register(r'reports', views.ComplianceReportViewSet)
router.register(r'system-controls', views.SystemControlStatusViewSet)
router.register(r'systems', views.InformationSystemViewSet)

app_name = 'compliance'

urlpatterns = [
    # Landing and home redirect
    path('', landing_view, name='home'),
    path('welcome/', landing_view, name='landing'),

    # Main dashboard (requires authentication)
    path('dashboard/', views.dashboard_view, name='dashboard_view'),

    # System management
    path('add-system/', views_fixed.add_system, name='add_system'),
    path('edit-system/<int:system_id>/', views.edit_system, name='edit_system'),
    path('delete-system/<int:system_id>/', views.delete_system, name='delete_system'),
    path('system/<int:system_id>/', views.system_detail, name='system_detail'),

    # Control management
    path('control/<int:control_status_id>/', views_fixed.control_detail, name='control_detail'),
    path('update-control/<int:control_status_id>/', views.update_control_status, name='update_control_status'),
    path('delete-control-status/<int:control_status_id>/', views.delete_control_status, name='delete_control_status'),

    # Evidence management
    path('upload-evidence/<int:control_status_id>/', views.upload_evidence, name='upload_evidence'),
    path('review-evidence/<int:evidence_id>/', views.review_evidence, name='review_evidence'),

    # Controller management
    path('assign-controller/<int:controller_id>/', views.assign_controller_view, name='assign_controller'),
    path('my-assignments/', views.my_assignments, name='my_assignments'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),

    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('export-compliance-report/', views.export_compliance_report, name='export_compliance_report'),

    # Deployment and Results Extraction - NEW


    # Questionnaire and API endpoints - NEW
    path('questionnaire/', views.questionnaire_view, name='questionnaire'),
    path('questionnaire-completed/', views.questionnaire_completed_callback, name='questionnaire_completed'),



    # API endpoints
    path('api/', include(router.urls)),
    path('api/login/', views.api_login_view, name='api_login'),
    path('api/organizations/', views.organizations_api, name='organizations_api'),
    path('api/frameworks/', views.frameworks_api, name='frameworks_api'),
    path('api/assign-framework/<int:system_id>/', views.assign_framework_api, name='assign_framework_api'),
    path('api/remove-framework/<int:system_id>/<int:framework_id>/', views.remove_framework_api, name='remove_framework_api'),
    path('api/assign-controls/<int:system_id>/', views.assign_controls_api, name='assign_controls_api'),
    path('api/list-controls/<int:system_id>/', views.list_controls_api, name='list_controls_api'),
    path('api/framework/<int:framework_id>/controls/', views.list_framework_controls_api, name='list_framework_controls_api'),
    path('api/list-controls/framework/<int:framework_id>/', views.list_framework_controls_api, name='list_framework_controls_api_alt'),
    path('api/notifications/partial/', views.notifications_partial, name='notifications_partial'),
    path('api/deadline-countdown/<int:control_status_id>/', views.deadline_countdown, name='deadline_countdown'),
    path('api/compliance-metrics/', views.compliance_metrics_api, name='compliance_metrics_api'),

    # Framework and control management (legacy URLs)
    path('edit/<int:pk>/', views.edit_framework, name='edit_framework'),
    path('delete/<int:pk>/', views.delete_framework, name='delete_framework'),
    path('refresh/', views.refresh_frameworks, name='refresh_frameworks'),
    path('details/<int:pk>/', views.framework_details, name='framework_details'),
    path('systems-data/', views.get_system_data, name='get_system_data'),
    path('systems-filter/', views.get_systems_for_filter, name='get_systems_for_filter'),
    path('validate-name/', views.validate_system_name, name='validate_system_name'),

    # Status views
    path('compliant-controls/', views.compliant_controls_view, name='compliant_controls'),
    path('non-compliant-controls/', views.non_compliant_controls_view, name='non_compliant_controls'),
    path('partial-controls/', views.partial_controls_view, name='partial_controls'),
    path('pending-controls/', views.pending_controls_view, name='pending_controls'),

    # Evidence management
    path('upload-evidence-view/', views.upload_evidence_view, name='upload_evidence_view'),
    path('evidence-detail/<int:evidence_id>/', views.evidence_detail_view, name='evidence_detail'),

    # Authentication
    path('login/', views.custom_login_view, name='custom_login_view'),
    path('logout/', views.custom_logout_view, name='custom_logout_view'),

    # Control status management
    path('delete-control-status/<int:control_status_id>/', views.delete_control_status, name='delete_control_status'),
]
