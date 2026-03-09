from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Lead, Client, Interaction, Task, UserProfile
from .forms import CustomUserCreationForm, LeadForm, ClientForm, InteractionForm, TaskForm,DealForm
from django.contrib.auth.views import LoginView, LogoutView
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from .models import Deal

from django.contrib.auth import get_user_model
User = get_user_model()


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

from django.urls import reverse

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

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


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


from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

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

# -------------------------------------------------------- create user --------------
from django.contrib.auth.forms import UserCreationForm
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages

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
from django.views.generic import DetailView

class UserDetailView(LoginRequiredMixin, DetailView):
    model = get_user_model()
    template_name = 'users/user_detail.html'
    context_object_name = 'user'
    pk_url_kwarg = 'pk'

#------------------------------------------------------------ Update view ----------------
from django.views.generic import UpdateView
from django.contrib.auth.forms import UserChangeForm

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
from django.views.generic import DeleteView

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
    
from twilio.rest import Client
from django.conf import settings
from django.http import JsonResponse
def initiate_call(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    call = client.calls.create(
        url='http://demo.twilio.com/docs/voice.xml', # Your TwiML instructions
        to=lead.phone,
        from_=settings.TWILIO_PHONE_NUMBER
    )
    return JsonResponse({'status': 'success', 'call_sid': call.sid})

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

def operator_dashboard(request):
    period = request.GET.get('period', 'today')  # default: today

    today = timezone.now().date()
    start_date = today

    if period == 'today':
        start_date = today
    elif period == '7days':
        start_date = today - timedelta(days=7)
    elif period == 'this_month':
        start_date = today.replace(day=1)
    elif period == 'last_month':
        first_this_month = today.replace(day=1)
        start_date = (first_this_month - timedelta(days=1)).replace(day=1)
        end_date = first_this_month - timedelta(days=1)
    else:
        period = 'today' 

    end_date = today if period != 'last_month' else end_date

    leads = Lead.objects.filter(
        created_by=request.user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date if 'end_date' in locals() else today
    )

    # ────────────────────────────────────────────────
    # Calculate metrics
    # ────────────────────────────────────────────────

    total_leads = leads.count()

    dialing = leads.filter(status='contacted').count()

    qualified_or_better = leads.filter(
        status__in=['qualified', 'proposal', 'negotiation', 'closed']
    ).count()
    clean_approve_pct = round((qualified_or_better / total_leads * 100) if total_leads > 0 else 0, 1)

    cancellations = leads.filter(status='lost').count()
    cancellations_pct = round((cancellations / total_leads * 100) if total_leads > 0 else 0, 1)
    recalls = 0

    leads_per_hour = 0
    if total_leads > 0 and period == 'today':
        first_lead_time = leads.order_by('created_at').first()
        if first_lead_time:
            hours_active = max((timezone.now() - first_lead_time.created_at).total_seconds() / 3600, 1)
            leads_per_hour = round(total_leads / hours_active, 1)

    buyout_pct = 0

    avg_check = Deal.objects.filter(
        owner=request.user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date if 'end_date' in locals() else today
    ).aggregate(avg=Avg('value'))['avg'] or Decimal('0.00')

    bonuses = Decimal('0.00')

    context = {
        'period': period,
        'total_leads': total_leads,
        'dialing': dialing,
        'clean_approve': f"{clean_approve_pct}%",
        'cancellations': f"{cancellations_pct}%",
        'recalls': recalls,
        'leads_per_hour': leads_per_hour,
        'buyout': f"{buyout_pct}%",
        'average_check': f"${avg_check:,.2f}",
        'bonuses': f"{bonuses:,.2f} c.u.",
        # Add counts for the template
        'qualified_count': qualified_or_better,
        'lost_count': cancellations,
    }

    if request.htmx:
        # For HTMX requests, return only the partial that needs to be updated.
        return render(request, 'dashboard/partials/dashboard.html', context)

    # For regular page loads, return the full page.
    return render(request, 'dashboard/staff.html', context)

@login_required
def create_lead_view(request):
    """
    Handles GET requests to show a lead creation form and
    POST requests to create a new lead. Designed for HTMX.
    """
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.created_by = request.user
            lead.save()
            messages.success(request, f"Lead '{lead.name}' created successfully!")
            # A full redirect is the simplest way to refresh state after creation
            return redirect('staff_dashboard')
    else:
        form = LeadForm()

    context = {'form': form}

    if request.htmx:
        return render(request, 'dashboard/partials/create_lead.html', context)

    # For direct access, just go to the main dashboard page
    return redirect('staff_dashboard')

@login_required
def my_conversations_view(request):
    """
    Displays a list of recent interactions for the logged-in user.
    Designed for HTMX.
    """
    conversations = Interaction.objects.filter(
        created_by=request.user
    ).select_related('lead').order_by('-interaction_date')[:50]

    context = {'conversations': conversations}

    if request.htmx:
        return render(request, 'dashboard/partials/my_conversations.html', context)

    # For direct access, just go to the main dashboard page
    return redirect('staff_dashboard')