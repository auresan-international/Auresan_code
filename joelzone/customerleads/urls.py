from django.urls import path
from . import views

urlpatterns = [
    # Main entry point
    path('', views.CustomLoginView.as_view(), name='login_home'),

    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Dashboard redirect logic
    path('dashboard-redirect/', views.DashboardRedirectView.as_view(), name='dashboard_redirect'),
    path('dashboard-redirect/', views.DashboardRedirectView.as_view(), name='dashboard'),

    # Admin Dashboard
    path('administrator/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # Staff Dashboard (and its partials)
    path('staff/dashboard/', views.operator_dashboard, name='staff_dashboard'),
    path('staff/create-lead/', views.create_lead_view, name='create_lead'),
    path('staff/my-conversations/', views.my_conversations_view, name='my_conversations'),
    path('staff/charts/', views.staff_charts_view, name='staff_charts'),
    
    # Automated Dialer
    path('staff/start-auto-dial/', views.start_auto_dial, name='start_auto_dial'),
    path('leads/<int:lead_id>/call/', views.call_lead, name='call_lead'),

# Admin Links
    # Generic Lead Management (example)
    path('leads/', views.LeadListView.as_view(), name='leads'),
    path('leads/create/', views.LeadCreateView.as_view(), name='lead_create'),
    path('leads/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<int:pk>/update/', views.LeadUpdateView.as_view(), name='lead_update'),
    path('leads/<int:pk>/delete/', views.LeadDeleteView.as_view(), name='lead_delete'),
           

    # User Management
    path('users/', views.UserManagementView.as_view(), name='user_management'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<int:pk>/activate/', views.UserActivateView.as_view(), name='user_activate'),
    path('users/<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='user_deactivate'),


    # Sales Pipeline
    path('sales-pipeline/', views.SalesPipelineView.as_view(), name='sales_pipeline'),

    # Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # Tasks
    path('tasks/', views.TaskListView.as_view(), name='tasks'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),

    # Interactions
    path('interactions/', views.InteractionListView.as_view(), name='interactions'),
    path('interactions/create/', views.InteractionCreateView.as_view(), name='interaction_create'),

    # Analytics & Reports
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('reports/', views.ReportsView.as_view(), name='reports'),

    # Client Management
    path('clients/', views.ClientListView.as_view(), name='clients'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),

    # System & Features
    path('activity-logs/', views.ActivityLogView.as_view(), name='activity_logs'),
    path('email-notifications/', views.EmailNotificationsView.as_view(), name='email_notifications'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('api-management/', views.APIManagementView.as_view(), name='api_management'),
    path('help-support/', views.HelpSupportView.as_view(), name='help_support'),

    # Top Navigation
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('quick-add/', views.QuickAddView.as_view(), name='quick_add'),
]