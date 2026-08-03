from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from .models import CallLog, Lead, Client, Interaction, Task, UserProfile, Deal
from .forms import CustomUserCreationForm, LeadForm, ClientForm, InteractionForm, TaskForm, DealForm
import africastalking
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserChangeForm
User = get_user_model()
from .utils import voice
from django.db import transaction
from django.utils.decorators import method_decorator
from .utils import format_phone_to_e164


def build_operator_chart_data():
    labels = ['Time in calls', 'Idle', 'On break', 'On education', 'Calls received', 'Not answered', 'Chats handled']
    values = [42, 18, 8, 5, 20, 4, 13]
    colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#64748b', '#14b8a6']
    total = sum(values)
    segments = []
    start = 0

    for value, color in zip(values, colors):
        percentage = (value / total * 100) if total else 0
        end = start + percentage
        segments.append(f"{color} {start:.1f}% {end:.1f}%")
        start = end

    stats = []
    for label, value, color in zip(labels, values, colors):
        pct = round((value / total * 100), 1) if total else 0
        stats.append({'label': label, 'value': value, 'color': color, 'percentage': pct})

    return {
        'labels': labels,
        'values': values,
        'colors': colors,
        'stats': stats,
        'style': f"conic-gradient({' ,'.join(segments)});",
        'total': total,
    }


def build_operator_conversations(request):
    call_logs = CallLog.objects.filter(lead__created_by=request.user).select_related('lead').order_by('-created_at')[:8]
    interactions = Interaction.objects.filter(created_by=request.user).select_related('lead').order_by('-interaction_date')[:8]

    items = []
    for call_log in call_logs:
        items.append({
            'id': f'call-{call_log.id}',
            'kind': 'call',
            'title': f"Call with {call_log.lead.name}",
            'summary': call_log.status.replace('_', ' ').title() if call_log.status else 'Recorded call session',
            'timestamp': call_log.created_at,
            'recording_url': '#',
        })

    for interaction in interactions:
        items.append({
            'id': f'interaction-{interaction.id}',
            'kind': 'chat' if interaction.interaction_type == 'other' else 'interaction',
            'title': f"{interaction.get_interaction_type_display()} with {interaction.lead.name}",
            'summary': interaction.notes[:140] if interaction.notes else 'Conversation notes captured',
            'timestamp': interaction.interaction_date,
            'recording_url': None,
        })

    items.sort(key=lambda item: item['timestamp'], reverse=True)
    return items[:12]


# Create your views here.
def index(request):
    return render(request, 'base.html')

class DashboardView(TemplateView):
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # You can add dynamic data here
        context.update({
            'selected_togarties': '49 / 657',
            'vegla_requisite': '0',
            'vegla_on_regul': '126',
            'basiced_togarties': '0 / 271',
            'returned_togarties': '30 / 217',
        })
        return context

def dashboard_view(request):
    return render(request, 'dashboard.html', {
        'selected_togarties': '49 / 657',
        'vegla_requisite': '0',
        'vegla_on_regul': '126',
        'basiced_togarties': '0 / 271',
        'returned_togarties': '30 / 217',
    })

# Authentication Views


class CustomLoginView(LoginView):
    template_name = 'accounts/login_form.html'

    def get_success_url(self):
        user = self.request.user
        
        if user.is_superuser:
            return reverse('admin_dashboard')

        try:
            profile = user.profile  # assuming profile is always created
            role = profile.role
        except (AttributeError, UserProfile.DoesNotExist):
            role = 'sales_rep'  # fallback

        if role == 'admin':
            return reverse('admin_dashboard')
        else:
            return reverse('staff_dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Welcome back, {self.request.user.get_full_name() or self.request.user.username}!'
        )
        return response

class CustomLogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out successfully.')
        return redirect('login')

    def post(self, request):
        return self.get(request)


# Optional: Keep this for manual redirects or future use
@method_decorator(login_required, name='dispatch')
class DashboardRedirectView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser:
            return redirect('admin_dashboard')
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return redirect('admin_dashboard')
        else:
            return redirect('staff_dashboard')



class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'admin/dashboard.html'

    def test_func(self):
        # Only allow users with role 'administrator'
        return self.request.user.is_superuser or (
            hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'admin'
        )

    def handle_no_permission(self):
        messages.error(self.request, "Administrator access required.")
        return redirect('staff_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_leads = Lead.objects.all()
        total_leads = all_leads.count()

        # Stats cards
        new_leads_count = all_leads.filter(status='new').count()
        # The view `convert_lead_to_client` uses 'converted'.
        # We'll assume 'converted' is the status for a lead that became a client.
        converted_leads_count = all_leads.filter(status='converted').count()
        hot_leads_count = all_leads.filter(
            priority='high',
        ).exclude(
            status__in=['converted', 'closed', 'lost']
        ).count()

        # Pipeline overview & leads by status
        status_counts_query = all_leads.values('status').annotate(count=Count('id'))
        status_counts = {item['status']: item['count'] for item in status_counts_query}

        # Recent activities
        recent_leads = all_leads.order_by('-created_at')[:5]
        recent_tasks = Task.objects.filter(completed=False).order_by('due_date')[:5]

        # Lead sources
        leads_by_source = all_leads.values('source').annotate(count=Count('id')).order_by('-count')

        # Performance Metrics
        conversion_rate = (converted_leads_count / total_leads * 100) if total_leads > 0 else 0

        context.update({
            'total_leads': total_leads,
            'new_leads': new_leads_count,
            'converted_leads': converted_leads_count,
            'hot_leads': hot_leads_count,
            'status_counts': status_counts,
            'recent_leads': recent_leads,
            'recent_tasks': recent_tasks,
            'leads_by_source': leads_by_source,
            'conversion_rate': conversion_rate,
        })

        return context

# ===================================  Leads ========================================
# leads/views.py
class LeadListView(LoginRequiredMixin, ListView):
    model = Lead
    template_name = 'leads/leadslist.html'
    context_object_name = 'page_obj'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        # Change 'assigned_to' → 'created_by'
        queryset = Lead.objects.select_related('created_by').order_by('-created_at')

        # Search
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(email__icontains=q) |
                Q(phone__icontains=q) |
                Q(company__icontains=q) |
                Q(notes__icontains=q)
            )

        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Priority filter
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        # Assigned to filter → now filters on created_by
        created_by = self.request.GET.get('assigned_to')  # keep form name the same
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_leads = Lead.objects.all()
        today = timezone.now()
        week_ago = today - timedelta(days=7)

        context.update({
            'total_leads': all_leads.count(),
            'new_this_week': all_leads.filter(created_at__gte=week_ago).count(),
            'converted': all_leads.filter(status='converted').count(),
            'lost': all_leads.filter(status='lost').count(),
            'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        })
        return context


class LeadDetailView(LoginRequiredMixin, DetailView):
    model = Lead
    template_name = 'leads/lead_detail.html'
    context_object_name = 'lead'

class LeadCreateView(LoginRequiredMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = 'leads/create_lead.html'
    success_url = reverse_lazy('leads')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Lead created successfully!')
        return super().form_valid(form)

class LeadUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = 'leads/lead_form.html'
    success_url = reverse_lazy('leads')
    
    def form_valid(self, form):
        messages.success(self.request, 'Lead updated successfully!')
        return super().form_valid(form)

class LeadDeleteView(LoginRequiredMixin, DeleteView):
    model = Lead
    template_name = 'leads/lead_confirm_delete.html'
    success_url = reverse_lazy('leads')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Lead deleted successfully!')
        return super().delete(request, *args, **kwargs)

# ================================================ User Management =================================
class UserManagementView(LoginRequiredMixin, ListView):
    template_name = 'users/user_management.html'
    paginate_by = 15

    def get_queryset(self):
        return User.objects.select_related().order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        # Apply filters
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            )

        is_active = self.request.GET.get('is_active')
        if is_active in ('0', '1'):
            queryset = queryset.filter(is_active=bool(int(is_active)))

        is_staff = self.request.GET.get('is_staff')
        if is_staff in ('0', '1'):
            is_staff_bool = bool(int(is_staff))
            if is_staff_bool:
                queryset = queryset.filter(is_staff=True)
            else:
                queryset = queryset.filter(is_staff=False, is_superuser=False)

        # Pagination
        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            'page_obj': page_obj,
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'new_this_month': User.objects.filter(
                date_joined__gte=timezone.now().replace(day=1)
            ).count(),
            'query_string': self.request.GET.urlencode(),
        })

        return context


class UserCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = get_user_model()
    form_class = CustomUserCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('user_management')
    success_message = "User created successfully!"

    def form_valid(self, form):
        # The role logic is already handled in form.save()
        return super().form_valid(form)
    
#-------------------------------------------------------- Detail view ----------------

class UserDetailView(LoginRequiredMixin, DetailView):
    model = get_user_model()
    template_name = 'users/user_detail.html'
    context_object_name = 'user'
    pk_url_kwarg = 'pk'

#------------------------------------------------------------ Update view ----------------

class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserChangeForm  # or create a custom form without password field
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('user_management')
    success_message = "User '%(username)s' was successfully updated."
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Remove password field from update form
        form.fields.pop('password', None)
        return form

#------------------------------------------------------------ delete view ----------------

class UserDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('user_management')
    success_message = "User was successfully deleted."
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
    
#------------------------------------------------------------ Activate user view ----------------
class UserActivateView(LoginRequiredMixin, View):
    """
    Activates a user account.
    """
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        
        if user.is_active:
            messages.info(request, f"User '{user.username}' is already active.")
        else:
            user.is_active = True
            user.save()
            messages.success(request, f"User '{user.username}' has been activated successfully.")
        
        return redirect('user_management')

#------------------------------------------------------------ Deactivate user view ----------------

class UserDeactivateView(LoginRequiredMixin, View):
    """
    Deactivates a user account (prevents self-deactivation).
    """
    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        
        # Prevent deactivating yourself
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect('user_management')
        
        if not user.is_active:
            messages.info(request, f"User '{user.username}' is already inactive.")
        else:
            user.is_active = False
            user.save()
            messages.success(request, f"User '{user.username}' has been deactivated successfully.")
        
        return redirect('user_management')

class UserProfileView(LoginRequiredMixin, UpdateView):
    template_name = 'users/profile.html'
    success_url = reverse_lazy('profile')
    
    def get_object(self):
        return self.request.user
    
    def get_form_class(self):
        from .forms import UserProfileForm
        return UserProfileForm

# ============================================================== Sales Pipeline View------------
class SalesPipelineView(LoginRequiredMixin, ListView):
    template_name = 'sales/pipeline.html'  # Adjust if your template is in a different folder
    context_object_name = 'deals'
    paginate_by = 0  # We don't paginate Kanban – we show all filtered deals

    def get_queryset(self):
        queryset = Deal.objects.select_related('contact', 'owner').order_by('stage', '-value')

        # Search filter
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(contact__name__icontains=q) |
                Q(contact__email__icontains=q) |
                Q(contact__company__icontains=q) |
                Q(notes__icontains=q)
            )

        # Stage filter
        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(stage=stage)

        # Owner filter
        owner = self.request.GET.get('owner')
        if owner:
            queryset = queryset.filter(owner_id=owner)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deals = self.object_list

        # Group deals by stage (dictionary: stage_value → queryset of deals in that stage)
        deals_by_stage = {}
        for stage_value, stage_display in Deal.STAGE_CHOICES:
            deals_by_stage[stage_value] = deals.filter(stage=stage_value)

        # Calculate stats
        today = timezone.now()
        this_month_start = today.replace(day=1)

        total_value = deals.aggregate(total=Sum('value'))['total'] or 0
        won_this_month = deals.filter(
            stage='closed_won',  # Adjust if your won stage is different
            updated_at__gte=this_month_start
        ).aggregate(total=Sum('value'))['total'] or 0

        open_deals = deals.exclude(stage__in=['closed_won', 'closed_lost']).count()
        lost_deals = deals.filter(stage='closed_lost').count()

        context.update({
            'stages': Deal.STAGE_CHOICES,
            'deals_by_stage': deals_by_stage,
            'total_pipeline_value': total_value,
            'won_this_month': won_this_month,
            'open_deals': open_deals,
            'lost_deals': lost_deals,
            'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        })

        return context
    

class DealCreateView(LoginRequiredMixin, CreateView):
    model = Deal
    form_class = DealForm
    template_name = 'sales/deal_form.html'  # create this template
    success_url = reverse_lazy('sales_pipeline')  # redirect back to pipeline

    def form_valid(self, form):
        # Automatically set the current user as owner
        form.instance.owner = self.request.user
        return super().form_valid(form)
    
# Client Management Views
class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20

class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'

# Interaction Management Views
class InteractionListView(LoginRequiredMixin, ListView):
    model = Interaction
    template_name = 'interactions/interaction_list.html'
    context_object_name = 'interactions'
    paginate_by = 20
    
    def get_queryset(self):
        return Interaction.objects.all().order_by('-interaction_date')
    
# ---------------------------------------------Interactions --------------------
class InteractionCreateView(LoginRequiredMixin, CreateView):
    model = Interaction
    form_class = InteractionForm
    template_name = 'interactions/interaction_form.html'
    success_url = reverse_lazy('interactions')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Interaction logged successfully!')
        return super().form_valid(form)

def format_phone_to_e164(phone_number):
    """Helper to convert local numbers to E.164 format for Africa's Talking."""
    if not phone_number:
        return None
    # Remove all non-numeric characters
    clean_number = "".join(filter(str.isdigit, phone_number))
    # Handle Kenyan numbers starting with 0 (Standard for AT sandbox/Kenya)
    if clean_number.startswith('0') and len(clean_number) == 10:
        return "+254" + clean_number[1:]
    if not phone_number.startswith('+'):
        return "+" + clean_number
    return phone_number

# =======================================auto dail-===========================

from .models import Lead, CallLog
from .utils import format_phone_to_e164  # Ensure this utility handles 0700... formats properly

africastalking.initialize(settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY)
voice = africastalking.Voice

@login_required
def start_auto_dial(request):
    with transaction.atomic():
        # 1. Fetch the next new lead using a row-level lock
        next_lead = (
            Lead.objects.select_for_update()
            .filter(status='new')
            .order_by('created_at')
            .first()
        )

        # Handle case where queue is empty
        if not next_lead:
            return HttpResponse(
                '<button class="btn btn-warning" disabled>'
                '<i class="fas fa-exclamation-triangle"></i> No new leads in queue.'
                '</button>'
            )

        # 2. Format the phone number to E.164
        formatted_phone = format_phone_to_e164(next_lead.phone)

        # CRITICAL PROTECTION: Catch cases where formatting results in empty, "+", or too short string
        if not formatted_phone or formatted_phone == "+" or len(formatted_phone) < 10:
            # Move the lead out of 'new' so it doesn't brick your auto-dial loop
            next_lead.status = 'failed'
            next_lead.save()
            
            return HttpResponse(
                f'<div class="alert alert-warning mb-0">'
                f'<i class="fas fa-times-circle"></i> Skipped <strong>{next_lead.name}</strong> (Invalid phone: {next_lead.phone})'
                f'</div>'
            )

        # 3. Trigger the Outbound Call via AfricasTalking
        try:
            call_response = voice.call(
                settings.AFRICASTALKING_VIRTUAL_NUMBER,
                formatted_phone
            )

            # Safely parse the sessionId from the response payload
            session_id = None
            try:
                if isinstance(call_response, dict):
                    session_id = call_response.get("entries", [{}])[0].get("sessionId")
                else:
                    session_id = call_response['entries'][0]['sessionId']
            except Exception:
                pass

            # 4. Update Lead Status on success
            next_lead.status = 'contacted'
            next_lead.last_contacted_at = timezone.now()
            next_lead.save()

            # 5. Log the Action
            CallLog.objects.create(
                lead=next_lead,
                session_id=session_id or "",
                status="initiated",
                direction="outbound"
            )

            # 6. Return Success UI snippet back to HTMX
            return HttpResponse(
                f'<div class="alert alert-success d-flex align-items-center mb-0">'
                f'<i class="fas fa-spinner fa-spin me-2"></i> Calling <strong>{next_lead.name}</strong> ({formatted_phone})...'
                f'</div>'
            )

        except Exception as e:
            # SAFETY FALLBACK: If AT API rejects the call, mark lead status to prevent infinite loop
            next_lead.status = 'failed'
            next_lead.save()

            # Return Error UI snippet back to HTMX if SDK or networking fails
            return HttpResponse(
                f'<div class="alert alert-danger mb-0">'
                f'<i class="fas fa-exclamation-circle"></i> Call failed for {next_lead.name}: {str(e)}'
                f'</div>'
            )
# Task Management Views
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    
    def get_queryset(self):
        return Task.objects.filter(assigned_to=self.request.user).order_by('-due_date')

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    success_url = reverse_lazy('tasks')
    
    def form_valid(self, form):
        form.instance.assigned_to = self.request.user
        messages.success(self.request, 'Task created successfully!')
        return super().form_valid(form)

# Analytics & Reports
class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic analytics data
        context['leads_by_source'] = Lead.objects.values('source').annotate(count=Count('id'))
        context['leads_by_status'] = Lead.objects.values('status').annotate(count=Count('id'))
        context['conversion_rate'] = self.calculate_conversion_rate()
        
        return context
    
    def calculate_conversion_rate(self):
        total_leads = Lead.objects.count()
        converted_leads = Lead.objects.filter(status='converted').count()
        return (converted_leads / total_leads * 100) if total_leads > 0 else 0

class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/reports.html'

# Activity History
class ActivityLogView(LoginRequiredMixin, ListView):
    template_name = 'activity/activity_logs.html'
    context_object_name = 'activities'
    paginate_by = 50
    
    def get_queryset(self):
        # This would typically come from an ActivityLog model
        # For now, combine recent actions from different models
        return []



# System Features
class EmailNotificationsView(LoginRequiredMixin, TemplateView):
    template_name = 'notifications/email_notifications.html'

class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'settings/settings.html'

class APIManagementView(LoginRequiredMixin, TemplateView):
    template_name = 'api/api_management.html'

class HelpSupportView(LoginRequiredMixin, TemplateView):
    template_name = 'help/help_support.html'


# Additional Features
class NotificationListView(LoginRequiredMixin, ListView):
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    
    def get_queryset(self):
        # Return user's notifications
        return []

class QuickAddView(LoginRequiredMixin, TemplateView):
    template_name = 'quick_add/quick_add.html'

# Function-based views for simple actions
@login_required
def convert_lead_to_client(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    client = Client.objects.create(
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        converted_from=lead
    )
    lead.status = 'converted'
    lead.save()
    messages.success(request, f'Lead {lead.name} converted to client successfully!')
    return redirect('clients')

@login_required
def mark_task_complete(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
    task.completed = True
    task.save()
    messages.success(request, 'Task marked as complete!')
    return redirect('tasks')


# =============================================== STAFF DASHBOARD ============================================
from datetime import timedelta
from decimal import Decimal

@login_required
def operator_dashboard(request):
    # 1. Get current time context
    now = timezone.now()
    period = request.GET.get('period', 'today')

    # 2. Base querysets
    # For the table: Always fetch EVERY SINGLE lead across your whole system
    all_leads_table = Lead.objects.all().order_by('-created_at')
    
    # For metrics: We filter this queryset down based on the active period tab
    metrics_query = Lead.objects.all()

    # 3. Apply Date Adjustments for Metrics Filter
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        metrics_query = metrics_query.filter(created_at__gte=start_date)
        
    elif period == '7days':
        start_date = now - timedelta(days=7)
        metrics_query = metrics_query.filter(created_at__gte=start_date)
        
    elif period == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        metrics_query = metrics_query.filter(created_at__gte=start_date)
        
    elif period == 'last_month':
        # Calculate the first and last day of previous month
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_last_month = first_of_this_month - timedelta(seconds=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        metrics_query = metrics_query.filter(
            created_at__gte=first_day_of_last_month,
            created_at__lte=last_day_of_last_month
        )

# 4. Aggregate Metric Calculations (Optimized to hit DB once)
    aggregates = metrics_query.aggregate(
        # CHANGED: renamed from 'total' to 'total_count' to avoid field name collision
        total_count=Count('id'),
        
        # Counts based on your custom Lead status tags
        dialing_cnt=Count('id', filter=Q(status='dialing')),
        approved_cnt=Count('id', filter=Q(status='approved')),  
        cancelled_cnt=Count('id', filter=Q(status='cancelled')),
        recall_cnt=Count('id', filter=Q(status='recall')),
        
        # Financial analytics - now safely points to your model's actual 'total' field
        avg_check=Avg('total', filter=Q(total__gt=0))  
    )

    # Extract aggregated data safely with modified key name
    total_leads = aggregates['total_count'] or 0
    dialing = aggregates['dialing_cnt'] or 0
    qualified_count = aggregates['approved_cnt'] or 0
    lost_count = aggregates['cancelled_cnt'] or 0
    recalls = aggregates['recall_cnt'] or 0
    avg_check_val = aggregates['avg_check'] or 0.0000

    # 5. Calculate Percentages for Dashboard Layouts
    clean_approve = "0%"
    cancellations = "0%"
    if total_leads > 0:
        clean_approve = f"{(qualified_count / total_leads) * 100:.1f}%"
        cancellations = f"{(lost_count / total_leads) * 100:.1f}%"

    # Mock placeholders for business logic aggregates not strictly mapping to a Lead field
    # Replace these formulas with your specific phone-system metrics or profile models if tracked
    leads_per_hour = round(total_leads / 8, 1) if period == 'today' else round(total_leads / 40, 1)
    buyout = "0%" if total_leads == 0 else f"{(qualified_count / total_leads) * 92:.1f}%" 
    bonuses = f"{qualified_count * 5.50:.2f} c.u."  # Base structural multiplier example

    # 6. Format Financial Currency Checks
    average_check = f"${avg_check_val:,.2f}"

    # 7. Construct Full UI Template Context Map
    context = {
        # Master table contains EVERYTHING
        'leads': all_leads_table,
        
        # Control & Card tracking filters
        'period': period,
        'total_leads': total_leads,
        'dialing': dialing,
        'clean_approve': clean_approve,
        'qualified_count': qualified_count,
        'cancellations': cancellations,
        'lost_count': lost_count,
        'recalls': recalls,
        'leads_per_hour': leads_per_hour,
        'buyout': buyout,
        'average_check': average_check,
        'bonuses': bonuses,
        'active_tab': 'dashboard',
        'content_template': 'dashboard/partials/dashboard.html',
        'chart_data': build_operator_chart_data(),
        'conversation_items': build_operator_conversations(request),
    }

    # 8. Clean HTMX Swapping Engine routing
    if request.htmx:
        return render(request, 'dashboard/partials/dashboard.html', context)
    return render(request, 'dashboard/staff.html', context)

@login_required
def create_lead_view(request):
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.created_by = request.user
            if not lead.status:
                lead.status = 'new'
            lead.save()

            messages.success(request, f"Lead '{lead.name}' created successfully!")

            if request.htmx:
                # return ONLY partial HTML, not full dashboard
                form = LeadForm()  # reset form
                return render(request, 'leads/create_lead.html', {
                    'form': form,
                    'success': True
                })

            return redirect('staff_dashboard')

    else:
        form = LeadForm()

    return render(request, 'leads/create_lead.html', {'form': form})

@login_required
def call_lead(request, lead_id):
    lead = Lead.objects.get(id=lead_id)

    try:
        response = voice.call(
            callerId=settings.AFRICASTALKING_VIRTUAL_NUMBER,
            callAttempts=[
                {
                    "phoneNumber": lead.phone
                }
            ]
        )

        return JsonResponse({
            "success": True,
            "message": "Call initiated",
            "response": str(response)
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        })

@login_required
def my_conversations_view(request):
    """
    Displays a list of recent interactions for the logged-in user.
    Designed for HTMX.
    """
    conversations = Interaction.objects.filter(
        created_by=request.user
    ).select_related('lead').order_by('-interaction_date')[:50]

    context = {
        'conversations': conversations,
        'conversation_items': build_operator_conversations(request),
        'active_tab': 'conversations',
        'content_template': 'dashboard/partials/my_conversations.html',
    }

    if request.htmx:
        return render(request, 'dashboard/partials/my_conversations.html', context)

    return render(request, 'dashboard/staff.html', context)


@login_required
def staff_charts_view(request):
    context = {
        'active_tab': 'charts',
        'content_template': 'dashboard/partials/charts.html',
        'chart_data': build_operator_chart_data(),
    }

    if request.htmx:
        return render(request, 'dashboard/partials/charts.html', context)

    return render(request, 'dashboard/staff.html', context)