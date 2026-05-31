from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User 
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail 
from django.conf import settings 
from django.core.serializers import serialize 
from django.template.loader import render_to_string 
from django.utils.html import strip_tags           
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import timedelta, datetime
import json 
import string 
import random 
import os 
from docxtpl import DocxTemplate 
from .models import OrgProfile, Student, Attendance, Event, LoginLockout, AuditLog
from .utils import log_audit_event
from .middleware import get_current_request

# ==========================================
# 🟢 4 STRICT RBAC GUARDS (PAM-BLOCK SA MALING URL ACCESS) 🟢
# ==========================================
def is_admin_strictly(user):
    is_auth = user.is_authenticated and user.is_superuser
    if user.is_authenticated and not user.is_superuser:
        request = get_current_request()
        log_audit_event(request, 'UNAUTHORIZED', status='Denied', changes={'attempted_role': 'Admin', 'user_role': 'Other'})
    return is_auth

def is_adviser_strictly(user):
    is_auth = user.is_authenticated and user.is_staff and not user.is_superuser
    if user.is_authenticated and (user.is_superuser or not user.is_staff):
        request = get_current_request()
        log_audit_event(request, 'UNAUTHORIZED', status='Denied', changes={'attempted_role': 'Adviser'})
    return is_auth

def is_organizer_strictly(user):
    is_auth = user.is_authenticated and OrgProfile.objects.filter(user=user).exists()
    if user.is_authenticated and not is_auth:
        request = get_current_request()
        log_audit_event(request, 'UNAUTHORIZED', status='Denied', changes={'attempted_role': 'Organizer'})
    return is_auth

def is_student_strictly(user):
    is_auth = user.is_authenticated and Student.objects.filter(user=user).exists()
    if user.is_authenticated and not is_auth:
        request = get_current_request()
        log_audit_event(request, 'UNAUTHORIZED', status='Denied', changes={'attempted_role': 'Student'})
    return is_auth

ORG_FULL_NAMES = {
    "ITO": "ITO - INFORMATION TECHNOLOGY ORGANIZATION",
    "YEO": "YEO - YOUNG ENTREPRENEURSHIP ORGANIZATION",
    "ITS": "ITS - INSTITUTE OF TECHNOLOGY SOCIETY",
    "FTO": "FTO - FUTURE TEACHER ORGANIZATION",
    "PAS": "PAS - PUBLIC ADMINISTRATION SOCIETY",
    "CAO": "CAO - CULTURE AND ARTS",
    "PRIDEVerse": "PRIDEVerse",
    "SSC": "SSC - SUPREME STUDENT COUNCIL",
    "ROTC": "ROTC - Reserve Officers' Training Corps",
    "NEWSETTE": "NEWSETTE",
    "PUSO": "PUSO - PUP UNISAN SPORTS ORGANIZATION",
}

def check_lockout(request, type='portal'):
    session_key = f'lockout_until_{type}'
    lockout_until = request.session.get(session_key)
    if lockout_until:
        lockout_time = datetime.fromisoformat(lockout_until)
        if timezone.now() < lockout_time:
            remaining = (lockout_time - timezone.now()).total_seconds()
            return True, int(remaining)
    return False, 0

def check_account_lockout(identifier):
    if not identifier:
        return False, 0
    lockout, created = LoginLockout.objects.get_or_create(identifier=identifier)
    if lockout.lockout_until and timezone.now() < lockout.lockout_until:
        remaining = (lockout.lockout_until - timezone.now()).total_seconds()
        return True, int(remaining)
    return False, 0

def record_failed_attempt(identifier):
    lockout, created = LoginLockout.objects.get_or_create(identifier=identifier)
    lockout.failed_attempts += 1

    if lockout.failed_attempts % 5 == 0:
        lockout_minutes = (lockout.failed_attempts // 5) * 2
        lockout.lockout_until = timezone.now() + timedelta(minutes=lockout_minutes)
        lockout.save()
        return True, lockout_minutes * 60, lockout.failed_attempts

    lockout.save()
    return False, 0, lockout.failed_attempts

def reset_account_lockout(identifier):
    LoginLockout.objects.filter(identifier=identifier).update(failed_attempts=0, lockout_until=None)

def index(request):
    is_locked, remaining = check_lockout(request, type='portal')
    return render(request, 'index.html', {'is_locked': is_locked, 'remaining': remaining})

def staff_logout_view(request):
    if request.user.is_authenticated:
        # 🟢 Calculate Session Duration
        last_login = AuditLog.objects.filter(actor=request.user, action='LOGIN_SUCCESS').first()
        duration_str = "Unknown"
        if last_login:
            duration = timezone.now() - last_login.timestamp
            hours, remainder = divmod(int(duration.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours}h {minutes}m"

        log_audit_event(request, 'LOGOUT', status='Success', changes={'session_duration': duration_str})
    logout(request)
    return redirect('/admin/login/')

def portal_logout_view(request):
    if request.user.is_authenticated:
        # 🟢 Calculate Session Duration
        last_login = AuditLog.objects.filter(actor=request.user, action='LOGIN_SUCCESS').first()
        duration_str = "Unknown"
        if last_login:
            duration = timezone.now() - last_login.timestamp
            hours, remainder = divmod(int(duration.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours}h {minutes}m"

        log_audit_event(request, 'LOGOUT', status='Success', changes={'session_duration': duration_str})
    logout(request)
    return redirect('/')

# ==========================================
# 🟢 PINAG-ISANG MAIN PORTAL LOGIN (STUDENT & ORGANIZER) 🟢
# ==========================================
def portal_login_view(request):
    if request.method == 'POST':
        is_locked, remaining = check_lockout(request, type='portal')
        if is_locked:
            return JsonResponse({"status": "lockout", "message": "Too many attempts.", "remaining": remaining})

        student_number = request.POST.get('student_number')
        password = request.POST.get('password')

        # Check Account Lockout
        is_acc_locked, acc_remaining = check_account_lockout(student_number)
        if is_acc_locked:
            return JsonResponse({"status": "lockout", "message": "Account locked.", "remaining": acc_remaining})

        user = authenticate(request, username=student_number, password=password)

        if user is not None:
            # Check if this is a Staff/Admin trying to login here (RBAC strict separation)
            if user.is_superuser or (user.is_staff and not OrgProfile.objects.filter(user=user).exists()):
                log_audit_event(request, 'LOGIN_FAILED', status='Denied', changes={'reason': 'Staff/Admin attempting Portal Login', 'username': student_number})
                return JsonResponse({"status": "error", "message": "Admin/Adviser accounts must login through the Staff Portal (/admin/login/)."})

            # Success - reset attempts
            request.session['failed_attempts_portal'] = 0
            if 'lockout_until_portal' in request.session: del request.session['lockout_until_portal']
            reset_account_lockout(student_number)

            if OrgProfile.objects.filter(user=user).exists():
                login(request, user)
                log_audit_event(request, 'LOGIN_SUCCESS', status='Success', changes={'role': 'Organizer'}, actor=user)
                return JsonResponse({"status": "success", "redirect_url": "/organizer/homepage"})
            elif Student.objects.filter(user=user).exists():
                student = Student.objects.get(user=user)
                if not student.is_verified:
                    log_audit_event(request, 'LOGIN_FAILED', status='Denied', changes={'reason': 'Unverified Student Account', 'username': student_number}, actor=user)
                    return JsonResponse({"status": "error", "message": "Account is still pending approval. Please wait for your Organizer."})
                else:
                    login(request, user)
                    log_audit_event(request, 'LOGIN_SUCCESS', status='Success', changes={'role': 'Student'}, actor=user)
                    return JsonResponse({"status": "success", "redirect_url": "/student/dashboard"})
            else:
                log_audit_event(request, 'LOGIN_FAILED', status='Denied', changes={'reason': 'Account role not identified', 'username': student_number})
                return JsonResponse({"status": "error", "message": "Account is neither a registered Student nor an Organizer."})
        else:
            # Failed attempt logic
            is_locked_now, lock_time, total_attempts = record_failed_attempt(student_number)
            
            log_audit_event(request, 'LOGIN_FAILED', status='Failed', changes={'username': student_number, 'attempt_count': total_attempts})

            if is_locked_now:
                request.session['lockout_until_portal'] = (timezone.now() + timedelta(seconds=lock_time)).isoformat()
                return JsonResponse({
                    "status": "lockout", 
                    "message": f"Too many failed attempts ({total_attempts}). Please wait.", 
                    "remaining": lock_time
                })

            return JsonResponse({"status": "error", "message": f"Incorrect credentials. Attempt {total_attempts % 5} of 5."})

    return redirect('index')

# ==========================================
# 🟢 FORGOT PASSWORD SYSTEM (ALL ACTORS) 🟢
# ==========================================
def forgot_password_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier') # Student Number or Username

        try:
            user = User.objects.get(username=identifier)
            email = user.email

            if not email:
                # Try to get from Student profile if not in User
                student = Student.objects.filter(user=user).first()
                if student: email = student.email_address

            if not email:
                return JsonResponse({"status": "error", "message": "No email associated with this account. Please contact Admin."})

            # Generate temporary code
            chars = string.ascii_letters + string.digits
            temp_code = ''.join(random.choice(chars) for i in range(8))
            request.session['reset_code'] = temp_code
            request.session['reset_user_id'] = user.id

            html_content = render_to_string('email/change_password.html', {
                'password': temp_code,
                'email_address': email
            })

            send_mail(
                "Password Reset Request - PUPUni-CAMS",
                strip_tags(html_content),
                settings.EMAIL_HOST_USER,
                [email],
                html_message=html_content,
                fail_silently=False,
            )
            return JsonResponse({"status": "success", "message": "Verification code sent to your registered email!"})

        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Account not found in our records."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return render(request, 'forgot_password.html')

def verify_reset_code(request):
    if request.method == 'POST':
        typed_code = request.POST.get('code')
        saved_code = request.session.get('reset_code')

        if not saved_code or typed_code != saved_code:
            return JsonResponse({"status": "error", "message": "Incorrect verification code."})

        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error", "message": "Invalid request."})

def complete_password_reset(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        user_id = request.session.get('reset_user_id')

        if not user_id:
            return JsonResponse({"status": "error", "message": "Session expired. Please try again."})

        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()

        # Cleanup
        if 'reset_code' in request.session: del request.session['reset_code']
        if 'reset_user_id' in request.session: del request.session['reset_user_id']
        if 'failed_attempts' in request.session: request.session['failed_attempts'] = 0
        if 'lockout_until' in request.session: del request.session['lockout_until']

        return JsonResponse({"status": "success", "message": "Password successfully reset! You can now login."})
    return JsonResponse({"status": "error", "message": "Invalid request."})

# ==========================================
# STUDENT VIEWS
# ==========================================
def generate_student_password(request):
    if request.method == 'POST':
        email = request.POST.get('email_address')
        if not email:
            return JsonResponse({"status": "error", "message": "Please enter an email address first."})

        chars = string.ascii_letters + string.digits
        random_password = ''.join(random.choice(chars) for i in range(10))
        request.session['generated_password'] = random_password 

        try:
            html_content = render_to_string('email/create_account.html', {
                'password': random_password,
                'email_address': email
            })
            text_content = strip_tags(html_content)

            send_mail(
                "Your Account Password - PUPUni-CAMS",
                text_content,             
                settings.EMAIL_HOST_USER,
                [email],
                html_message=html_content,
                fail_silently=False,
            )
            return JsonResponse({"status": "success", "message": "Code sent! Please check your email inbox (and spam folder)."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Email Error: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request."})

def verify_student_password(request):
    if request.method == 'POST':
        typed_password = request.POST.get('password')
        saved_password = request.session.get('generated_password')

        if not saved_password:
            return JsonResponse({"status": "error", "message": "Please click 'Get Code' first to receive your password."})

        if typed_password != saved_password:
            return JsonResponse({"status": "error", "message": "Incorrect Code! Please make sure you copied the exact password from your email."})

        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error", "message": "Invalid request."})

def student_register(request):
    if request.method == 'POST':
        try:
            password = request.POST.get('password')
            saved_password = request.session.get('generated_password')

            if not saved_password or password != saved_password:
                return JsonResponse({"status": "error", "message": "Authentication failed. Invalid password."})

            full_name = request.POST.get('full_name')
            student_number = request.POST.get('student_number')
            email_address = request.POST.get('email_address')
            year_level = request.POST.get('year_level')
            program = request.POST.get('program')
            organization = request.POST.get('organization', 'Not Assigned') 
            face_data = request.POST.get('facial_registration_data')
            birthdate = request.POST.get('birthdate')
            profile_picture = request.FILES.get('profile_picture')
            cover_photo = request.FILES.get('cover_photo')

            user, created = User.objects.get_or_create(username=student_number)
            user.set_password(password)
            user.email = email_address
            user.save()

            defaults_data = {
                'user': user,
                'full_name': full_name,
                'email_address': email_address,
                'program': program,
                'year_level': year_level,
                'organization': organization.strip(), 
                'password': password, 
                'face_encoding': face_data,
                'role': 'Student',
                'is_verified': False 
            }

            if birthdate: defaults_data['birthdate'] = birthdate
            if profile_picture: defaults_data['profile_picture'] = profile_picture
            if cover_photo: defaults_data['cover_photo'] = cover_photo

            Student.objects.update_or_create(student_number=student_number, defaults=defaults_data)

            if 'generated_password' in request.session:
                del request.session['generated_password']

            # 🟢 LOG REGISTRATION
            log_audit_event(request, 'REGISTRATION', status='Success', changes={'student_number': student_number})

            return JsonResponse({"status": "success", "message": "Registration Successful! Please wait for your Organizer to approve your account."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return redirect('index')

@user_passes_test(is_student_strictly, login_url='/')
def student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    # 🟢 CONSTRUCT RECENT NOTIFICATIONS FOR PROFILE PREVIEW
    notifications = get_student_notifications(student)
    recent_notifications = notifications[:4]  # Show only top 4 on profile

    # 🟢 STATS FOR STUDENT
    attended_count = Attendance.objects.filter(student=student).count()
    present_count = Attendance.objects.filter(student=student, face_matched=True, is_valid_location=True).count()
    absent_count = attended_count - present_count # Simplistic

    context = {
        'student': student,
        'notifications': recent_notifications,
        'attended_count': attended_count,
        'present_count': present_count,
        'absent_count': absent_count
    }
    return render(request, 'student/profile.html', context)

def get_student_notifications(student):
    notifications = []

    # 1. Welcome Message
    notifications.append({
        'id': f"welcome_{student.id}",
        'type': 'system',
        'title': 'Welcome to PUPUni-CAMS!',
        'message': f"Mabuhay {student.full_name}! Your account has been verified. You can now participate in campus events and track your attendance.",
        'sender': 'System Admin',
        'date': student.created_at.strftime('%b %d, %Y') if student.created_at else 'System',
        'timestamp': student.created_at.timestamp() if student.created_at else 0,
        'status': 'System'
    })

    # 2. Upcoming Events (Approved & Future)
    upcoming_events = Event.objects.filter(event_status='Approved', event_date__gte=timezone.now().date()).order_by('event_date')[:5]
    for evt in upcoming_events:
        notifications.append({
            'id': f"event_{evt.id}",
            'type': 'event',
            'title': f"Upcoming: {evt.event_title}",
            'message': f"An exciting event '{evt.event_title}' is happening on {evt.event_date.strftime('%B %d')} at {evt.venue}. Don't miss out!",
            'sender': evt.org_id,
            'date': evt.created_at.strftime('%b %d, %Y'),
            'timestamp': evt.created_at.timestamp(),
            'status': 'Approved'
        })

    # 3. Attendance Issues
    attendance_issues = Attendance.objects.filter(student=student).filter(Q(face_matched=False) | Q(is_valid_location=False)).order_by('-time_in')[:5]
    for att in attendance_issues:
        issue_msg = ""
        if not att.face_matched and not att.is_valid_location:
            issue_msg = "Face recognition failed and you were outside the event geofence."
        elif not att.face_matched:
            issue_msg = "Face recognition failed during your attendance check."
        else:
            issue_msg = "You were detected outside the designated event location."

        notifications.append({
            'id': f"att_{att.id}",
            'type': 'alert',
            'title': f"Attendance Issue: {att.event.event_title}",
            'message': f"There was a problem recording your attendance for {att.event.event_title}. {issue_msg} Please contact the organizer.",
            'sender': 'Security System',
            'date': att.time_in.strftime('%b %d, %Y'),
            'timestamp': att.time_in.timestamp(),
            'status': 'Rejected'
        })

    # Sort by timestamp descending
    notifications.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return notifications

@user_passes_test(is_student_strictly, login_url='/')
def student_messages(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    notifications = get_student_notifications(student)

    context = {
        'student': student,
        'notifications_json': json.dumps(notifications)
    }
    return render(request, 'student/messages.html', context)

@user_passes_test(is_student_strictly, login_url='/')
def update_student_password(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        new_password = request.POST.get('new_password')
        saved_code = request.session.get('generated_password')

        if not saved_code or code != saved_code:
            return JsonResponse({"status": "error", "message": "Invalid Verification Code!"})

        user = request.user
        user.set_password(new_password)
        user.save()
        login(request, user) 

        if 'generated_password' in request.session:
            del request.session['generated_password']

        return JsonResponse({"status": "success", "message": "Password updated successfully!"})
    return JsonResponse({"status": "error", "message": "Invalid request."})

@user_passes_test(is_student_strictly, login_url='/')
def update_student_profile(request):
    if request.method == 'POST':
        try:
            student = Student.objects.get(user=request.user)
            full_name = request.POST.get('full_name')
            year_level = request.POST.get('year_level')
            birthdate = request.POST.get('birthdate')

            if full_name: student.full_name = full_name
            if year_level: student.year_level = year_level
            if birthdate: student.birthdate = birthdate

            if 'profile_picture' in request.FILES:
                student.profile_picture = request.FILES['profile_picture']
            if 'cover_photo' in request.FILES:
                student.cover_photo = request.FILES['cover_photo']

            student.save()
            return JsonResponse({"status": "success", "message": "Profile updated successfully!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request."})

@user_passes_test(is_student_strictly, login_url='/')
def student_homepage(request):
    upcoming_events = Event.objects.filter(event_status='Approved').order_by('event_date')[:4]
    latest_news = Event.objects.filter(event_status='Approved').order_by('-created_at')[:4]

    upcoming_data = []
    for e in upcoming_events:
        upcoming_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y').upper(),
            'location': e.venue,
            'image': e.thumbnail.name if e.thumbnail else 'background.jpg',
            'description': e.description
        })

    news_data = []
    for e in latest_news:
        news_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.created_at.strftime('%b %d, %Y').upper(),
            'location': e.venue,
            'image': e.thumbnail.name if e.thumbnail else 'research.jpg',
            'description': e.description
        })

    context = {
        'upcoming_events_json': json.dumps(upcoming_data),
        'latest_news_json': json.dumps(news_data)
    }
    return render(request, 'student/homepage.html', context)

@user_passes_test(is_student_strictly, login_url='/')
def student_school_events(request):
    all_events = Event.objects.filter(event_status='Approved').order_by('event_date')
    events_data = []
    for e in all_events:
        events_data.append({
            'id': e.id,
            'title': e.event_title,
            'category': 'Organization', # Default category for now
            'date': e.event_date.strftime('%b %d, %Y').upper(),
            'time': e.start_time.strftime('%I:%M %p'),
            'venue': e.venue,
            'image': e.thumbnail.url if e.thumbnail else '',
            'description': e.description
        })
    return render(request, 'student/school_events.html', {'events_json': json.dumps(events_data)})

@user_passes_test(is_student_strictly, login_url='/')
def student_event_calendar(request): return render(request, 'student/event_calendar.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_evaluation(request): return render(request, 'student/evaluation.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_evaluation_form(request): return render(request, 'student/evaluation_form.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_event_history(request): return render(request, 'student/event_history.html')

# ==========================================
# ORGANIZER VIEWS
# ==========================================

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_homepage(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    managed_events = Event.objects.filter(org_id=org_acronym).order_by('-created_at')[:5]
    managed_data = []
    for e in managed_events:
        managed_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y').upper(),
            'status': e.event_status,
            'image': e.thumbnail.url if e.thumbnail else ''
        })

    action_required = Event.objects.filter(org_id=org_acronym, event_status='Admin Approved').first()
    
    latest_news = Event.objects.filter(event_status='Approved').order_by('-created_at')[:4]
    news_data = []
    for e in latest_news:
        news_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.created_at.strftime('%b %d, %Y').upper(),
            'image': e.thumbnail.url if e.thumbnail else ''
        })

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'managed_events_json': json.dumps(managed_data),
        'action_required_json': json.dumps({
            'title': action_required.event_title,
            'id': action_required.id
        }) if action_required else None,
        'latest_news_json': json.dumps(news_data)
    }
    return render(request, 'organizer/homepage.html', context)

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_school_events(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
    return render(request, 'organizer/school_events.html', {'org_acronym': org_acronym, 'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym)})

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_create_events(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
        
    events = Event.objects.filter(org_id=org_acronym).order_by('-created_at')
    events_data = []
    
    for e in events:
        events_data.append({
            'id': e.id,
            'title': e.event_title or "",
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '', # Formatted neatly
            'start_time': e.start_time.strftime('%H:%M') if e.start_time else '', # Keep 24-hr format specifically for <input type="time">
            'end_time': e.end_time.strftime('%H:%M') if getattr(e, 'end_time', None) else '', # Keep 24-hr format
            'venue': e.venue or "",
            'description': e.description or "",
            'requester_name': getattr(e, 'requester_name', '') or "",
            'adviser_name': getattr(e, 'adviser_name', '') or "",
            'status': e.event_status.upper() if e.event_status else "",
            'org': org_acronym
        })

    return render(request, 'organizer/create_events.html', {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'events_json': json.dumps(events_data)
    })

@user_passes_test(is_organizer_strictly, login_url='/')
def submit_event_proposal(request):
    if request.method == 'POST':
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            org_acronym = org_profile.organization.strip()

            event_id = request.POST.get('event_id')
            requester_name = request.POST.get('requester_name')
            adviser_name = request.POST.get('adviser_name')
            title = request.POST.get('title')
            event_date = request.POST.get('date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            venue = request.POST.get('venue')
            description = request.POST.get('description')

            if event_id:
                # 🟢 RESCHEDULE / EDIT EXISTING EVENT 🟢
                event = Event.objects.get(id=event_id, org_id=org_acronym)
                event.requester_name = requester_name
                event.event_title = title
                event.event_date = event_date
                event.start_time = start_time
                event.venue = venue
                event.description = description
                
                if hasattr(event, 'end_time'): event.end_time = end_time
                if hasattr(event, 'adviser_name'): event.adviser_name = adviser_name
                if hasattr(event, 'equipment_needed'): event.equipment_needed = "" 
                
                event.event_status = 'Pending Adviser' 
                event.current_location = 'Office of the Adviser'
                event.save()
                message = "Event proposal updated and resubmitted to Adviser successfully!"
            else:
                # 🟢 CREATE NEW EVENT 🟢
                event = Event(
                    org_id=org_acronym,
                    proposal_by_user_id=request.user.username,
                    requester_name=requester_name,
                    event_title=title,
                    event_date=event_date,
                    start_time=start_time,
                    venue=venue,
                    description=description,
                    event_status='Pending Adviser', 
                    current_location='Office of the Adviser'
                )
                if hasattr(event, 'end_time'): event.end_time = end_time
                if hasattr(event, 'adviser_name'): event.adviser_name = adviser_name
                if hasattr(event, 'equipment_needed'): event.equipment_needed = ""
                event.save()
                message = "New event proposal submitted to Adviser successfully!"

            return JsonResponse({"status": "success", "message": message})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

# 🟢 DYNAMIC DOCX GENERATOR (HANDLES ALL 3 TEMPLATES) 🟢
@user_passes_test(is_organizer_strictly, login_url='/')
def download_event_proposal_doc(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            doc_type = data.get('docType', 'approval')
            
            # Pipili ng Template depende sa Request
            if doc_type == 'excuse':
                template_name = 'TEMPLATE_EXCUSE.docx'
            elif doc_type == 'reschedule':
                template_name = 'TEMPLATE_RESCHEDULE.docx'
            else:
                template_name = 'TEMPLATE_APPROVAL.docx'
                
            template_path = os.path.join(settings.BASE_DIR, 'static', 'templates', template_name)
            
            if not os.path.exists(template_path):
                return JsonResponse({'status': 'error', 'message': f'Word Template {template_name} missing on server! Please check folder.'})

            doc = DocxTemplate(template_path)
            
            # Buong Context ng Letter
            context = {
                'letDate': data.get('letDate', ''),
                'fullOrgName': data.get('fullOrgName', ''),
                'letTitle': data.get('letTitle', ''),
                'letDesc': data.get('letDesc', ''),
                'letEvtDate': data.get('letEvtDate', ''),
                'letEvtTime': data.get('letEvtTime', ''),
                'letVenue': data.get('letVenue', ''),
                'sigName': data.get('sigName', '').upper(),
                'sigOrg': data.get('sigOrg', '').upper(),
                'sigAdviser': data.get('sigAdviser', '').upper(),
                # Variables para sa Excuse Letter
                'targetClasses': data.get('targetClasses', ''),
                'reqEquipment': data.get('reqEquipment', ''),
                # Variables para sa Reschedule
                'origDate': data.get('origDate', ''),
                'reschedReason': data.get('reschedReason', ''),
            }
            
            doc.render(context)
            
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="{doc_type.capitalize()}_Document_{data.get("sigOrg", "Request")}.docx"'
            doc.save(response)
            
            return response
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_manage_students(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    pending_students = Student.objects.filter(organization__iexact=org_acronym, is_verified=False)
    approved_students = Student.objects.filter(organization__iexact=org_acronym, is_verified=True)

    return render(request, 'organizer/manage_students.html', {
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'pending_students': pending_students, 
        'approved_students': approved_students 
    })

@user_passes_test(is_organizer_strictly, login_url='/')
def approve_individual_student(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(id=student_id)
            student.is_verified = True
            student.save()
            
            # 🟢 SEND HTML WELCOME EMAIL
            send_student_email(student, 'welcome', {})

            # 🟢 LOG VERIFICATION
            log_audit_event(request, 'VERIFICATION', status='Success', changes={'student': student.full_name})

            messages.success(request, f"Successfully assigned {student.full_name} to {student.organization}!")
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")
    return redirect('organizer_manage_students')

# ==========================================
# 🟢 UTILITY: SEND STUDENT EMAIL NOTIFICATION
# ==========================================
def send_student_email(student, email_type, context_data):
    if not student.email_notifications:
        return False
    
    subject = "PUPUni-CAMS Notification"
    template_name = ""
    
    if email_type == 'welcome':
        subject = f"Account Approved - {student.organization} Student Portal"
        template_name = "email/welcome_email.html"
    elif email_type == 'event_alert':
        subject = f"New Event: {context_data.get('event_title')}"
        template_name = "email/event_alert.html"
    elif email_type == 'attendance':
        subject = f"Attendance Issue: {context_data.get('event_title')}"
        template_name = "email/attendance_status.html"
    elif email_type == 'evaluation':
        subject = f"Evaluation Issue: {context_data.get('event_title')}"
        template_name = "email/evaluation_issue.html"
    
    if not template_name:
        return False

    context_data['full_name'] = student.full_name
    context_data['email_address'] = student.email_address

    html_message = render_to_string(template_name, context_data)
    plain_message = strip_tags(html_message)

    try:
        send_mail(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
            [student.email_address],
            html_message=html_message,
            fail_silently=True
        )
        return True
    except:
        return False

@user_passes_test(is_student_strictly, login_url='/')
def update_notification_preference(request):
    if request.method == 'POST':
        enabled = request.POST.get('email_notifications') == 'true'
        try:
            student = Student.objects.get(user=request.user)
            student.email_notifications = enabled
            student.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_manage_attendance(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    # Fetch attendance for events belonging to this org
    attendance_records = Attendance.objects.filter(event__org_id=org_acronym).select_related('student', 'event').order_by('-time_in')
    
    attendance_data = []
    for att in attendance_records:
        status = "Verified" if att.face_matched and att.is_valid_location else "Issue"
        attendance_data.append({
            'id': att.id,
            'name': att.student.full_name,
            'number': att.student.student_number,
            'program': att.student.program,
            'year': att.student.year_level,
            'time': att.time_in.strftime('%I:%M %p'),
            'date': att.time_in.strftime('%b %d, %Y'),
            'status': status,
            'event': att.event.event_title,
            'venue': att.event.venue,
            'lat': float(att.latitude) if att.latitude else 13.8392, # Default to campus if missing
            'lng': float(att.longitude) if att.longitude else 121.9861,
            'img': att.student.profile_picture.url if att.student.profile_picture else '/static/images/student.jpg'
        })

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'attendance_data_json': json.dumps(attendance_data)
    }
    return render(request, 'organizer/manage_attendance.html', context)

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_analytics(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
    return render(request, 'organizer/analytics.html', {'org_acronym': org_acronym, 'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym)})

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_profile(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = 'UNKNOWN'
        org_profile = None

    full_name = request.user.first_name if request.user.first_name else request.user.username
    
    recent_events = Event.objects.filter(org_id=org_acronym).order_by('-created_at')[:4]
    completed_events = Event.objects.filter(org_id=org_acronym, event_status='Approved').order_by('-created_at')
    pending_students = Student.objects.filter(organization__iexact=org_acronym, is_verified=False).order_by('-created_at')

    context = {
        'org_profile': org_profile,
        'full_name': full_name,
        'student_number': request.user.username,
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'recent_events': recent_events,
        'completed_events': completed_events,
        'pending_students': pending_students 
    }
    return render(request, 'organizer/profile.html', context)

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_message_history(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = 'UNKNOWN'

    events = Event.objects.filter(org_id=org_acronym).order_by('-id')
    students = Student.objects.filter(organization__iexact=org_acronym, is_verified=False).order_by('-id')

    notifications = []
    
    for s in students:
        date_str = s.created_at.strftime('%b %d, %Y') if hasattr(s, 'created_at') and s.created_at else 'Recent'
        timestamp = s.created_at.timestamp() if hasattr(s, 'created_at') and s.created_at else s.id
        
        notifications.append({
            'id': f"stud_{s.id}",
            'type': 'student',
            'title': 'New Student Registration',
            'message': f"Mabuhay Iskolar! {s.full_name} is waiting for your approval to join the organization portal.",
            'sender': 'System Admin',
            'date': date_str,
            'timestamp': timestamp,
            'url': '/organizer/manage-students'
        })

    for e in events:
        date_str = e.created_at.strftime('%b %d, %Y') if hasattr(e, 'created_at') and e.created_at else 'Recent'
        timestamp = e.created_at.timestamp() if hasattr(e, 'created_at') and e.created_at else e.id
        
        if e.event_status == 'Approved':
            msg = f"Great news! Your event proposal for '{e.event_title}' has been officially APPROVED by the Administration."
            sender = 'Admin Office'
        elif e.event_status == 'Admin Approved':
            msg = f"Initial Approval granted for '{e.event_title}'! Please upload your signed documents in the Document Vault."
            sender = 'Admin Office'
        elif e.event_status == 'Rejected':
            msg = f"Notice: Your event proposal for '{e.event_title}' was REJECTED. Please click to view the remarks."
            sender = 'Admin / Adviser'
        else:
            msg = f"Update: Your event proposal for '{e.event_title}' is currently UNDER REVIEW."
            sender = 'System Notification'
            
        notifications.append({
            'id': f"evt_{e.id}",
            'raw_id': e.id,
            'type': 'event',
            'title': e.event_title,
            'status': e.event_status,
            'remarks': str(e.remarks) if e.remarks else '',
            'message': msg,
            'sender': sender,
            'date': date_str,
            'timestamp': timestamp,
        })

    notifications.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    context = {
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'notifications_json': json.dumps(notifications)
    }
    return render(request, 'organizer/message_history.html', context)


@user_passes_test(is_organizer_strictly, login_url='/')
def update_organizer_profile(request):
    if request.method == 'POST':
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            
            full_name = request.POST.get('full_name')
            if full_name:
                request.user.first_name = full_name
                request.user.save()
            
            if 'profile_picture' in request.FILES:
                org_profile.profile_picture = request.FILES['profile_picture']
            if 'cover_photo' in request.FILES:
                org_profile.cover_photo = request.FILES['cover_photo']
            
            org_profile.save()
            return JsonResponse({"status": "success", "message": "Profile updated successfully!"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
            
    return JsonResponse({"status": "error", "message": "Invalid request."})

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_attendance_history(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    # Fetch completed events or events with attendance records
    events_with_attendance = Event.objects.filter(org_id=org_acronym).order_by('-event_date')
    
    history_data = []
    for e in events_with_attendance:
        history_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y') if e.event_date else 'No Date',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '--',
            'venue': e.venue,
            'type': 'Attendance',
            'img': e.thumbnail.url if e.thumbnail else '/static/images/PUPLogo.png'
        })

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'history_data_json': json.dumps(history_data)
    }
    return render(request, 'organizer/attendance_history.html', context)

# ==========================================
# 🟢 UPDATED 6-STEP DOCUMENT TRACKING LOGIC 🟢
# ==========================================
@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_document_tracking(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
        
    events = Event.objects.filter(org_id=org_acronym).order_by('-created_at')
    docs_data = []
    
    # 📍 Campus Landmarks for PUP Unisan (Kalilayan Ibaba) - Wider Spread
    HUB_COORDS = [13.84545, 121.96885]    # Student Center (SW)
    ADVISER_COORDS = [13.84575, 121.96915] # Faculty Lounge (Middle)
    ADMIN_COORDS = [13.84615, 121.96955]   # Academic Bldg (NE)

    for e in events:
        if e.event_status == 'Pending Adviser':
            loc = "Office of the Org Adviser (Initial Review)"
            coords = ADVISER_COORDS
            progress = 1 
        elif e.event_status == 'Pending Admin':
            loc = "Office of the Admin (Initial Clearance)"
            coords = ADMIN_COORDS
            progress = 2 
        elif e.event_status == 'Admin Approved':
            loc = "Student Organization Office (Gathering Signatures)"
            coords = HUB_COORDS
            progress = 3 
        elif e.event_status == 'Permit Verification':
            loc = "Office of the Org Adviser (Signature Verification)"
            coords = ADVISER_COORDS
            progress = 4 
        elif e.event_status == 'Final Admin Review':
            loc = "Office of the Admin (Final Clearance)"
            coords = ADMIN_COORDS
            progress = 5 
        elif e.event_status == 'Approved':
            loc = "Live in Portal (PUP Unisan Student Org Hub)"
            coords = HUB_COORDS
            progress = 6 
        elif e.event_status == 'Rejected':
            loc = "Returned to Organizer (Correction Required)"
            coords = HUB_COORDS
            
            # Deduce step index for rejection timeline display
            curr_loc = str(e.current_location).lower()
            if "adviser" in curr_loc:
                progress = 4 if ("verify" in curr_loc or "signature" in curr_loc) else 1
            elif "admin" in curr_loc:
                progress = 5 if ("final" in curr_loc or "clearance" in curr_loc) else 2
            else:
                progress = 1
        else:
            loc = "PUP Unisan, Kalilayan Ibaba, Unisan, Quezon"
            coords = ADVISER_COORDS
            progress = 0

        docs_data.append({
            'id': e.id,
            'eventName': e.event_title,       
            'orgName': e.org_id,              
            'status': e.event_status,
            'date': str(e.event_date),
            'currentLoc': loc,                
            'docType': 'Activity Proposal',
            'coords': coords,
            'progress': progress,
            'rejectReason': str(e.remarks) if e.remarks else 'No reason provided.'
        })

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'documents_json': json.dumps(docs_data)
    }
    return render(request, 'organizer/document_tracking.html', context)

# ==========================================
# 🟢 DOCUMENT VAULT LOGIC (PARA SA UPLOADS) 🟢
# ==========================================
@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_event_vault(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
    
    pending_events = Event.objects.filter(org_id=org_acronym, event_status='Admin Approved').order_by('-id')
    pending_data = []
    for e in pending_events:
        pending_data.append({
            'id': e.id,
            'eventName': e.event_title,
            'orgName': e.org_id
        })

    vault_events = Event.objects.filter(org_id=org_acronym, event_status__in=['Permit Verification', 'Final Admin Review', 'Approved']).order_by('-id')
    vault_data = []
    for e in vault_events:
        docs = []
        mode = e.requirement_mode if getattr(e, 'requirement_mode', None) else 4

        if mode == 2:
            if e.letter_image: docs.append({'title': '1. Letter of Reschedule', 'preview': e.letter_image.url})
            if getattr(e, 'event_cover_photo', None): docs.append({'title': '2. Event Reschedule Cover Photo', 'preview': e.event_cover_photo.url})
            elif getattr(e, 'reschedule_cover_photo', None): docs.append({'title': '2. Event Reschedule Cover Photo', 'preview': e.reschedule_cover_photo.url})
            elif e.other_attachments: docs.append({'title': '2. Event Reschedule Cover Photo', 'preview': e.other_attachments.url})
        else:
            if e.letter_image: docs.append({'title': '1. Request Letter', 'preview': e.letter_image.url})
            if e.permit_image: docs.append({'title': '2. Event Permit', 'preview': e.permit_image.url})
            if e.equipment_image: docs.append({'title': '3. Equipment Form', 'preview': e.equipment_image.url})
            if getattr(e, 'event_cover_photo', None): docs.append({'title': '4. Event Cover Photo', 'preview': e.event_cover_photo.url})
            elif e.other_attachments: docs.append({'title': '4. Event Cover Photo', 'preview': e.other_attachments.url})

        vault_data.append({
            'id': e.id,
            'eventName': e.event_title,
            'date': e.created_at.strftime("%b %d, %Y") if e.created_at else "",
            'mode': str(e.requirement_mode) if e.requirement_mode else str(len(docs)),
            'docs': docs
        })

    context = {
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'pending_json': json.dumps(pending_data),
        'vault_json': json.dumps(vault_data)
    }
    return render(request, 'organizer/event_documents.html', context)

# 🟢 IN-UPDATE PARA SALUHIN AT I-SAVE ANG IKATLONG LARAWAN (EQUIPMENT IMAGE) 🟢
@user_passes_test(is_organizer_strictly, login_url='/')
def upload_signed_permit(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        requirement_mode = request.POST.get('requirement_mode')
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            org_acronym = org_profile.organization.strip()
            
            event = Event.objects.get(id=event_id, org_id=org_acronym)
            event.event_status = 'Permit Verification' 
            
            if requirement_mode:
                event.requirement_mode = int(requirement_mode)
            
            if request.FILES.get('letter_image'):
                event.letter_image = request.FILES.get('letter_image')
            if request.FILES.get('permit_image'):
                event.permit_image = request.FILES.get('permit_image')
            if request.FILES.get('equipment_image'):
                event.equipment_image = request.FILES.get('equipment_image')
            
            # Catch event_cover_photo (fallback to other_attachments for compatibility)
            if request.FILES.get('event_cover_photo'):
                event.event_cover_photo = request.FILES.get('event_cover_photo')
            elif request.FILES.get('other_attachments'):
                event.event_cover_photo = request.FILES.get('other_attachments')

            # Catch reschedule_cover_photo for 2-file system
            if request.FILES.get('reschedule_cover_photo'):
                event.reschedule_cover_photo = request.FILES.get('reschedule_cover_photo')
                
            event.save()
            
            return JsonResponse({'status': 'success', 'message': 'Documents uploaded successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})


@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_feedback_detail(request):
    return render(request, 'organizer/feedback.html')

# ==========================================
# 🟢 ADMIN VIEWS (AYOS NA YUNG TIME BUGS!) 🟢
# ==========================================
@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def event_approvals_view(request): 
    # PENDING EVENTS (Action Required)
    pending = Event.objects.filter(event_status__in=['Pending Admin', 'Final Admin Review']).order_by('-created_at')
    pending_data = []
    for e in pending:
        # 🟢 Idinagdag ang equipment_url pati 12-hour format sa Admin 🟢
        pending_data.append({
            'id': e.id, 'org': e.org_id, 'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'equipment': getattr(e, 'equipment_needed', '') or '', 'status': e.event_status.upper() if e.event_status else '',
            'letter_url': e.letter_of_approval.url if getattr(e, 'letter_of_approval', None) else (e.letter_image.url if getattr(e, 'letter_image', None) else ''),
            'permit_url': e.permit_to_conduct.url if getattr(e, 'permit_to_conduct', None) else (e.permit_image.url if getattr(e, 'permit_image', None) else ''),
            'equipment_url': e.excuse_letter_equipment.url if getattr(e, 'excuse_letter_equipment', None) else (e.equipment_image.url if getattr(e, 'equipment_image', None) else ''),
            'event_cover_photo': e.event_cover_photo.url if getattr(e, 'event_cover_photo', None) else (e.cover_photo.url if getattr(e, 'cover_photo', None) else ''),
            'letter_of_reschedule': e.letter_of_reschedule.url if getattr(e, 'letter_of_reschedule', None) else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if getattr(e, 'reschedule_cover_photo', None) else (getattr(e, 'reschedule_cover_photo_legacy', None).url if getattr(e, 'reschedule_cover_photo_legacy', None) else ''),
            'requirement_mode': e.requirement_mode
            })
        
    # HISTORY EVENTS (Transaction Log)
    history = Event.objects.filter(event_status__in=['Approved', 'Rejected']).order_by('-created_at')
    history_data = []
    for e in history:
        # 🟢 Idinagdag ang lahat ng fields para sa History consistency 🟢
        history_data.append({
            'id': e.id, 'org': e.org_id, 'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'equipment': getattr(e, 'equipment_needed', '') or '', 'status': e.event_status.upper() if e.event_status else '',
            'remarks': e.remarks if e.remarks else '',
            'letter_url': e.letter_of_approval.url if getattr(e, 'letter_of_approval', None) else (e.letter_image.url if getattr(e, 'letter_image', None) else ''),
            'permit_url': e.permit_to_conduct.url if getattr(e, 'permit_to_conduct', None) else (e.permit_image.url if getattr(e, 'permit_image', None) else ''),
            'equipment_url': e.excuse_letter_equipment.url if getattr(e, 'excuse_letter_equipment', None) else (e.equipment_image.url if getattr(e, 'equipment_image', None) else ''),
            'event_cover_photo': e.event_cover_photo.url if getattr(e, 'event_cover_photo', None) else (e.cover_photo.url if getattr(e, 'cover_photo', None) else ''),
            'letter_of_reschedule': e.letter_of_reschedule.url if getattr(e, 'letter_of_reschedule', None) else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if getattr(e, 'reschedule_cover_photo', None) else (getattr(e, 'reschedule_cover_photo_legacy', None).url if getattr(e, 'reschedule_cover_photo_legacy', None) else ''),
            'requirement_mode': e.requirement_mode
        })
        
    return render(request, 'admin/event_approvals.html', {
        'events_json': json.dumps(pending_data),
        'history_json': json.dumps(history_data)
    })

@user_passes_test(is_student_strictly, login_url='/')
def record_attendance(request):
    if request.method == 'POST':
        try:
            student = Student.objects.get(user=request.user)
            event_title = request.POST.get('event_title')
            face_matched = request.POST.get('face_matched') == 'true'
            is_valid_location = request.POST.get('is_valid_location') == 'true'
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            
            event = Event.objects.get(event_title=event_title, event_status='Approved')
            
            attendance = Attendance.objects.create(
                student=student,
                event=event,
                face_matched=face_matched,
                is_valid_location=is_valid_location,
                latitude=lat,
                longitude=lng
            )
            
            # 🟢 GRANULAR AUDIT LOGGING FOR ATTENDANCE
            log_audit_event(request, 'ATTENDANCE', target_model='Event', target_id=event.id, status='Success', changes={
                'event': event_title,
                'student': student.full_name,
                'face_match': face_matched,
                'location': is_valid_location
            })
            
            # 🟢 TRIGGER EMAIL IF ISSUES
            if not face_matched or not is_valid_location:
                face_status = "✅ Matched" if face_matched else "❌ Failed"
                loc_status = "✅ Within Venue" if is_valid_location else "❌ Outside Venue"
                
                send_student_email(student, 'attendance', {
                    'event_title': event.event_title,
                    'face_status': face_status,
                    'location_status': loc_status,
                    'timestamp': attendance.time_in.strftime('%Y-%m-%d %H:%M:%S')
                })
                
            return JsonResponse({'status': 'success', 'message': 'Attendance recorded!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@user_passes_test(is_student_strictly, login_url='/')
def submit_evaluation(request):
    if request.method == 'POST':
        try:
            student = Student.objects.get(user=request.user)
            event_title = request.POST.get('event_title')
            
            rating = request.POST.get('rating')
            if not rating:
                send_student_email(student, 'evaluation', {'event_title': event_title})
                return JsonResponse({'status': 'error', 'message': 'Rating required'})

            # 🟢 LOG EVALUATION ACTION
            log_audit_event(request, 'EVALUATION', status='Success', changes={'event': event_title, 'rating': rating})
            return JsonResponse({'status': 'success', 'message': 'Evaluation saved!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def admin_api_action(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = Event.objects.get(id=data.get('event_id'))
            
            if data.get('action') == 'approve':
                if event.event_status == 'Pending Admin':
                    event.event_status = 'Admin Approved' 
                    event.current_location = "With Student Org (For Signatures)"
                    message = "Initial Approval granted! Student Org must now upload signed permits."
                elif event.event_status == 'Final Admin Review':
                    event.event_status = 'Approved' 
                    event.current_location = "System Published"
                    
                    if data.get('event_date'): event.event_date = data.get('event_date')
                    if data.get('event_time'): event.start_time = data.get('event_time')
                    
                    event.save() # Save before sending emails to ensure data is updated

                    # 🟢 SEND EVENT ALERT TO ALL STUDENTS OF THE ORG
                    students = Student.objects.filter(organization__iexact=event.org_id, is_verified=True, email_notifications=True)
                    for s in students:
                        send_student_email(s, 'event_alert', {
                            'event_title': event.event_title,
                            'org_name': ORG_FULL_NAMES.get(event.org_id, event.org_id),
                            'event_date': event.event_date.strftime('%B %d, %Y'),
                            'start_time': event.start_time.strftime('%I:%M %p'),
                            'venue': event.venue
                        })

                    message = "Signatures verified! Event has been fully approved and published with countdown!"
                else:
                    event.event_status = 'Approved'
                    message = "Event approved."

                event.save()
                return JsonResponse({"status": "success", "message": message})
            
            elif data.get('action') == 'reject':
                event.event_status = 'Rejected'
                event.remarks = data.get('remarks')
                event.save()
                return JsonResponse({"status": "success", "message": "Event Rejected by Admin."})
                
            elif data.get('action') == 'reschedule':
                event.event_date = data.get('event_date')
                event.start_time = data.get('event_time')
                if data.get('event_end_time'):
                    event.end_time = data.get('event_end_time')
                event.remarks = f"Event was rescheduled by Admin to {event.event_date} at {event.start_time}."
                event.save()
                return JsonResponse({"status": "success", "message": "Event successfully rescheduled."})
                
        except Exception as e: return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def manage_accounts_view(request): 
    students = Student.objects.select_related('user').filter(user__is_active=True)
    student_data = []
    
    for s in students:
        status = 'Active' if s.is_verified else 'Pending'
        student_data.append({
            'id': s.id, 'name': s.full_name, 'email': s.email_address, 'username': s.student_number,
            'org': s.organization, 'year': s.year_level, 'birthdate': str(s.birthdate) if s.birthdate else '',
            'status': status, 'avatar': f"https://ui-avatars.com/api/?name={s.full_name}&background=800000&color=fff"
        })
        
    return render(request, 'admin/manage_accounts.html', {'students_json': json.dumps(student_data)})


@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def manage_organizers_view(request): 
    org_profiles = OrgProfile.objects.select_related('user').filter(user__is_active=True)
    org_data = []
    for profile in org_profiles:
        name = profile.user.first_name if profile.user.first_name else "Organizer"
        org_data.append({
            'id': profile.user.id, 'name': name, 'username': profile.user.username,
            'email': profile.user.email,
            'org': profile.organization, 'status': 'Active',
            'avatar': f"https://ui-avatars.com/api/?name={name}&background=800000&color=fff"
        })
    return render(request, 'admin/student_org.html', {'organizers_json': json.dumps(org_data)})


@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def account_history_view(request):
    history_data = []
    students = Student.objects.select_related('user').filter(user__is_active=False)
    for s in students:
        history_data.append({
            'id': f"S-{s.id}", 'name': s.full_name, 'username': s.student_number,
            'org': s.organization, 'year': s.year_level, 'birthdate': str(s.birthdate) if s.birthdate else '',
            'type': 'Student', 'status': 'Deactivated',
            'avatar': f"https://ui-avatars.com/api/?name={s.full_name}&background=800000&color=fff"
        })
    orgs = OrgProfile.objects.select_related('user').filter(user__is_active=False)
    for o in orgs:
        name = o.user.first_name if o.user.first_name else "Organizer"
        history_data.append({
            'id': f"O-{o.user.id}", 'name': name, 'username': o.user.username,
            'org': o.organization, 'year': 'N/A', 'birthdate': '',
            'type': 'Student Org', 'status': 'Deactivated',
            'avatar': f"https://ui-avatars.com/api/?name={name}&background=800000&color=fff"
        })
    return render(request, 'admin/account_history.html', {'history_json': json.dumps(history_data)})

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def student_api_action(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data.get('action') == 'deactivate':
                student = Student.objects.get(id=data.get('id'))
                student.user.is_active = False 
                student.user.save()
                return JsonResponse({"status": "success", "message": "Student deactivated and moved to History."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def organizer_api_action(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')

            if action == 'create':
                username = data.get('username')
                if User.objects.filter(username=username).exists(): return JsonResponse({"status": "error", "message": "Username already exists!"})
                user = User.objects.create_user(username=username, password=data.get('password'), email=data.get('email', ''))
                user.first_name = data.get('name') 
                user.save()
                OrgProfile.objects.create(user=user, organization=data.get('org'))
                return JsonResponse({"status": "success", "message": f"Account for {data.get('org')} successfully created!"})

            elif action == 'edit':
                user_id = data.get('id')
                user = User.objects.get(id=user_id)
                org_profile = OrgProfile.objects.get(user=user)
                new_username = data.get('username')
                if new_username != user.username and User.objects.filter(username=new_username).exists():
                    return JsonResponse({"status": "error", "message": "Username is already taken by another account!"})
                user.first_name = data.get('name')
                user.username = new_username
                user.email = data.get('email', user.email)
                if data.get('password'): user.set_password(data.get('password'))
                user.save()
                org_profile.organization = data.get('org')
                org_profile.save()
                return JsonResponse({"status": "success", "message": "Account credentials updated successfully!"})

            elif action == 'delete': 
                user_id = data.get('id')
                user = User.objects.get(id=user_id)
                user.is_active = False 
                user.save()
                return JsonResponse({"status": "success", "message": "Org access deactivated and moved to History."})

        except Exception as e: return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid Request"})

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def org_monitor_view(request):
    return render(request, 'admin/org_monitor.html')

# ==========================================
# 🟢 ADVISER VIEWS (WITH DYNAMIC ORG FILTERING) 🟢
# ==========================================
@user_passes_test(is_adviser_strictly, login_url='/admin/login/')
def adviser_dashboard(request):
    assigned_org = None
    for org in ORG_FULL_NAMES.keys():
        if org.lower() in request.user.username.lower() or org.lower() in request.user.first_name.lower() or org.lower() in request.user.last_name.lower():
            assigned_org = org
            break
            
    if assigned_org:
        events = Event.objects.filter(org_id__iexact=assigned_org, event_status__in=['Pending Adviser', 'Permit Verification']).order_by('-created_at')
    else:
        events = Event.objects.filter(event_status__in=['Pending Adviser', 'Permit Verification']).order_by('-created_at')

    events_data = []
    for e in events:
        events_data.append({
            'id': e.id, 'org': e.org_id, 'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'equipment': getattr(e, 'equipment_needed', '') or '', 'status': e.event_status.upper() if e.event_status else '',
            'letter_url': e.letter_of_approval.url if getattr(e, 'letter_of_approval', None) else (e.letter_image.url if getattr(e, 'letter_image', None) else ''),
            'permit_url': e.permit_to_conduct.url if getattr(e, 'permit_to_conduct', None) else (e.permit_image.url if getattr(e, 'permit_image', None) else ''),
            'equipment_url': e.excuse_letter_equipment.url if getattr(e, 'excuse_letter_equipment', None) else (e.equipment_image.url if getattr(e, 'equipment_image', None) else ''),
            'event_cover_photo': e.event_cover_photo.url if getattr(e, 'event_cover_photo', None) else (e.cover_photo.url if getattr(e, 'cover_photo', None) else ''),
            'letter_of_reschedule': e.letter_of_reschedule.url if getattr(e, 'letter_of_reschedule', None) else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if getattr(e, 'reschedule_cover_photo', None) else (getattr(e, 'reschedule_cover_photo_legacy', None).url if getattr(e, 'reschedule_cover_photo_legacy', None) else ''),
            'requirement_mode': e.requirement_mode
            })
    return render(request, 'organization adviser/dashboard.html', {'events_json': json.dumps(events_data)})

@user_passes_test(is_adviser_strictly, login_url='/admin/login/')
def adviser_history(request):
    assigned_org = None
    for org in ORG_FULL_NAMES.keys():
        if org.lower() in request.user.username.lower() or org.lower() in request.user.first_name.lower() or org.lower() in request.user.last_name.lower():
            assigned_org = org
            break
            
    if assigned_org:
        events = Event.objects.filter(org_id__iexact=assigned_org).exclude(event_status__in=['Pending Adviser', 'Permit Verification']).order_by('-created_at')
    else:
        events = Event.objects.exclude(event_status__in=['Pending Adviser', 'Permit Verification']).order_by('-created_at')

    events_data = []
    for e in events:
        events_data.append({
            'id': e.id, 'org': e.org_id, 'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'equipment': getattr(e, 'equipment_needed', '') or '', 'status': e.event_status.upper() if e.event_status else '',
            'remarks': e.remarks if e.remarks else '',
            'letter_url': e.letter_of_approval.url if getattr(e, 'letter_of_approval', None) else (e.letter_image.url if getattr(e, 'letter_image', None) else ''),
            'permit_url': e.permit_to_conduct.url if getattr(e, 'permit_to_conduct', None) else (e.permit_image.url if getattr(e, 'permit_image', None) else ''),
            'equipment_url': e.excuse_letter_equipment.url if getattr(e, 'excuse_letter_equipment', None) else (e.equipment_image.url if getattr(e, 'equipment_image', None) else ''),
            'event_cover_photo': e.event_cover_photo.url if getattr(e, 'event_cover_photo', None) else (e.cover_photo.url if getattr(e, 'cover_photo', None) else ''),
            'letter_of_reschedule': e.letter_of_reschedule.url if getattr(e, 'letter_of_reschedule', None) else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if getattr(e, 'reschedule_cover_photo', None) else (getattr(e, 'reschedule_cover_photo_legacy', None).url if getattr(e, 'reschedule_cover_photo_legacy', None) else ''),
            'requirement_mode': e.requirement_mode
        })
    return render(request, 'organization adviser/history.html', {'events_json': json.dumps(events_data)})

@user_passes_test(is_adviser_strictly, login_url='/admin/login/')
def adviser_api_action(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event = Event.objects.get(id=data.get('event_id'))
            
            if data.get('action') == 'approve':
                if event.event_status == 'Pending Adviser':
                    event.event_status = 'Pending Admin'
                    event.current_location = "Admin Office"
                    message = "Forwarded to Administration for initial review."
                elif event.event_status == 'Permit Verification':
                    event.event_status = 'Final Admin Review'
                    event.current_location = "Admin Office (Final Clearance)"
                    message = "Uploaded signatures verified. Forwarded to Admin for final approval."
                else:
                    event.event_status = 'Pending Admin'
                    message = "Forwarded."

                event.save()
                return JsonResponse({"status": "success", "message": message})
            
            elif data.get('action') == 'reject':
                event.event_status = 'Rejected'
                event.remarks = data.get('remarks')
                event.save()
                return JsonResponse({"status": "success", "message": "Event Rejected."})
                
        except Exception as e: return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

# ==========================================
# 🟢 ADMIN AUDIT LOGS (WITH LOCAL TIME FIX) 🟢
# ==========================================
@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def admin_audit_logs(request):
    """
    Dashboard for the Admin to monitor system activity.
    Fetches all logs and passes them as JSON for Vue.js rendering.
    """
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    logs_data = []
    for log in logs:
        # 🟢 Convert UTC to Local Time (Asia/Manila) before displaying
        local_time = localtime(log.timestamp)
        
        logs_data.append({
            'id': log.id,
            'actor': log.actor.username if log.actor else 'Anonymous',
            'action': log.action,
            'target': log.target_model or 'System',
            'status': log.status,
            'ip': log.ip_address,
            'ua': log.user_agent,
            # 🟢 12-hour format with AM/PM for accuracy and readability
            'timestamp': local_time.strftime('%Y-%m-%d %I:%M:%S %p'),
            'changes': log.changes if isinstance(log.changes, dict) else (json.loads(log.changes) if log.changes else {})
        })
        
    return render(request, 'admin/audit_logs.html', {
        'logs_json': json.dumps(logs_data)
    })

def staff_login_view(request):
    if request.method == 'POST':
        is_locked, remaining = check_lockout(request, type='staff')
        if is_locked:
            return JsonResponse({"status": "lockout", "message": "Too many attempts.", "remaining": remaining})

        u = request.POST.get('username')
        p = request.POST.get('password')
        
        # Check Account Lockout
        is_acc_locked, acc_remaining = check_account_lockout(u)
        if is_acc_locked:
            return JsonResponse({"status": "lockout", "message": "Account locked.", "remaining": acc_remaining})

        user = authenticate(request, username=u, password=p)
        
        if user is not None:
            # Check if this is a Student/Organizer trying to login here (RBAC strict separation)
            if not user.is_staff and not user.is_superuser:
                log_audit_event(request, 'LOGIN_FAILED', status='Denied', changes={'reason': 'Student/Organizer attempting Staff Login', 'username': u})
                return JsonResponse({"status": "error", "message": "Student/Organizer accounts must login through the Student Portal (/)."})

            if user.is_staff or user.is_superuser:
                request.session['failed_attempts_staff'] = 0
                if 'lockout_until_staff' in request.session: del request.session['lockout_until_staff']
                reset_account_lockout(u)
                
                login(request, user)
                
                role = 'Admin' if user.is_superuser else 'Adviser'
                log_audit_event(request, 'LOGIN_SUCCESS', status='Success', changes={'role': role})

                redirect_url = '/admin/' if user.is_superuser else '/adviser/dashboard/'
                return JsonResponse({"status": "success", "redirect_url": redirect_url})
            else:
                log_audit_event(request, 'LOGIN_FAILED', status='Denied', changes={'reason': 'No staff privileges', 'username': u})
                return JsonResponse({"status": "error", "message": "Access Denied. You do not have staff privileges."})
        else:
            is_locked_now, lock_time, total_attempts = record_failed_attempt(u)
            
            log_audit_event(request, 'LOGIN_FAILED', status='Failed', changes={'username': u, 'attempt_count': total_attempts})
            
            if is_locked_now:
                request.session['lockout_until_staff'] = (timezone.now() + timedelta(seconds=lock_time)).isoformat()
                return JsonResponse({
                    "status": "lockout", 
                    "message": f"Too many failed attempts ({total_attempts}). Please wait.", 
                    "remaining": lock_time
                })
                
            return JsonResponse({"status": "error", "message": f"Invalid credentials. Attempt {total_attempts % 5} of 5."})
            
    is_locked, remaining = check_lockout(request, type='staff')
    return render(request, 'admin/login.html', {'is_locked': is_locked, 'remaining': remaining})

def debug_database_view(request):
    students = Student.objects.all()
    org_profiles = OrgProfile.objects.all()
    return JsonResponse({
        "status": "success",
        "database_records": {
            "Students": json.loads(serialize('json', students)),
            "Organizers": json.loads(serialize('json', org_profiles))
        }
    }, safe=False, json_dumps_params={'indent': 4})
