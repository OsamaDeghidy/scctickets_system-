# tickets/urls.py

from django.urls import path
from . import views
from .views import *

urlpatterns = [
 
     path('accounts/login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
     path('register/', views.register_view, name='register'),
    # باقي المسارات...
 
    path('create-ticket/', create_ticket_view, name='create_ticket'),
    path('', profile_view, name='profile'),
    path('logout/', logout_view, name='logout'),
    path('ticket/<int:ticket_id>/close/', close_ticket_view, name='close_ticket'),  # مسار إغلاق التذكرة
    path('supervisor_dashboard/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('assign_ticket/<int:ticket_id>/', views.assign_ticket_view, name='assign_ticket'),
    path('service_provider_dashboard/', views.service_provider_dashboard, name='service_provider_dashboard'),
    path('update_ticket_status/<int:ticket_id>/', views.update_ticket_status_view, name='update_ticket_status'),
    path('ticket/<int:ticket_id>/reopen/', reopen_ticket_view, name='reopen_ticket'),
    path('get_tickets_json/', views.get_tickets_json, name='get_tickets_json'),
    path('verify_email/', verify_email_view, name='verify_email'),
    path('resend-verification-code/', resend_verification_code_view, name='resend_verification_code'),
    path('ticket/<int:ticket_id>/', ticket_detail_view, name='ticket_detail'),

]
