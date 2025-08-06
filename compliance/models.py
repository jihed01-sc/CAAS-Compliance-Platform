from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg

class Organization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Framework(models.Model):
    """Main compliance frameworks like ISO 27001, SOC 2, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


from django.db import models
from django.utils import timezone

class ControlCategory(models.Model):
    """Categories within frameworks (e.g., Access Control, Data Protection)"""
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)  # e.g., AC, CP, SC
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['framework', 'code']
        verbose_name_plural = "Control Categories"
        ordering = ['framework', 'code']  # Added for consistent ordering

    def __str__(self):
        return f"{self.framework.name} - {self.name}"

    def get_full_path(self):
        """Get the full category path for subcategories"""
        if self.parent_category:
            return f"{self.parent_category.get_full_path()} > {self.name}"
        return self.name

    def get_full_path(self):
        """Get the full path of the category including parent categories"""
        path = [self.name]
        parent = self.parent_category
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent_category
        return " / ".join(path)


class Control(models.Model):
    """Individual compliance controls"""
    STATUS_CHOICES = [
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('partially_compliant', 'Partially Compliant'),
        ('not_applicable', 'Not Applicable'),
        ('under_review', 'Under Review'),
    ]

    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name='controls')
    category = models.ForeignKey(ControlCategory, on_delete=models.CASCADE, related_name='controls')
    control_id = models.CharField(max_length=200)  # Increased from 50 to 200 characters
    title = models.CharField(max_length=500)  # Increased from 300 to 500 characters
    description = models.TextField()
    recommendation = models.TextField(blank=True, null=True)
    implementation_guidance = models.TextField(blank=True)

    # Status and assessment (optional, may be system-specific in SystemControlStatus)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='under_review')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='medium')

    # Ownership and assignment
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_controls')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_controls')

    # Dates
    last_assessed = models.DateTimeField(null=True, blank=True)
    next_review_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['framework', 'control_id']
        ordering = ['framework', 'control_id']

    def __str__(self):
        return f"{self.framework.name} - {self.control_id}: {self.title}"


class ControllerProfile(models.Model):
    """Separate model for controllers who implement controls"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='controller_profile')
    department = models.CharField(max_length=100, blank=True)
    expertise_areas = models.TextField(blank=True, help_text="Areas of expertise (comma-separated)")
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department}"


class InformationSystem(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='systems')
    frameworks = models.ManyToManyField(Framework, related_name='information_systems', blank=True)
    compliance_controls = models.ManyToManyField(
        Control,
        through='SystemControlStatus',
        related_name='information_systems'
    )
    status = models.CharField(max_length=20, choices=Control.STATUS_CHOICES, default='under_review')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cached_progress = models.IntegerField(default=0)  # Cached progress for performance

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_cached_progress()

    def update_cached_progress(self):
        """Update cached progress based on control statuses"""
        control_statuses = self.systemcontrolstatus_set.all()
        if control_statuses.exists():
            total_progress = control_statuses.aggregate(Avg('progress'))['progress__avg'] or 0
            self.cached_progress = int(total_progress)
        else:
            self.cached_progress = 0
        super().save(update_fields=['cached_progress'])

    @property
    def progress(self):
        """Return cached progress"""
        return self.cached_progress

    @property
    def compliance_status(self):
        """Calculate overall compliance status"""
        control_statuses = self.systemcontrolstatus_set.all()
        if not control_statuses.exists():
            return 'under_review'

        statuses = [status.status for status in control_statuses]
        if all(status == 'compliant' for status in statuses):
            return 'compliant'
        elif all(status == 'non_compliant' for status in statuses):
            return 'non_compliant'
        elif any(status == 'partially_compliant' for status in statuses):
            return 'partially_compliant'
        else:
            return 'under_review'


class SystemControlStatus(models.Model):
    """Enhanced model for system-control relationships with new features"""
    IMPLEMENTATION_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('pending_evidence', 'Pending Evidence'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
    ]

    system = models.ForeignKey(InformationSystem, on_delete=models.CASCADE)
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, null=True, blank=True)
    control = models.ForeignKey(Control, on_delete=models.CASCADE)
    controller = models.ForeignKey(
        ControllerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Controller assigned to implement this control"
    )
    status = models.CharField(max_length=20, choices=Control.STATUS_CHOICES, default='under_review')
    implementation_status = models.CharField(max_length=20, choices=IMPLEMENTATION_STATUS_CHOICES,
                                             default='not_started')
    progress = models.IntegerField(default=0)  # 0-100
    previously_implemented = models.BooleanField(
        null=True,
        blank=True,
        help_text="Has this control been implemented before?"
    )
    deadline = models.DateTimeField(null=True, blank=True)
    evidence_upload_deadline = models.DateTimeField(null=True, blank=True)
    evidence_uploaded = models.BooleanField(default=False)
    evidence_approved = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    controller_notes = models.TextField(blank=True, help_text="Notes from the controller")
    assigned_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['system', 'framework', 'control']

    def __str__(self):
        return f"{self.system.name} - {self.framework.name if self.framework else 'No Framework'} - {self.control.control_id}"

    def save(self, *args, **kwargs):
        """Override save to set deadlines and progress based on previous implementation"""
        if self.previously_implemented is not None and not self.deadline:
            if self.previously_implemented:
                self.deadline = timezone.now() + timedelta(hours=1)
                self.evidence_upload_deadline = timezone.now() + timedelta(hours=1)
                self.progress = 50
                self.status = 'partially_compliant'
            else:
                self.deadline = timezone.now() + timedelta(days=7)
                self.evidence_upload_deadline = timezone.now() + timedelta(days=7)
                self.progress = 0
                self.status = 'non_compliant'
            self.assigned_at = timezone.now()
            self.implementation_status = 'in_progress'
        if not self.framework and self.control:
            self.framework = self.control.framework  # Set framework from control if not set
        super().save(*args, **kwargs)
        self.system.update_cached_progress()

    @property
    def is_deadline_passed(self):
        """Check if the deadline has passed"""
        if self.deadline:
            return timezone.now() > self.deadline
        return False

    @property
    def time_remaining(self):
        """Get time remaining until deadline"""
        if self.deadline:
            remaining = self.deadline - timezone.now()
            if remaining.total_seconds() > 0:
                return remaining
        return None

    def update_progress_on_evidence_upload(self):
        """Update progress when evidence is uploaded"""
        if self.evidence_uploaded and not self.evidence_approved:
            self.progress = 75
            self.status = 'partially_compliant'
            self.implementation_status = 'under_review'
        elif self.evidence_uploaded and self.evidence_approved:
            self.progress = 100
            self.status = 'compliant'
            self.implementation_status = 'completed'
            self.completed_at = timezone.now()
        self.save()


@property
def deadline_status(self):
    """Get deadline status for UI styling"""
    if not self.deadline:
        return 'no_deadline'

    time_remaining = self.time_remaining
    if not time_remaining:
        return 'overdue'

    if time_remaining.days == 0:
        if time_remaining.seconds < 7200:  # Less than 2 hours
            return 'critical'
        else:
            return 'warning'
    elif time_remaining.days <= 1:
        return 'warning'
    else:
        return 'normal'


@property
def urgency_level(self):
    """Get urgency level (0-100) based on deadline proximity"""
    if not self.deadline:
        return 0

    time_remaining = self.time_remaining
    if not time_remaining:
        return 100  # Overdue

    total_seconds = time_remaining.total_seconds()
    if total_seconds <= 7200:  # 2 hours
        return 100
    elif total_seconds <= 86400:  # 24 hours
        return 80
    elif total_seconds <= 259200:  # 3 days
        return 60
    else:
        return 20
class Evidence(models.Model):
    """Evidence supporting compliance controls"""
    EVIDENCE_TYPES = [
        ('document', 'Document'),
        ('screenshot', 'Screenshot'),
        ('policy', 'Policy'),
        ('procedure', 'Procedure'),
        ('log', 'System Log'),
        ('certificate', 'Certificate'),
        ('configuration', 'Configuration File'),
        ('other', 'Other'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_revision', 'Needs Revision'),
    ]

    system_control_status = models.ForeignKey(
        SystemControlStatus,
        on_delete=models.CASCADE,
        related_name='evidence',
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES)
    file_path = models.FileField(upload_to='evidence/')
    url = models.URLField(blank=True)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    reviewer_feedback = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_evidence'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_evidence')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(default=1)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    reviewed = models.BooleanField(default=False)
    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.system_control_status.control.control_id if self.system_control_status else 'No Control'} - {self.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.system_control_status:
            self.system_control_status.evidence_uploaded = True
            if self.approval_status == 'approved':
                self.system_control_status.evidence_approved = True
            self.system_control_status.update_progress_on_evidence_upload()


class EvidenceReview(models.Model):
    """Track evidence review history"""
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=Evidence.APPROVAL_STATUS_CHOICES)
    feedback = models.TextField()
    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f"{self.evidence.title} - {self.status} by {self.reviewer}"


class Assessment(models.Model):
    """Assessment records for controls"""
    control = models.ForeignKey(Control, on_delete=models.CASCADE, related_name='assessments')
    assessor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=Control.STATUS_CHOICES)
    findings = models.TextField()
    recommendations = models.TextField(blank=True)
    assessment_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assessment_date']

    def __str__(self):
        return f"{self.control.control_id} - {self.assessment_date.strftime('%Y-%m-%d')}"


class ComplianceReport(models.Model):
    """Generated compliance reports"""
    REPORT_TYPES = [
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('gap_analysis', 'Gap Analysis'),
        ('trend_analysis', 'Trend Analysis'),
    ]

    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    report_data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.framework.name} - {self.title}"


class ControlTag(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    controls = models.ManyToManyField(Control, related_name='tags')

    def __str__(self):
        return self.name


class ImportJob(models.Model):
    framework = models.ForeignKey(Framework, on_delete=models.CASCADE)
    imported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    details = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Import for {self.framework.name} - {self.status}"

class ControlMapping(models.Model):
    source_control = models.ForeignKey(Control, related_name='source_mappings', on_delete=models.CASCADE)
    target_control = models.ForeignKey(Control, related_name='target_mappings', on_delete=models.CASCADE, null=True, blank=True)  # Added null=True, blank=True
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['source_control', 'target_control']

    def __str__(self):
        return f"{self.source_control} -> {self.target_control}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('deadline_approaching', 'Deadline Approaching'),
        ('deadline_passed', 'Deadline Passed'),
        ('deadline_warning', 'Deadline Warning'),  # New: 3+ days before deadline
        ('deadline_overdue', 'Deadline Overdue'),  # New: Past deadline
        ('evidence_uploaded', 'Evidence Uploaded'),
        ('evidence_approved', 'Evidence Approved'),
        ('evidence_rejected', 'Evidence Rejected'),
        ('control_assigned', 'Control Assigned'),
        ('email_sent', 'Email Alert Sent'),  # New: Track email notifications
    ]

    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')  # New field
    system_control_status = models.ForeignKey(
        SystemControlStatus,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority', '-created_at']  # Order by priority first

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def get_priority_icon(self):
        """Get icon for priority level"""
        icons = {
            'low': '🔵',
            'medium': '🟡',
            'high': '🟠',
            'urgent': '🔴',
        }
        return icons.get(self.priority, '🔵')

    def get_priority_class(self):
        """Get CSS class for priority styling"""
        return f"priority-{self.priority}"


class QuestionnaireResult(models.Model):
    """Store results from the external ngrok questionnaire"""
    MATURITY_LEVELS = [
        ('initial', 'Initial (1)'),
        ('developing', 'Developing (2)'),
        ('defined', 'Defined (3)'),
        ('managed', 'Managed (4)'),
        ('optimized', 'Optimized (5)'),
    ]

    RISK_LEVELS = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('very_high', 'Very High'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questionnaire_results')
    session_id = models.CharField(max_length=100, unique=True, help_text="Unique identifier from ngrok questionnaire")

    # Overall scores
    overall_score = models.IntegerField(help_text="Overall compliance score (0-100)")
    maturity_level = models.CharField(max_length=20, choices=MATURITY_LEVELS)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS)

    # Category scores (JSON field to store flexible data)
    category_scores = models.JSONField(default=dict, help_text="Scores by category from questionnaire")
    framework_recommendations = models.JSONField(default=list, help_text="Recommended frameworks")
    gap_analysis = models.JSONField(default=dict, help_text="Gap analysis results")
    priority_actions = models.JSONField(default=list, help_text="Priority actions to take")

    # Raw questionnaire data
    raw_responses = models.JSONField(default=dict, help_text="Complete questionnaire responses")

    # Timestamps
    completed_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - Score: {self.overall_score}% ({self.completed_at.strftime('%Y-%m-%d')})"

    def get_score_color(self):
        """Return color class based on score"""
        if self.overall_score >= 80:
            return 'success'
        elif self.overall_score >= 60:
            return 'warning'
        else:
            return 'danger'

    def get_recommendations_by_priority(self):
        """Get recommendations grouped by priority"""
        high_priority = [item for item in self.priority_actions if item.get('priority') == 'high']
        medium_priority = [item for item in self.priority_actions if item.get('priority') == 'medium']
        low_priority = [item for item in self.priority_actions if item.get('priority') == 'low']

        return {
            'high': high_priority,
            'medium': medium_priority,
            'low': low_priority
        }
