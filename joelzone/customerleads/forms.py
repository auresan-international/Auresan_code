from django import forms
from django.contrib.auth import get_user_model
from .models import Lead, Client, Interaction, Task,Deal,CustomUser
from django.contrib.auth.forms import UserCreationForm


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'job_title',
            'avatar',
            'password1',
            'password2',
            'role',          # ← new field (not a real model field)
        ]

    # Virtual field for choosing role
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
        # Make avatar optional
        self.fields['avatar'].required = False
        self.fields['job_title'].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Set role based on selection
        role = self.cleaned_data['role']
        if role == 'administrator':
            user.is_superuser = True
            user.is_staff = True
        else:  # staff
            user.is_superuser = False
            user.is_staff = True  # Staff still needs is_staff=True to access admin

        if commit:
            user.save()
            # Update UserProfile role based on selection
            if hasattr(user, 'profile'):
                if role == 'administrator':
                    user.profile.role = 'admin'
                else:
                    user.profile.role = 'sales_rep'
                user.profile.save()
        return user

class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = [
            'name',
            'email',
            'phone',
            'company',
            'status',
            'priority',
            'source',
            'notes',
            # Add 'assigned_to' here later if you implement it
        ]
        
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Additional notes about the lead...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: Make some fields required or add placeholders
        self.fields['name'].widget.attrs.update({'placeholder': 'Full name of the lead'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email address'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'Phone number'})
        self.fields['company'].widget.attrs.update({'placeholder': 'Company name'})

class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = [
            'title', 'value', 'probability', 'stage',
            'expected_close_date', 'contact', 'notes'
        ]
        widgets = {
            'expected_close_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone', 'company', 'address']

class InteractionForm(forms.ModelForm):
    class Meta:
        model = Interaction
        fields = ['lead', 'interaction_type', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'related_lead']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        from django.contrib.auth.models import User
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']