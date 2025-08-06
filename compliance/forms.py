from django import forms
from .models import InformationSystem, Framework, Control, SystemControlStatus, Evidence, EvidenceReview, Organization,ControllerProfile

class SystemCreationForm(forms.ModelForm):
    class Meta:
        model = InformationSystem
        fields = ['name', 'description', 'organization']  # Remove 'frameworks'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if InformationSystem.objects.filter(name__iexact=name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("A system with this name already exists.")
        return name



class ControlAssignmentForm(forms.Form):
    """Form for assigning controls to a system within a framework"""

    def __init__(self, *args, **kwargs):
        framework = kwargs.pop('framework', None)
        super().__init__(*args, **kwargs)

        # Filter controls by framework if provided
        if framework:
            self.fields['controls'].queryset = Control.objects.filter(framework=framework)
            self.fields['controls'].label = f"Controls for {framework.name}"

    controls = forms.ModelMultipleChoiceField(
        queryset=Control.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select controls to assign to this system"
    )
    controller = forms.ModelChoiceField(
        queryset=ControllerProfile.objects.filter(is_active=True),
        required=False,
        empty_label="Select a controller (optional)",
        help_text="Assign a controller to manage these controls"
    )
    previously_implemented = forms.ChoiceField(
        choices=[('', 'Select an option'), ('yes', 'Yes'), ('no', 'No')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Have you implemented these controls before?"
    )
class EvidenceUploadForm(forms.ModelForm):
    class Meta:
        model = Evidence
        fields = ['title', 'description', 'evidence_type', 'file_path', 'url']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'evidence_type': forms.Select(),
        }

class EvidenceReviewForm(forms.ModelForm):
    class Meta:
        model = EvidenceReview
        fields = ['status', 'feedback']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4}),
        }

class SystemControlStatusForm(forms.ModelForm):
    class Meta:
        model = SystemControlStatus
        fields = ['status', 'progress', 'deadline', 'evidence_upload_deadline', 'notes', 'controller_notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'controller_notes': forms.Textarea(attrs={'rows': 4}),
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'evidence_upload_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class FrameworkAssignmentForm(forms.Form):
    """Form for assigning frameworks to a system"""

    def __init__(self, *args, **kwargs):
        system = kwargs.pop('system', None)
        super().__init__(*args, **kwargs)

        if system:
            # Get already assigned frameworks for this system
            # Use the correct relationship: system.frameworks.all() instead of Framework.objects.filter(system=system)
            assigned_framework_ids = system.frameworks.all().values_list('id', flat=True)

            # Filter out already assigned frameworks
            self.fields['framework'].queryset = Framework.objects.exclude(
                id__in=assigned_framework_ids
            )

    framework = forms.ModelChoiceField(
        queryset=Framework.objects.all(),
        empty_label="Select a framework to assign",
        help_text="Choose a framework to assign to this system"
    )
