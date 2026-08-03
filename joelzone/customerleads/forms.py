from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Lead, Client, Interaction, Task, Deal, CustomUser

# --- UTILITY MIXIN FOR BULK STYLING ---
class ProfessionalFormMixin:
    """
    Automatically applies professional Bootstrap form styling to any form inherits it.
    Matches inputs, selects, textareas, and special HTML5 fields.
    """
    def apply_professional_styles(self):
        for field_name, field in self.fields.items():
            # Apply styling classes based on widget type
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({'class': 'form-control', 'rows': 3})
            elif isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput, forms.URLInput)):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, (forms.DateInput, forms.DateTimeInput)):
                field.widget.attrs.update({'class': 'form-control'})
            
            # Optional: Add clear placeholders if they don't have them
            if not field.widget.attrs.get('placeholder') and field.label:
                field.widget.attrs.update({'placeholder': f'Enter {field.label.lower()}'})


# --- FORMS ---

class CustomUserCreationForm(UserCreationForm, ProfessionalFormMixin):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'job_title',
            'avatar',
        ]

    role = forms.ChoiceField(
        choices=[
            ('staff', 'Staff (Regular Staff)'),
            ('administrator', 'Administrator (Full Access)'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='staff',
        label="User Role",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False
        self.fields['job_title'].required = False
        self.apply_professional_styles()

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data['role']
        if role == 'administrator':
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = True

        if commit:
            user.save()
            if hasattr(user, 'profile'):
                if role == 'administrator':
                    user.profile.role = 'admin'
                else:
                    user.profile.role = 'sales_rep'
                user.profile.save()
        return user


class LeadForm(forms.ModelForm, ProfessionalFormMixin):
    class Meta:
        model = Lead
        fields = '__all__'
        exclude = ['created_by', 'created_at', 'updated_at', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Explicit dropdown assignments
        self.fields['sex'].widget = forms.Select(choices=[
            ('', 'Select Gender'),
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ])
        
        # Apply bulk classes to text/select fields via the mixin
        self.apply_professional_styles()

    def save(self, commit=True):
        instance = super().save(commit=False)
        extra_info = []
        fields_to_capture = [
            ('quantity', 'Quantity'), ('total', 'Total'), 
            ('russian_post_track', 'Russian Post Track'), ('delivery_time', 'Delivery Time'),
            ('index', 'Index'), ('region', 'Region'), ('city', 'City'), 
            ('district', 'District'), ('address', 'Address'), ('sex', 'Sex'), 
            ('age', 'Age'), ('comment', 'Comment'), 
            ('cancellation_reason', 'Cancellation Reason'), 
            ('return_reason', 'Return Reason'), ('spam_reason', 'Spam Reason'),
            ('additional_field_14', 'Additional Field #14'),
        ]

        for field_name, label in fields_to_capture:
            value = self.cleaned_data.get(field_name)
            if value not in (None, '', [], {}):
                extra_info.append(f"{label}: {value}")

        if extra_info:
            metadata = "\n".join(extra_info)
            header = "--- Order Metadata ---"

            if instance.notes and header in instance.notes:
                main_notes = instance.notes.split(header)[0].strip()
                instance.notes = f"{main_notes}\n\n{header}\n{metadata}" if main_notes else f"{header}\n{metadata}"
            else:
                separator = "\n\n" if instance.notes else ""
                instance.notes = f"{instance.notes}{separator}{header}\n{metadata}"

        if commit:
            instance.save()
        return instance


class DealForm(forms.ModelForm, ProfessionalFormMixin):
    class Meta:
        model = Deal
        fields = [
            'title', 'value', 'probability', 'stage',
            'expected_close_date', 'contact', 'notes'
        ]
        widgets = {
            'expected_close_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_professional_styles()


class ClientForm(forms.ModelForm, ProfessionalFormMixin):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone', 'company', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_professional_styles()


class InteractionForm(forms.ModelForm, ProfessionalFormMixin):
    class Meta:
        model = Interaction
        fields = ['lead', 'interaction_type', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_professional_styles()


class TaskForm(forms.ModelForm, ProfessionalFormMixin):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'related_lead']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_professional_styles()


class UserProfileForm(forms.ModelForm, ProfessionalFormMixin):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_professional_styles()