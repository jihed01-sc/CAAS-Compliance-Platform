from rest_framework import serializers
from .models import (
    ComplianceFramework, ControlCategory,
    ComplianceControl, Evidence,
    Assessment, ComplianceReport
)

class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    controls_count = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceFramework
        fields = '__all__'

    def get_controls_count(self, obj):
        return obj.controls.count()

class ControlCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlCategory
        fields = '__all__'

class ComplianceControlSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    owner_name = serializers.CharField(source='owner.username', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    evidence_count = serializers.SerializerMethodField()
    latest_assessment = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceControl
        fields = '__all__'

    def get_evidence_count(self, obj):
        return obj.evidence.count()

    def get_latest_assessment(self, obj):
        latest = obj.assessments.order_by('-assessment_date').first()
        if latest:
            return {
                'date': latest.assessment_date,
                'status': latest.status,
                'assessor': latest.assessor.username if latest.assessor else None
            }
        return None

class EvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = Evidence
        fields = '__all__'

class AssessmentSerializer(serializers.ModelSerializer):
    assessor_name = serializers.CharField(source='assessor.username', read_only=True)
    control_id = serializers.CharField(source='control.control_id', read_only=True)

    class Meta:
        model = Assessment
        fields = '__all__'

class ComplianceReportSerializer(serializers.ModelSerializer):
    framework_name = serializers.CharField(source='framework.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)

    class Meta:
        model = ComplianceReport
        fields = '__all__'
from .models import SystemControlStatus, InformationSystem

class SystemControlStatusSerializer(serializers.ModelSerializer):
    control_title = serializers.CharField(source='control.title', read_only=True)
    control_id = serializers.CharField(source='control.control_id', read_only=True)
    framework_name = serializers.CharField(source='control.framework.name', read_only=True)
    system_name = serializers.CharField(source='system.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)

    class Meta:
        model = SystemControlStatus
        fields = [
            'id', 'system', 'system_name',
            'control', 'control_id', 'control_title', 'framework_name',
            'status', 'progress', 'assigned_to', 'assigned_to_name', 'notes'
        ]
class EvidenceUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ['id', 'title', 'description', 'evidence_type', 'file_path', 'url']
class InformationSystemSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = InformationSystem
        fields = '__all__'
