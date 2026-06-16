from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from campus_app import views 
from django.contrib.auth import views as auth_views 

urlpatterns = [
    path('debug/check-database/', views.debug_database_view, name='debug_database_view'),

    # ==========================================
    # ADMIN & ADVISER URLS
    # ==========================================
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/login/', views.staff_login_view, name='staff_login'),
    path('admin/logout/', views.staff_logout_view, name='admin_logout'),
    
    path('admin/manage-accounts/', views.manage_accounts_view, name='manage_accounts'),
    path('admin/manage-organizers/', views.manage_organizers_view, name='manage_organizers'),
    path('admin/audit-logs/', views.admin_audit_logs, name='admin_audit_logs'),
    path('admin/notifications/', views.admin_notifications_view, name='admin_notifications'),
    path('admin/api/notifications/', views.get_admin_notifications_api, name='admin_api_notifications'),
    
    # 🟢 LINKS PARA SA HISTORY AT ORG MONITOR NG ADMIN 🟢
    path('admin/account-history/', views.account_history_view, name='account_history'),
    path('admin/org-monitor/', views.org_monitor_view, name='org_monitor'),
    path('admin/org-monitor/detail/', views.admin_feedback_detail, name='admin_feedback_detail'),
    
    # 🟢 API PARA SA MANAGE ACCOUNTS (DEACTIVATE/CREATE) 🟢
    path('admin/api/student-action/', views.student_api_action, name='student_api_action'),
    path('admin/api/organizer-action/', views.organizer_api_action, name='organizer_api_action'),
    
    path('admin/event-approvals/', views.event_approvals_view, name='event_approvals'),
    
    # 🟢 BAGONG API PARA SA ADMIN APPROVE/REJECT EVENTS 🟢
    path('admin/api/event-action/', views.admin_api_action, name='admin_api_action'),

    path('django-admin/', admin.site.urls),

    path('adviser/dashboard/', views.adviser_dashboard, name='adviser_dashboard'),
    path('adviser/history/', views.adviser_history, name='adviser_history'),
    path('adviser/api/notifications/', views.get_adviser_notifications_api, name='adviser_api_notifications'),

    # 🟢 BAGONG API PARA SA ADVISER APPROVE/REJECT 🟢
    path('adviser/api/action/', views.adviser_api_action, name='adviser_api_action'),

    # API FOR UPDATING USER LOCATION
    path('api/update-user-location/', views.update_user_location, name='update_user_location'),

    # ==========================================
    # MAIN PORTAL (INDEX)
    # ==========================================
    path('', views.index, name='index'),
    path('portal/login/', views.portal_login_view, name='portal_login'),
    path('portal/logout/', views.portal_logout_view, name='portal_logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('api/verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('api/complete-password-reset/', views.complete_password_reset, name='complete_password_reset'),
    path('api/poll-organizer-password/', views.poll_organizer_password, name='poll_organizer_password'),

    # ==========================================
    # STUDENT URLS
    # ==========================================
    path('student/register', views.student_register, name='student_register'),
    path('student/generate-password', views.generate_student_password, name='generate_student_password'),
    path('student/verify-password', views.verify_student_password, name='verify_student_password'),
    path('student/update-password', views.update_student_password, name='update_student_password'),
    path('student/update-profile', views.update_student_profile, name='update_student_profile'),
    path('student/update-face', views.update_student_face, name='update_student_face'),
    path('student/update-notif-preference', views.update_notification_preference, name='update_notification_preference'),
    path('student/api/notifications/', views.get_student_notifications_api, name='student_api_notifications'),
    path('student/record-attendance', views.record_attendance, name='record_attendance_student'),
    path('record-attendance/', views.record_attendance, name='record_attendance'),
    path('student/submit-evaluation', views.submit_evaluation, name='submit_evaluation'),
    path('student/dashboard', views.student_homepage, name='student_homepage'),
    path('student/school-events', views.student_school_events, name='student_school_events'),
    path('student/calendar', views.student_event_calendar, name='student_event_calendar'),
    path('student/evaluation', views.student_evaluation, name='student_evaluation'),
    path('student/evaluation-form', views.student_evaluation_form, name='student_evaluation_form'),
    path('student/profile', views.student_profile, name='student_profile'),
    path('student/event-history', views.student_event_history, name='student_event_history'),
    path('student/messages', views.student_messages, name='student_messages'),

    # ==========================================
    # ORGANIZER URLS
    # ==========================================
    path('organizer/homepage', views.organizer_homepage, name='organizer_homepage'),
    path('organizer/school-events', views.organizer_school_events, name='organizer_school_events'),
    path('organizer/register-face/', views.register_organizer_face, name='register_organizer_face'),
    path('organizer/create-events', views.organizer_create_events, name='organizer_create_events'),
    
    # 🟢 DITO YUNG API PARA MA-SAVE YUNG GINAWANG EVENT PROPOSAL SA DATABASE 🟢
    path('organizer/api/notifications/', views.get_organizer_notifications_api, name='organizer_api_notifications'),
    path('organizer/api/submit-proposal/', views.submit_event_proposal, name='submit_event_proposal'),
    
    # 🟢 BAGONG API PARA SA PAG-DOWNLOAD NG WORD TEMPLATE 🟢
    path('organizer/download-proposal-doc/', views.download_event_proposal_doc, name='download_event_proposal_doc'),
    
    path('organizer/manage-students', views.organizer_manage_students, name='organizer_manage_students'),
    # Force reload comment 2
    path('organizer/approve-student', views.approve_individual_student, name='approve_individual_student'), 
    path('organizer/reject-student', views.reject_individual_student, name='reject_individual_student'), 
    path('organizer/attendance-hub', views.organizer_attendance_events, name='organizer_attendance_events'),
    path('organizer/manage-attendance', views.organizer_manage_attendance, name='organizer_manage_attendance'),
    
    # 🟢 DITO YUNG ANALYTICS AT DETAILED FEEDBACK MO NA GINAWA NATIN 🟢
    path('organizer/analytics', views.organizer_analytics, name='organizer_analytics'),
    path('organizer/feedback/detail', views.organizer_feedback_detail, name='organizer_feedback_detail'),
    
    path('organizer/profile', views.organizer_profile, name='organizer_profile'),
    path('organizer/api/update-profile/', views.update_organizer_profile, name='update_organizer_profile'),
    path('organizer/api/update-notif-preference/', views.update_org_notification_preference, name='update_org_notification_preference'),
    path('organizer/api/mark-notifs-read/', views.mark_org_notifications_read, name='mark_org_notifications_read'),
    path('organizer/message-history', views.organizer_message_history, name='organizer_message_history'),
    path('organizer/attendance-history', views.organizer_attendance_history, name='organizer_attendance_history'),
    path('organizer/document-tracking', views.organizer_document_tracking, name='organizer_document_tracking'),

    # 🟢 DOCUMENT VAULT URLS (PARA SA UPLOADS) 🟢
    path('organizer/event-vault/', views.organizer_event_vault, name='organizer_event_vault'),
    path('organizer/upload-permit/', views.upload_signed_permit, name='upload_signed_permit'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)