from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User 
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail 
from django.conf import settings 
from django.core.serializers import serialize 
from django.template.loader import render_to_string 
from django.utils.html import strip_tags           
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import timedelta, datetime
from django.core.files.base import ContentFile
import json 
import string 
import random 
import os 
import io
import base64
import zipfile
from docxtpl import DocxTemplate 
from .models import OrgProfile, Student, Attendance, Event, LoginLockout, AuditLog
from .utils import log_audit_event
from .middleware import get_current_request
from .ai_utils import verify_face, get_sentiment, get_rating_sentiment
from django.core.cache import cache

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

def get_img(e):
    if not e: return '/static/images/PUPLogo.png'
    if hasattr(e, 'event_cover_photo') and e.event_cover_photo: return e.event_cover_photo.url
    if hasattr(e, 'cover_photo') and e.cover_photo: return e.cover_photo.url
    if hasattr(e, 'thumbnail') and e.thumbnail: return e.thumbnail.url
    return '/static/images/PUPLogo.png'

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

        # Check if user exists BEFORE applying lockout logic
        if not User.objects.filter(username=student_number).exists():
            log_audit_event(request, 'LOGIN_FAILED', status='Failed', changes={'reason': 'Account does not exist', 'username': student_number})
            return JsonResponse({"status": "error", "message": "Account does not exist. Please register first."})

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
            
            # Since we checked existence above, we can attribute this to the user
            existing_user = User.objects.filter(username=student_number).first()
            log_audit_event(request, 'LOGIN_FAILED', status='Failed', changes={'username': student_number, 'attempt_count': total_attempts}, actor=existing_user)

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
                if OrgProfile.objects.filter(user=user).exists():
                    log_audit_event(request, 'PASSWORD_RESET_REQUEST', status='Warning', changes={'message': f'Organizer {user.username} requested a password reset.'}, actor=user)
                    return JsonResponse({"status": "success", "message": "Admin has been notified of your password reset request. Please wait for them to generate a new password."})
                else:
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

def poll_organizer_password(request):
    if request.method == 'GET':
        username = request.GET.get('username')
        if not username:
            return JsonResponse({"status": "error", "message": "Missing username."})
        
        # Check cache for the password generated by Admin
        new_pwd = cache.get(f'reset_pwd_{username}')
        if new_pwd:
            # Delete it from cache to prevent security leaks
            cache.delete(f'reset_pwd_{username}')
            return JsonResponse({"status": "completed", "password": new_pwd})
        
        return JsonResponse({"status": "waiting"})
    return JsonResponse({"status": "error", "message": "Invalid request."})

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
    recent_notifications = notifications[:10]  # Increased to top 10 for better coverage

    # 🟢 STATS FOR STUDENT
    all_events_count = Event.objects.filter(
        Q(org_id=student.organization) | 
        Q(is_flag_raising=True) |
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved', event_date__lt=timezone.now().date()).count()

    attended_count = Attendance.objects.filter(student=student).count()
    present_count = Attendance.objects.filter(student=student, face_matched=True, is_valid_location=True).count()
    absent_count = max(0, all_events_count - present_count)

    # 🟢 RECENT ACTIVITY LOGS
    # Get latest 3 attendance records and 3 audit logs for evaluations
    recent_attendance = Attendance.objects.filter(student=student).order_by('-time_in')[:3]
    
    # Using AuditLog to find recent evaluations
    from .models import AuditLog
    recent_evals = AuditLog.objects.filter(actor=request.user, action='EVALUATION').order_by('-timestamp')[:3]
    
    recent_activity = []
    for att in recent_attendance:
        details = {
            'face_matched': att.face_matched,
            'is_valid_location': att.is_valid_location,
            'timestamp': att.time_in.strftime('%B %d, %Y at %I:%M %p'),
            'capture_url': att.capture_image.url if att.capture_image else None,
            'coords': f"{att.latitude}, {att.longitude}" if att.latitude else "N/A"
        }
        recent_activity.append({
            'id': f'att_{att.id}',
            'type': 'Attendance',
            'title': att.event.event_title,
            'venue': att.event.venue,
            'date': att.time_in.strftime('%b %d, %Y'),
            'time': att.time_in.strftime('%I:%M %p'),
            'icon': 'ph-user-focus',
            'color': 'text-green-500',
            'bg': 'bg-green-50 dark:bg-green-900/20',
            'timestamp': att.time_in,
            'details': details,
            'details_json': json.dumps(details)
        })
    
    for evl in recent_evals:
        changes = evl.changes if isinstance(evl.changes, dict) else json.loads(evl.changes)
        title = changes.get('event', 'Event Evaluation')
        
        # Try to find the event to get venue
        event = Event.objects.filter(event_title=title).first()
        venue = event.venue if event else 'Campus Event'

        details = {
            'rating': changes.get('rating', '0'),
            'feedback': changes.get('feedback', 'No feedback provided.'),
            'total_raw_score': changes.get('total_raw_score', '0'),
            'detailed_scores': changes.get('detailed_scores', {}),
            'sentiment': changes.get('sentiment', None) # Pass VADER result
        }

        recent_activity.append({
            'id': f'eval_{evl.id}',
            'type': 'Evaluation',
            'title': title,
            'venue': venue,
            'date': evl.timestamp.strftime('%b %d, %Y'),
            'time': evl.timestamp.strftime('%I:%M %p'),
            'icon': 'ph-star',
            'color': 'text-blue-500',
            'bg': 'bg-blue-50 dark:bg-blue-900/20',
            'timestamp': evl.timestamp,
            'details': details,
            'details_json': json.dumps(details)
        })
    
    # Sort activity by actual timestamp
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activity = recent_activity[:5]

    context = {
        'student': student,
        'notifications': recent_notifications,
        'attended_count': attended_count,
        'present_count': present_count,
        'absent_count': absent_count,
        'recent_activity': recent_activity
    }
    return render(request, 'student/profile.html', context)

def get_student_notifications(student):
    if not student.email_notifications:
        return []

    notifications = []
    now = timezone.now()
    today = now.date()

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

    # 2. Upcoming & Newly Published Events
    # Filter: Own Org + Global Events
    relevant_events = Event.objects.filter(
        Q(org_id=student.organization) | 
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved')

    upcoming_events = relevant_events.filter(event_date__gte=today).order_by('event_date')[:8]

    for evt in upcoming_events:
        # Check if it was recently approved (last 3 days)
        is_new = (now - evt.created_at).days <= 3
        prefix = "🔥 NEW EVENT: " if is_new else "Upcoming: "

        # Check for rescheduling in remarks
        is_rescheduled = evt.remarks and "rescheduled" in evt.remarks.lower()
        if is_rescheduled:
            prefix = "📅 RESCHEDULED: "

        notifications.append({
            'id': f"event_{evt.id}",
            'type': 'update' if is_rescheduled else ('new' if is_new else 'event'),
            'title': f"{prefix}{evt.event_title}",
            'message': f"Event '{evt.event_title}' is happening on {evt.event_date.strftime('%B %d')} at {evt.venue}. {evt.remarks if is_rescheduled else 'Don\'t miss out!'}",
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

    # 4. Evaluation Reminders
    # Attended events in the last 14 days that have ended
    recent_attended = Attendance.objects.filter(
        student=student, 
        face_matched=True, 
        is_valid_location=True,
        event__event_date__lt=today,
        event__event_date__gte=today - timedelta(days=14)
    ).select_related('event')

    # Check which ones are already evaluated via AuditLog
    evaluated_ids = list(AuditLog.objects.filter(
        actor=student.user, 
        action='EVALUATION', 
        status='Success'
    ).values_list('target_id', flat=True))

    for att in recent_attended:
        if str(att.event.id) not in evaluated_ids:
            notifications.append({
                'id': f"eval_rem_{att.event.id}",
                'type': 'evaluation',
                'title': f"Feedback Required: {att.event.event_title}",
                'message': f"How was '{att.event.event_title}'? Please share your feedback in the Evaluation Hub to help us improve!",
                'sender': 'System',
                'date': att.event.event_date.strftime('%b %d, %Y'),
                'timestamp': att.event.event_date.timestamp() + 86400, # Set to day after event
                'status': 'Pending'
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
def update_student_face(request):
    if request.method == 'POST':
        try:
            student = Student.objects.get(user=request.user)
            face_data = request.POST.get('face_encoding')
            if not face_data:
                return JsonResponse({'status': 'error', 'message': 'No facial data received.'})
            
            student.face_encoding = face_data
            student.save()
            
            log_audit_event(request, 'UPDATE', target_model='Student', target_id=str(student.id), status='Success', changes={'face_encoding': 'Updated'})
            return JsonResponse({'status': 'success', 'message': 'Face identity updated successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

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
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    org_acronym = student.organization.strip()

    # 🟢 Fetch OrgProfile for the student's organization
    org_profile = OrgProfile.objects.filter(organization=org_acronym).first()
    
    # 🟢 RBAC Filtered: Own Org + Global Events
    org_filter = Q(org_id=org_acronym) | Q(event_title__icontains='Flag Raising') | Q(event_title__icontains='General Assembly') | Q(event_title__icontains='Student Week')

    # Show events from 7 days ago onwards to include recent past events as requested
    recent_limit = timezone.now().date() - timedelta(days=7)
    upcoming_events = Event.objects.filter(org_filter).filter(
        event_status='Approved',
        event_date__gte=recent_limit
    ).order_by('event_date', 'start_time')[:4]
    
    latest_news = Event.objects.filter(org_filter).filter(event_status='Approved').order_by('-created_at')[:4]

    # --- 🟢 STRICT ORGANIZATION-SPECIFIC SLIDESHOW LOGIC 🟢 ---
    slideshow_images = []
    import os
    from django.conf import settings
    
    org_img_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'orgImage', org_acronym)
    if os.path.exists(org_img_dir):
        files = os.listdir(org_img_dir)
        # 1. Identify Logo (Must be first)
        logo_file = next((f for f in files if f.lower().startswith(org_acronym.lower()) and f.lower().endswith(('.png', '.jpg', '.jpeg'))), None)
        if logo_file:
            slideshow_images.append({
                'url': f'/static/images/orgImage/{org_acronym}/{logo_file}',
                'is_logo': True
            })
        
        # 2. Add other images from folder (and only from folder)
        other_files = [f for f in files if f != logo_file and f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        for f in other_files:
            slideshow_images.append({
                'url': f'/static/images/orgImage/{org_acronym}/{f}',
                'is_logo': False
            })

    # Final Fallback if folder empty
    if not slideshow_images:
        slideshow_images = [{'url': '/static/images/PUPLogo.png', 'is_logo': True}]

    def clean_desc(desc):
        if not desc: return 'No description provided.'
        # Remove [NEW EVENT] or [RESCHEDULE] tags and technical metadata
        if "Desc:" in desc:
            return desc.split("Desc:")[1].strip()
        return desc

    upcoming_data = []
    for e in upcoming_events:
        upcoming_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y').upper(),
            'location': e.venue,
            'image': get_img(e),
            'description': clean_desc(e.description)
        })

    news_data = []
    for e in latest_news:
        news_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.created_at.strftime('%b %d, %Y').upper(),
            'location': e.venue,
            'image': get_img(e),
            'description': clean_desc(e.description)
        })

    # 🟢 DYNAMIC ACTION REQUIRED LOGIC 🟢
    now = timezone.now()
    action_required = None
    
    # 1. Look for an ACTIVE or RECENT event today
    active_events = Event.objects.filter(org_filter).filter(
        event_status='Approved', 
        event_date=now.date(),
        end_time__gt=now.time()
    ).order_by('start_time')
    
    evaluated_titles = list(AuditLog.objects.filter(actor=request.user, action='EVALUATION', status='Success').values_list('changes__event', flat=True))

    for e in active_events:
        # Get student's attendance for this event
        att = Attendance.objects.filter(student=student, event_id=e.id).first()
        
        # Scenario A: Has not Timed In yet
        if not att:
            # Only if event has started or about to start (within 30 mins)
            start_dt = timezone.make_aware(datetime.combine(e.event_date, e.start_time))
            if now >= (start_dt - timedelta(minutes=30)):
                action_required = {
                    'id': e.id, 'type': 'attendance', 'title': 'Time In Required',
                    'message': f"Log your attendance for '{e.event_title}' now.",
                    'button_text': 'Check In Now', 'url': '/student/school-events/'
                }
                break

        # Scenario B: Timed In but NOT yet Timed Out
        elif att and not att.time_out:
            # Check if it's near/past end time
            if e.end_time:
                end_dt = timezone.make_aware(datetime.combine(e.event_date, e.end_time))
                # Allow timeout 15 mins before end
                if now >= (end_dt - timedelta(minutes=15)):
                    action_required = {
                        'id': e.id, 'type': 'attendance', 'title': 'Time Out Required',
                        'message': f"Don't forget to time out for '{e.event_title}'.",
                        'button_text': 'Check Out Now', 'url': '/student/school-events/'
                    }
                    break
        
        # Scenario C: Timed Out but NOT yet Evaluated
        elif att and att.time_out and e.event_title not in evaluated_titles:
            action_required = {
                'id': e.id, 'type': 'evaluation', 'title': 'Evaluation Required',
                'message': f"Please share your feedback for '{e.event_title}'.",
                'button_text': 'Evaluate Now', 'url': '/student/evaluation/'
            }
            break

    # Fetch all approved events for the calendar (Own Org + Global)
    all_approved_events = Event.objects.filter(org_filter).filter(event_status='Approved').order_by('-event_date')
    calendar_data = []
    for e in all_approved_events:
        calendar_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%Y-%m-%d'),
            'status': e.event_status,
            'venue': e.venue,
            'description': clean_desc(e.description),
            'start_time': e.start_time.strftime('%I:%M %p') if e.start_time else "",
            'end_time': e.end_time.strftime('%I:%M %p') if e.end_time else "",
            'image': get_img(e)
        })

    context = {
        'student': student,
        'latest_news_json': json.dumps(news_data),
        'calendar_events_json': json.dumps(calendar_data),
        'action_required_json': json.dumps(action_required),
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'org_about': ORG_ABOUT_US.get(org_acronym, "Advancing university excellence."),
        'slideshow_images': slideshow_images,
    }
    return render(request, 'student/homepage.html', context)

@user_passes_test(is_student_strictly, login_url='/')
def student_school_events(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    # 🟢 RBAC Filtered: Own Org + Global Events
    all_events = Event.objects.filter(
        Q(org_id=student.organization) | 
        Q(is_flag_raising=True) |
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved').order_by('-event_date', '-start_time')
    
    # 🟢 DETAILED ATTENDANCE TRACKING 🟢
    attendance_qs = Attendance.objects.filter(student=student)
    attendance_map = {str(att.event_id): att for att in attendance_qs}

    def clean_desc(desc):
        if not desc: return 'Join us for this exciting campus activity managed by university organizations.'
        if "Desc:" in desc:
            return desc.split("Desc:")[1].strip()
        return desc

    events_data = []
    for e in all_events:
        img_url = ""
        if e.event_cover_photo: img_url = e.event_cover_photo.url
        elif e.cover_photo: img_url = e.cover_photo.url
        elif e.thumbnail: img_url = e.thumbnail.url
        else: img_url = '/static/images/PUPLogo.png'

        att_record = attendance_map.get(str(e.id))

        events_data.append({
            'id': e.id,
            'title': e.event_title,
            'org': e.org_id,
            'date': e.event_date.strftime('%Y-%m-%d'),
            'date_display': e.event_date.strftime('%b %d, %Y').upper(),
            'time': e.start_time.strftime('%I:%M %p'),
            'start_time_iso': e.start_time.strftime('%H:%M:%S'),
            'end_time': e.end_time.strftime('%I:%M %p') if e.end_time else 'TBD',
            'end_time_iso': e.end_time.strftime('%H:%M:%S') if e.end_time else '',
            'venue': e.venue,
            'image': img_url,
            'description': clean_desc(e.description),
            'is_flag_raising': getattr(e, 'is_flag_raising', False),
            'target_lat': float(e.target_latitude) if e.target_latitude else 13.84615,
            'target_lng': float(e.target_longitude) if e.target_longitude else 121.96955,
            'already_attended': att_record is not None,
            'has_timed_out': att_record.time_out is not None if att_record else False,
        })
    
    student_data = {
        'face_encoding': student.face_encoding
    }

    return render(request, 'student/school_events.html', {
        'events_json': json.dumps(events_data),
        'student_json': json.dumps(student_data)
    })

@user_passes_test(is_student_strictly, login_url='/')
def student_event_calendar(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    # 🟢 RBAC Filtered: Own Org + Global Events
    approved_events = Event.objects.filter(
        Q(org_id=student.organization) | 
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved').order_by('event_date', 'start_time')
    
    # Prepare data for FullCalendar
    def clean_desc(desc):
        if not desc: return 'No description provided.'
        if "Desc:" in desc:
            return desc.split("Desc:")[1].strip()
        clean = desc.replace("[NEW EVENT]", "").replace("[RESCHEDULE]", "").strip()
        return clean if clean else 'No description provided.'

    events_data = []
    for event in approved_events:
        # Default image logic
        img_url = '/static/images/PUPLogo.png'
        if event.thumbnail:
            img_url = event.thumbnail.url
        elif event.event_cover_photo:
            img_url = event.event_cover_photo.url
        elif event.cover_photo:
            img_url = event.cover_photo.url

        events_data.append({
            'title': event.event_title,
            'start': event.event_date.isoformat(),
            'backgroundColor': '#800000',
            'borderColor': '#800000',
            'extendedProps': {
                'description': clean_desc(event.description),
                'venue': event.venue,
                'time': event.start_time.strftime('%I:%M %p'),
                'category': event.org_id,
                'image': img_url
            }
        })

    now = timezone.now()
    # Total upcoming events for CURRENT month
    upcoming_this_month_count = approved_events.filter(
        event_date__year=now.year,
        event_date__month=now.month,
        event_date__gte=now.date()
    ).count()

    # Masterlist: All approved events from today onwards
    masterlist_events = approved_events.filter(event_date__gte=now.date())
    for e in masterlist_events:
        e.cleaned_description = clean_desc(e.description)

    context = {
        'events_json': json.dumps(events_data),
        'masterlist_events': masterlist_events,
        'total_upcoming_month': upcoming_this_month_count,
        'current_month_year': now.strftime('%B %Y').upper()
    }
    return render(request, 'student/event_calendar.html', context)

@user_passes_test(is_student_strictly, login_url='/')
def student_evaluation(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    # 🟢 RBAC Filtered: Own Org + Global Events
    all_events = Event.objects.filter(
        Q(org_id=student.organization) | 
        Q(is_flag_raising=True) |
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved').order_by('-event_date', '-start_time')
    
    # 🟢 ATTENDANCE CHECK FOR EVALUATION (Must have timed out) 🟢
    attendance_qs = Attendance.objects.filter(student=student)
    attendance_map = {str(att.event_id): att for att in attendance_qs}

    evaluated_ids = [str(eid) for eid in list(AuditLog.objects.filter(
        actor=request.user, 
        action='EVALUATION', 
        status='Success'
    ).values_list('target_id', flat=True)) if eid]

    def clean_desc(desc):
        if not desc: return 'No description provided.'
        if "Desc:" in desc:
            return desc.split("Desc:")[1].strip()
        clean = desc.replace("[NEW EVENT]", "").replace("[RESCHEDULE]", "").strip()
        return clean if clean else 'No description provided.'

    events_data = []
    for e in all_events:
        img_url = ""
        if e.event_cover_photo: img_url = e.event_cover_photo.url
        elif e.cover_photo: img_url = e.cover_photo.url
        elif e.thumbnail: img_url = e.thumbnail.url
        else: img_url = '/static/images/PUPLogo.png'

        att_record = attendance_map.get(str(e.id))
        is_eligible = att_record is not None and att_record.time_out is not None

        events_data.append({
            'id': e.id,
            'title': e.event_title,
            'org': e.org_id,
            'date': e.event_date.strftime('%Y-%m-%d'),
            'date_display': e.event_date.strftime('%b %d, %Y').upper(),
            'time': e.start_time.strftime('%I:%M %p'),
            'start_time_iso': e.start_time.strftime('%H:%M:%S'),
            'end_time': e.end_time.strftime('%I:%M %p') if e.end_time else 'TBD',
            'end_time_iso': e.end_time.strftime('%H:%M:%S') if e.end_time else '',
            'venue': e.venue,
            'image': img_url,
            'description': e.description,
            'cleaned_description': clean_desc(e.description),
            'org': e.org_id,
            'already_evaluated': str(e.id) in evaluated_ids,
            'is_eligible': is_eligible,
            'att_status': 'No Time In' if not att_record else ('Pending Time Out' if not att_record.time_out else 'Ready')
        })

    history_logs = AuditLog.objects.filter(actor=request.user, action='EVALUATION').order_by('-timestamp')
    history_data = []
    for log in history_logs:
        try:
            changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
            history_data.append({
                'title': changes.get('event', 'Unknown Event'),
                'date': log.timestamp.strftime('%b %d, %Y'),
                'time': log.timestamp.strftime('%I:%M %p'),
                'rating': changes.get('rating', '0'),
                'feedback': changes.get('feedback', 'No feedback provided.'),
                'sentiment': changes.get('sentiment', None)
            })
        except: continue

    return render(request, 'student/evaluation.html', {
        'events_json': json.dumps(events_data),
        'history_json': json.dumps(history_data)
    })


@user_passes_test(is_student_strictly, login_url='/')
def student_evaluation_form(request): return render(request, 'student/evaluation_form.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_event_history(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('index')

    # 1. Fetch Attendance Records
    attendance_qs = Attendance.objects.filter(student=student).select_related('event').order_by('-time_in')
    history_data = []

    for att in attendance_qs:
        e = att.event
        img_url = '/static/images/PUPLogo.png'
        if e.thumbnail: img_url = e.thumbnail.url
        elif e.event_cover_photo: img_url = e.event_cover_photo.url
        elif e.cover_photo: img_url = e.cover_photo.url

        history_data.append({
            'id': f"att_{att.id}",
            'title': e.event_title,
            'date': att.time_in.strftime('%b %d, %Y'),
            'time': att.time_in.strftime('%I:%M %p'),
            'venue': e.venue,
            'type': 'Attendance',
            'img': img_url,
            'details': {
                'face_matched': att.face_matched,
                'is_valid_location': att.is_valid_location,
                'timestamp': att.time_in.strftime('%B %d, %Y at %I:%M %p'),
                'capture_url': att.capture_image.url if att.capture_image else None,
                'coords': f"{att.latitude}, {att.longitude}" if att.latitude else "N/A"
            }
        })

    # 2. Fetch Evaluation Records (from AuditLog)
    eval_logs = AuditLog.objects.filter(actor=request.user, action='EVALUATION', status='Success').order_on_timestamp = AuditLog.objects.filter(actor=request.user, action='EVALUATION', status='Success').order_by('-timestamp')
    for log in eval_logs:
        changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
        
        # Try to find the event to get venue and image
        event_title = changes.get('event', 'Unknown Event')
        event = Event.objects.filter(event_title=event_title).first()
        
        img_url = '/static/images/PUPLogo.png'
        venue = 'Campus Event'
        if event:
            if event.thumbnail: img_url = event.thumbnail.url
            elif event.event_cover_photo: img_url = event.event_cover_photo.url
            venue = event.venue

        history_data.append({
            'id': f"eval_{log.id}",
            'title': event_title,
            'date': log.timestamp.strftime('%b %d, %Y'),
            'time': log.timestamp.strftime('%I:%M %p'),
            'venue': venue,
            'type': 'Evaluation',
            'img': img_url,
            'details': {
                'rating': changes.get('rating', '0'),
                'feedback': changes.get('feedback', 'No feedback provided.'),
                'sentiment': changes.get('sentiment', None),
                'total_raw_score': changes.get('total_raw_score', '0'),
                'detailed_scores': changes.get('detailed_scores', {})
            }
        })

    # Sort combined history by date (latest first)
    # Since they are strings, we might need a better sort, but let's keep it simple for now or pass raw timestamps
    
    return render(request, 'student/event_history.html', {
        'history_json': json.dumps(history_data)
    })

# ==========================================
# ORGANIZER VIEWS
# ==========================================

ORG_ABOUT_US = {
    "ITO": "Home for tech enthusiasts. We bridge theory and practice through bootcamps and seminars.",
    "YEO": "Cultivating business leaders. We provide a platform for startups and financial literacy.",
    "ITS": "Uniting DOMT and DIT. We bridge administrative efficiency with digital innovation.",
    "FTO": "Molding tomorrow's leaders. We prepare educators through demos and outreach.",
    "PAS": "Training leaders in service. We offer a platform for governance and reforms.",
    "CAO": "Heartbeat of campus creativity. We showcase talent through theater, dance, and music.",
    "PRIDEVerse": "Advocacy for LGBTQIA+. We promote equality and a safe campus environment.",
    "SSC": "Voice of the student body. We protect rights through leadership and initiatives.",
    "ROTC": "Instilling discipline and duty. We provide military science and disaster training.",
    "NEWSETTE": "Official student publication. Delivering timely news and fearless journalism.",
    "PUSO": "Driving athletic endeavors. We promote sportsmanship and physical wellness."
}

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_homepage(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
        org_profile = None

    # --- 🟢 ORGANIZATION-SPECIFIC SLIDESHOW LOGIC 🟢 ---
    # Strictly only from the static folder as requested
    slideshow_images = []
    import os
    from django.conf import settings
    
    org_img_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'orgImage', org_acronym)
    if os.path.exists(org_img_dir):
        files = os.listdir(org_img_dir)
        # Prioritize Logo (File starting with acronym)
        logo_file = next((f for f in files if f.lower().startswith(org_acronym.lower()) and f.lower().endswith(('.png', '.jpg', '.jpeg'))), None)
        if logo_file:
            slideshow_images.append({'url': f'/static/images/orgImage/{org_acronym}/{logo_file}', 'is_logo': True})
        
        # Add other background images from the same folder
        other_files = [f for f in files if f != logo_file and f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        for f in other_files:
            slideshow_images.append({'url': f'/static/images/orgImage/{org_acronym}/{f}', 'is_logo': False})

    # Final Fallback if folder is empty or doesn't exist
    if not slideshow_images:
        slideshow_images = [
            {'url': '/static/images/org1.jpg', 'is_logo': False},
            {'url': '/static/images/PUPLogo.png', 'is_logo': True}
        ]

    # 🟢 Latest News: Own Org + Global Events
    latest_news = Event.objects.filter(
        Q(org_id=org_acronym) | 
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved').order_by('-created_at')[:4]

    def clean_desc(desc):
        if not desc: return 'No description provided.'
        # Remove [NEW EVENT] or [RESCHEDULE] tags and technical metadata
        if "Desc:" in desc:
            return desc.split("Desc:")[1].strip()
        # Remove common tags if they still exist
        clean = desc.replace("[NEW EVENT]", "").replace("[RESCHEDULE]", "").strip()
        return clean if clean else 'No description provided.'

    news_data = []
    for e in latest_news:
        news_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.created_at.strftime('%b %d, %Y').upper(),
            'image': get_img(e) or '/static/images/PUPLogo.png',
            'description': clean_desc(e.description),
            'location': e.venue or 'PUP Unisan'
        })

    # Stats Calculation
    today = timezone.now().date()
    active_members_count = Student.objects.filter(organization=org_acronym, is_verified=True).count()
    upcoming_events_count = Event.objects.filter(org_id=org_acronym, event_status='Approved', event_date__gte=today).count()
    pending_proposals_count = Event.objects.filter(org_id=org_acronym).exclude(event_status__in=['Approved', 'Rejected']).count()
    managed_events_count = Event.objects.filter(org_id=org_acronym, event_status='Approved', event_date__lt=today).count()

    # All Events for Calendar
    all_events = Event.objects.filter(org_id=org_acronym).order_by('-event_date')
    calendar_data = []
    for e in all_events:
        calendar_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%Y-%m-%d'),
            'status': e.event_status,
            'venue': e.venue,
            'description': clean_desc(e.description),
            'start_time': e.start_time.strftime('%I:%M %p') if e.start_time else "",
            'end_time': e.end_time.strftime('%I:%M %p') if e.end_time else "",
            'image': get_img(e) or '/static/images/PUPLogo.png'
        })

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'about_us_text': ORG_ABOUT_US.get(org_acronym, "Welcome to our organization! We are dedicated to serving the student body."),
        'latest_news_json': json.dumps(news_data),
        'calendar_events_json': json.dumps(calendar_data),
        'active_members_count': active_members_count,
        'upcoming_events_count': upcoming_events_count,
        'pending_proposals_count': pending_proposals_count,
        'managed_events_count': managed_events_count,
        'slideshow_images': slideshow_images,
    }
    return render(request, 'organizer/homepage.html', context)

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_school_events(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
        org_profile = None

    # 🟢 RBAC Filtered Ledger: Own Org + Global Events
    all_events = Event.objects.filter(
        Q(org_id=org_acronym) | 
        Q(event_title__icontains='Flag Raising') | 
        Q(event_title__icontains='General Assembly') | 
        Q(event_title__icontains='Student Week')
    ).filter(event_status='Approved').order_by('-event_date', '-start_time')
    
    # 🟢 DETAILED ATTENDANCE TRACKING 🟢
    attendance_map = {}
    if org_profile:
        attendance_qs = Attendance.objects.filter(organizer=org_profile)
        attendance_map = {str(att.event_id): att for att in attendance_qs}

    def clean_desc(desc):
        if not desc: return 'No description provided.'
        if "Desc:" in desc:
            return desc.split("Desc:")[1].strip()
        clean = desc.replace("[NEW EVENT]", "").replace("[RESCHEDULE]", "").strip()
        return clean if clean else 'No description provided.'

    events_data = []
    for e in all_events:
        img_url = ""
        if e.event_cover_photo: img_url = e.event_cover_photo.url
        elif e.cover_photo: img_url = e.cover_photo.url
        elif e.thumbnail: img_url = e.thumbnail.url
        else: img_url = '/static/images/PUPLogo.png'

        # 🟢 ADD COUNTS FOR ORGANIZER MONITORING 🟢
        att_count = Attendance.objects.filter(event=e).count()
        eval_count = AuditLog.objects.filter(action='EVALUATION', target_id=str(e.id)).count()

        att_record = attendance_map.get(str(e.id))

        events_data.append({
            'id': e.id,
            'title': e.event_title,
            'org': e.org_id,
            'date': e.event_date.strftime('%Y-%m-%d'),
            'date_display': e.event_date.strftime('%b %d, %Y').upper(),
            'time': e.start_time.strftime('%I:%M %p'),
            'start_time_iso': e.start_time.strftime('%H:%M:%S'),
            'end_time': e.end_time.strftime('%I:%M %p') if e.end_time else 'TBD',
            'end_time_iso': e.end_time.strftime('%H:%M:%S') if e.end_time else '',
            'venue': e.venue,
            'image': img_url,
            'description': clean_desc(e.description),
            'attendance_count': att_count,
            'evaluation_count': eval_count,
            'target_lat': float(e.target_latitude) if e.target_latitude else 13.84615,
            'target_lng': float(e.target_longitude) if e.target_longitude else 121.96955,
            'already_attended': att_record is not None,
            'has_timed_out': att_record.time_out is not None if att_record else False,
        })

    organizer_data = {
        'face_encoding': org_profile.face_encoding if org_profile else None
    }

    return render(request, 'organizer/school_events.html', {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'events_json': json.dumps(events_data),
        'organizer_json': json.dumps(organizer_data)
    })


@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_create_events(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
        
    events = Event.objects.filter(org_id=org_acronym).order_by('-created_at')
    events_data = []
    docs_data = []

    # 📍 Campus Landmarks for PUP Unisan (Kalilayan Ibaba) - Wider Spread
    HUB_COORDS = [13.84545, 121.96885]    # Student Center (SW)
    ADVISER_COORDS = [13.84575, 121.96915] # Faculty Lounge (Middle)
    ADMIN_COORDS = [13.84615, 121.96955]   # Academic Bldg (NE)

    # 🟢 REAL-TIME LOCATION LOGIC 🟢
    from .models import UserLocation
    adviser_loc = UserLocation.objects.filter(user__is_staff=True, user__is_superuser=False).order_by('-last_updated').first()
    if adviser_loc and adviser_loc.latitude and adviser_loc.longitude:
        ADVISER_COORDS = [float(adviser_loc.latitude), float(adviser_loc.longitude)]

    admin_loc = UserLocation.objects.filter(user__is_superuser=True).order_by('-last_updated').first()
    if admin_loc and admin_loc.latitude and admin_loc.longitude:
        ADMIN_COORDS = [float(admin_loc.latitude), float(admin_loc.longitude)]
    
    for e in events:
        events_data.append({
            'id': e.id,
            'title': e.event_title or "",
            'date': e.event_date.strftime('%Y-%m-%d') if e.event_date else '', # Fix format for JS new Date()
            'start_time': e.start_time.strftime('%H:%M') if e.start_time else '', 
            'end_time': e.end_time.strftime('%H:%M') if getattr(e, 'end_time', None) else '', 
            'venue': e.venue or "",
            'description': e.description or "",
            'requester_name': getattr(e, 'requester_name', '') or "",
            'adviser_name': getattr(e, 'adviser_name', '') or "",
            'status': e.event_status.upper() if e.event_status else "",
            'org': org_acronym
        })

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

    # Fetch approved events for rescheduling dropdown
    approved_events = Event.objects.filter(org_id=org_acronym, event_status='Approved').values('id', 'event_title', 'event_date')
    approved_events_list = []
    for ae in approved_events:
        approved_events_list.append({
            'id': ae['id'],
            'title': ae['event_title'],
            'date': ae['event_date'].strftime('%Y-%m-%d')
        })

    return render(request, 'organizer/create_events.html', {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'events_json': json.dumps(events_data),
        'documents_json': json.dumps(docs_data),
        'approved_events_json': json.dumps(approved_events_list)
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
            is_flag_raising = request.POST.get('is_flag_raising') == 'true'

            if event_id:
                # 🟢 RESCHEDULE / EDIT EXISTING EVENT 🟢
                event = Event.objects.get(id=event_id, org_id=org_acronym)
                event.requester_name = requester_name
                event.event_title = title
                event.event_date = event_date
                event.start_time = start_time
                event.venue = venue
                event.description = description or f"Updated activity for {org_acronym}."
                
                if hasattr(event, 'end_time'): event.end_time = end_time
                if hasattr(event, 'adviser_name'): event.adviser_name = adviser_name
                if hasattr(event, 'equipment_needed'): event.equipment_needed = "" 
                
                event.event_status = 'Pending Adviser' 
                event.current_location = 'Office of the Adviser'
                event.save()
                message = "Event proposal updated and resubmitted to Adviser successfully!"
            else:
                # 🟢 CREATE NEW EVENT 🟢
                status = 'Pending Adviser'
                loc = 'Office of the Adviser'
                
                # 🟢 FAST-TRACK BYPASS FOR FLAG RAISING 🟢
                if is_flag_raising:
                    status = 'Approved'
                    loc = 'System Published'
                    if not requester_name: requester_name = f"{org_acronym} President"

                event = Event(
                    org_id=org_acronym,
                    proposal_by_user_id=request.user.username,
                    requester_name=requester_name,
                    event_title=title,
                    event_date=event_date,
                    start_time=start_time,
                    venue=venue,
                    description=description or f"Flag Raising ceremony hosted by {org_acronym}.",
                    event_status=status,
                    current_location=loc,
                    is_flag_raising=is_flag_raising
                )
                if hasattr(event, 'end_time'): event.end_time = end_time
                if hasattr(event, 'adviser_name'): event.adviser_name = adviser_name
                if hasattr(event, 'equipment_needed'): event.equipment_needed = ""
                
                if is_flag_raising and request.FILES.get('cover_photo'):
                    event.event_cover_photo = request.FILES.get('cover_photo')

                event.save()
                message = "Flag Raising posted directly!" if is_flag_raising else "New event proposal submitted to Adviser successfully!"

            return JsonResponse({"status": "success", "message": message})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

# 🟢 DYNAMIC DOCX GENERATOR (HANDLES ZIP FOR MULTIPLE DOCUMENTS) 🟢
@user_passes_test(is_organizer_strictly, login_url='/')
def download_event_proposal_doc(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            doc_type = data.get('docType', 'approval')
            
            # Map of docTypes to template sets
            # new_event -> [Approval, Excuse]
            # reschedule_event -> [Reschedule, Excuse]
            # legacy/single -> [Original logic]
            
            templates_to_render = []
            if doc_type == 'new_event':
                templates_to_render = [
                    {'tpl': 'TEMPLATE_APPROVAL.docx', 'name': '1_Request_Letter.docx'},
                    {'tpl': 'TEMPLATE_EXCUSE.docx', 'name': '2_Excuse_and_Usage_Letter.docx'}
                ]
            elif doc_type == 'reschedule_event':
                templates_to_render = [
                    {'tpl': 'TEMPLATE_RESCHEDULE.docx', 'name': 'Reschedule_Letter.docx'}
                ]
            else:
                # Fallback for single doc requests (backward compatibility)
                tpl = 'TEMPLATE_APPROVAL.docx'
                if doc_type == 'excuse': tpl = 'TEMPLATE_EXCUSE.docx'
                elif doc_type == 'reschedule': tpl = 'TEMPLATE_RESCHEDULE.docx'
                templates_to_render = [{'tpl': tpl, 'name': f'{doc_type.capitalize()}_Letter.docx'}]

            # Context for rendering (shared across all docs in the set)
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
                'targetClasses': data.get('targetClasses', ''),
                'reqEquipment': data.get('reqEquipment', ''),
                'origDate': data.get('origDate', ''),
                'reschedReason': data.get('reschedReason', ''),
            }

            # If only one document, return directly as docx
            if len(templates_to_render) == 1:
                item = templates_to_render[0]
                template_path = os.path.join(settings.BASE_DIR, 'static', 'templates', item['tpl'])
                if not os.path.exists(template_path):
                    return JsonResponse({'status': 'error', 'message': f'Template missing: {item["tpl"]}'})
                
                doc = DocxTemplate(template_path)
                doc.render(context)
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                response['Content-Disposition'] = f'attachment; filename="{item["name"]}"'
                doc.save(response)
                return response
                return response

            # If multiple documents, package in a ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for item in templates_to_render:
                    template_path = os.path.join(settings.BASE_DIR, 'static', 'templates', item['tpl'])
                    if os.path.exists(template_path):
                        doc = DocxTemplate(template_path)
                        doc.render(context)
                        doc_io = io.BytesIO()
                        doc.save(doc_io)
                        doc_io.seek(0)
                        zip_file.writestr(item['name'], doc_io.read())

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.read(), content_type='application/zip')
            org_acr = data.get('sigOrg', 'Request')
            response['Content-Disposition'] = f'attachment; filename="Event_Documents_{org_acr}.zip"'
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

@user_passes_test(is_organizer_strictly, login_url='/')
def reject_individual_student(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        reject_reason = request.POST.get('reject_reason', 'No reason provided.')
        try:
            student = Student.objects.get(id=student_id)
            
            # Send Email before deletion (otherwise we lose the data)
            send_student_email(student, 'reject', {
                'reason': reject_reason,
                'organization': student.organization
            })
            
            # Log Rejection before deletion
            log_audit_event(request, 'REJECTION', status='Success', changes={'student': student.full_name, 'reason': reject_reason})
            
            # Delete associated User (which cascades to delete the Student record)
            user_account = student.user
            if user_account:
                user_account.delete()
            else:
                student.delete() # Fallback if no user is linked for some reason
            
            messages.success(request, f"Successfully rejected {student.full_name} and sent feedback.")
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
    elif email_type == 'reject':
        subject = "Registration Declined - Action Required"
        template_name = "email/rejection_email.html"
    
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

@user_passes_test(is_student_strictly, login_url='/')
def get_student_notifications_api(request):
    try:
        student = Student.objects.get(user=request.user)
        notifications = get_student_notifications(student)
        return JsonResponse({'status': 'success', 'notifications': notifications})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_attendance_events(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    org_events = Event.objects.filter(org_id=org_acronym, event_status='Approved').order_by('-event_date', '-start_time')
    
    event_data = []
    for event in org_events:
        event_data.append({
            'id': event.id,
            'title': event.event_title,
            'date': event.event_date.strftime("%b %d, %Y") if event.event_date else "TBA",
            'respondents': Attendance.objects.filter(event=event).count(),
        })

    return render(request, 'organizer/attendance_events.html', {
        'org_acronym': org_acronym,
        'events_data_json': json.dumps(event_data)
    })

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_manage_attendance(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    event_id = request.GET.get('event_id')
    if not event_id:
        return redirect('organizer_attendance_events')

    try:
        current_event = Event.objects.get(id=event_id, org_id=org_acronym)
    except Event.DoesNotExist:
        return redirect('organizer_attendance_events')

    # Fetch attendance for THIS specific event
    attendance_records = Attendance.objects.filter(event=current_event).select_related('student', 'organizer__user', 'event').order_by('-time_in')
    
    attendance_data = []
    for att in attendance_records:
        status = "Verified" if att.face_matched and att.is_valid_location else "Issue"
        
        if att.student:
            role = 'STUDENT'
            name = att.student.full_name
            number = att.student.student_number
            program = att.student.program
            year = att.student.year_level
            img = att.student.profile_picture.url if att.student.profile_picture else '/static/images/student.jpg'
        else:
            role = 'ORGANIZER'
            # Fallback to username if first/last name not set
            name = f"{att.organizer.user.first_name} {att.organizer.user.last_name}".strip() or att.organizer.user.username
            number = "ORG-MEMBER"
            program = att.organizer.organization
            year = "N/A"
            img = att.organizer.profile_picture.url if att.organizer.profile_picture else '/static/images/org1.jpg'

        attendance_data.append({
            'id': att.id,
            'role': role,
            'name': name,
            'number': number,
            'program': program,
            'year': str(year),
            'time': att.time_in.strftime('%I:%M %p'),
            'date': att.time_in.strftime('%b %d, %Y'),
            'has_timed_out': att.time_out is not None,
            'time_out': att.time_out.strftime('%I:%M %p') if att.time_out else None,
            'status': status,
            'event': att.event.event_title,
            'venue': att.event.venue,
            'lat': float(att.latitude) if att.latitude else 13.8392,
            'lng': float(att.longitude) if att.longitude else 121.9861,
            'img': img,
            'captured_face': att.capture_image.url if att.capture_image else None,
            'is_global': current_event.is_flag_raising
        })

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'attendance_data_json': json.dumps(attendance_data),
        'event': current_event
    }
    return render(request, 'organizer/manage_attendance.html', context)

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_analytics(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"

    # 🟢 NEWEST TO OLDEST ORDERING 🟢
    org_events = Event.objects.filter(org_id=org_acronym, event_status='Approved').order_by('-event_date', '-start_time')
    event_ids = [str(e.id) for e in org_events]
    
    # Fetch evaluations from AuditLog
    eval_logs = AuditLog.objects.filter(action='EVALUATION', target_id__in=event_ids, status='Success')
    
    total_evals = eval_logs.count()
    
    # Calculate average rating and sentiment
    total_rating = 0
    positive_count = 0 # This will now be based on VADER if available
    
    event_analytics_data = []
    for e in org_events:
        e_logs = [log for log in eval_logs if log.target_id == str(e.id)]
        e_count = len(e_logs)
        e_rating = 0
        e_dist = [0, 0, 0, 0, 0]
        
        if e_count > 0:
            e_total_rating = 0
            e_pos = 0
            for log in e_logs:
                try:
                    changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
                    r = float(changes.get('rating', 0))
                    e_total_rating += r
                    idx = int(round(r)) - 1
                    if 0 <= idx <= 4:
                        e_dist[idx] += 1
                    
                    # 🟢 AI-BASED SENTIMENT CHECK 🟢
                    # If AI sentiment exists, use it. Otherwise fallback to rating.
                    if 'sentiment' in changes:
                        if changes['sentiment'].get('label') == 'positive': e_pos += 1
                    else:
                        if r >= 4: e_pos += 1
                except: continue
            
            e_rating = e_total_rating / e_count
            total_rating += e_total_rating
            positive_count += e_pos
            
        event_analytics_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y'),
            'respondents': e_count,
            'score': round(e_rating, 1),
            'sentiment': int((e_pos / e_count * 100)) if e_count > 0 else 0,
            'dist': e_dist
        })

    avg_rating = round(total_rating / total_evals, 1) if total_evals > 0 else 0.0
    pos_sentiment = int((positive_count / total_evals * 100)) if total_evals > 0 else 0

    context = {
        'org_acronym': org_acronym, 
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'total_evals': total_evals,
        'avg_rating': avg_rating,
        'pos_sentiment': pos_sentiment,
        'events_managed': org_events.count(),
        'history_data_json': json.dumps(event_analytics_data)
    }
    return render(request, 'organizer/analytics.html', context)

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
    completed_events_qs = Event.objects.filter(org_id=org_acronym, event_status='Approved').order_by('-created_at')
    
    # Process analytics for completed events
    completed_events = []
    for evt in completed_events_qs:
        logs = AuditLog.objects.filter(action='EVALUATION', target_model='Event', target_id=str(evt.id), status='Success')
        total_rating = 0
        total_compound = 0
        count = 0
        
        for log in logs:
            if log.changes:
                try:
                    rating = float(log.changes.get('rating', 0))
                    compound = float(log.changes.get('sentiment', {}).get('compound', 0))
                    total_rating += rating
                    total_compound += compound
                    count += 1
                except: pass
                
        if count > 0:
            avg_rating = round(total_rating / count, 1)
            # Map compound (-1 to +1) to percentage (0% to 100%)
            sentiment_percent = int(((total_compound / count) + 1) / 2 * 100)
        else:
            avg_rating = 0.0
            sentiment_percent = 0
            
        evt.average_rating = avg_rating
        evt.sentiment_percentage = sentiment_percent
        completed_events.append(evt)
        
    pending_students = Student.objects.filter(organization__iexact=org_acronym, is_verified=False).order_by('-created_at')
    
    email_notifications = org_profile.email_notifications if org_profile else True
    read_notifications_str = org_profile.read_notifications if org_profile else ""
    read_notifications = [r for r in read_notifications_str.split(',') if r]

    context = {
        'org_profile': org_profile,
        'full_name': full_name,
        'student_number': request.user.username,
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'recent_events': recent_events,
        'completed_events': completed_events,
        'pending_students': pending_students,
        'email_notifications': email_notifications,
        'read_notifications_json': json.dumps(read_notifications)
    }
    return render(request, 'organizer/profile.html', context)

@user_passes_test(is_organizer_strictly, login_url='/')
def update_org_notification_preference(request):
    if request.method == 'POST':
        enabled = request.POST.get('email_notifications') == 'true'
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            org_profile.email_notifications = enabled
            org_profile.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@user_passes_test(is_organizer_strictly, login_url='/')
def mark_org_notifications_read(request):
    if request.method == 'POST':
        notif_ids = request.POST.get('notif_ids', '')
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            org_profile.read_notifications = notif_ids
            org_profile.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def get_all_org_notifications(org_acronym):
    notifications = []
    now = timezone.now()
    today = now.date()
    
    # Ensure acronym is clean
    org_clean = org_acronym.strip() if org_acronym else ""

    # 1. New Student Registrations
    try:
        students = Student.objects.filter(organization__iexact=org_clean, is_verified=False).order_by('-id')
        for s in students:
            dt = getattr(s, 'created_at', None) or now
            notifications.append({
                'id': f"stud_{s.id}", 'type': 'student', 'title': 'New Student Registration',
                'message': f"Mabuhay Iskolar! {s.full_name} is waiting for your approval to join the organization portal.",
                'sender': 'System Admin', 'date': dt.strftime('%b %d, %Y'), 'timestamp': dt.timestamp(), 'url': '/organizer/manage-students'
            })
    except Exception: pass

    # 2. Event Status Updates & Remarks
    try:
        events = Event.objects.filter(org_id__iexact=org_clean).order_by('-id')
        for e in events:
            dt = getattr(e, 'created_at', None) or now
            url = '/organizer/school-events'
            
            if e.event_status == 'Approved':
                msg = f"Great news! Your event proposal for '{e.event_title}' has been officially APPROVED by the Administration."
                sender = 'Admin Office'
            elif e.event_status == 'Admin Approved':
                msg = f"Initial Approval granted for '{e.event_title}'! Please upload your signed documents in the Document Vault."
                sender = 'Admin Office'
                url = '/organizer/document-tracking'
            elif e.event_status == 'Rejected':
                msg = f"Notice: Your event proposal for '{e.event_title}' was REJECTED. Please check the remarks for details."
                sender = 'Admin / Adviser'
            elif e.remarks and str(e.remarks).strip().lower() != 'none' and str(e.remarks).strip() != '':
                msg = f"Comment Update: Your proposal '{e.event_title}' has new remarks from the reviewer."
                sender = 'Adviser / Admin'
            else:
                msg = f"Update: Your event proposal for '{e.event_title}' is currently UNDER REVIEW."
                sender = 'System Notification'
                
            notifications.append({
                'id': f"evt_{e.id}", 'type': 'event', 'title': e.event_title, 'status': e.event_status,
                'remarks': str(e.remarks) if e.remarks else '', 'message': msg, 'sender': sender,
                'date': dt.strftime('%b %d, %Y'), 'timestamp': dt.timestamp(), 'url': url
            })
    except Exception: pass

    # 3. Attendance Issues
    try:
        att_issues = Attendance.objects.filter(event__org_id__iexact=org_clean).filter(Q(face_matched=False) | Q(is_valid_location=False)).order_by('-time_in')[:15]
        for att in att_issues:
            issue = "Biometric mismatch" if not att.face_matched else "Outside geofence"
            notifications.append({
                'id': f"att_issue_{att.id}", 'type': 'alert', 'title': 'Attendance Issue Detected',
                'message': f"Alert: {att.student.full_name} has a recorded {issue} for '{att.event.event_title}'.",
                'sender': 'Security System', 'date': att.time_in.strftime('%b %d, %Y'), 'timestamp': att.time_in.timestamp(),
                'url': '/organizer/manage-attendance'
            })
    except Exception: pass

    # 4. Incomplete Logs (Ended events)
    try:
        current_time = now.time()
        ended_events = Event.objects.filter(org_id__iexact=org_clean, event_status='Approved', event_date=today)
        for e in ended_events:
            if e.end_time and e.end_time < current_time:
                incomplete_count = Attendance.objects.filter(event=e, time_out__isnull=True).count()
                if incomplete_count > 0:
                    notifications.append({
                        'id': f"inc_{e.id}", 'type': 'alert', 'title': 'Incomplete Event Logs',
                        'message': f"Notice: {incomplete_count} students haven't timed out for the concluded event '{e.event_title}'.",
                        'sender': 'Attendance Monitor', 'date': e.event_date.strftime('%b %d, %Y'), 'timestamp': now.timestamp(),
                        'url': '/organizer/manage-attendance'
                    })
    except Exception: pass

    # 5. New Evaluations
    try:
        new_evals = AuditLog.objects.filter(action='EVALUATION', status='Success').order_by('-timestamp')[:15]
        for log in new_evals:
            try:
                evt_id = log.target_id
                if not evt_id: continue
                event = Event.objects.get(id=evt_id, org_id__iexact=org_clean)
                notifications.append({
                    'id': f"eval_{log.id}", 'type': 'message', 'title': 'New Event Feedback',
                    'message': f"Mabuhay! A student just submitted an evaluation for '{event.event_title}'.",
                    'sender': 'Evaluation Hub', 'date': log.timestamp.strftime('%b %d, %Y'), 'timestamp': log.timestamp.timestamp(),
                    'url': f"/organizer/feedback?event_id={event.id}"
                })
            except: continue
    except Exception: pass

    # Fallback: Welcome notification if empty
    if not notifications:
        notifications.append({
            'id': 'welcome_system', 'type': 'message', 'title': f'Welcome to Organizer Portal ({org_clean})',
            'message': 'Mabuhay! This is your message history. All your event updates and student alerts will appear here.',
            'sender': 'System', 'date': now.strftime('%b %d, %Y'), 'timestamp': now.timestamp(), 'url': '#'
        })

    # Safe sort
    def get_ts(x):
        try: return float(x.get('timestamp', 0))
        except: return 0
        
    notifications.sort(key=get_ts, reverse=True)
    return notifications

@user_passes_test(is_organizer_strictly, login_url='/')
def get_organizer_notifications_api(request):
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
        notifications = get_all_org_notifications(org_acronym)
        return JsonResponse({'status': 'success', 'notifications': notifications})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_message_history(request):
    org_profile = OrgProfile.objects.get(user=request.user)
    org_acronym = org_profile.organization.strip()
    notifications = get_all_org_notifications(org_acronym)

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

    # Fetch actual attendance records for this organizer
    org_attendances = Attendance.objects.filter(organizer=org_profile).select_related('event').order_by('-time_in')
    
    history_data = []
    for att in org_attendances:
        e = att.event
        
        img_url = '/static/images/PUPLogo.png'
        if e.thumbnail: img_url = e.thumbnail.url
        elif getattr(e, 'event_cover_photo', None): img_url = e.event_cover_photo.url
        elif getattr(e, 'cover_photo', None): img_url = e.cover_photo.url

        history_data.append({
            'id': e.id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y') if e.event_date else 'No Date',
            'time': att.time_in.strftime('%I:%M %p') if att.time_in else '--',
            'venue': e.venue,
            'type': 'Attendance',
            'img': img_url,
            'capture_img': att.capture_image.url if att.capture_image else '/static/images/PUPLogo.png',
            'matched': att.face_matched,
            'location': att.location_zone or "Verified inside PUP Campus Perimeter."
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

    # 🟢 REAL-TIME LOCATION LOGIC 🟢
    from .models import UserLocation
    adviser_loc = UserLocation.objects.filter(user__is_staff=True, user__is_superuser=False).order_by('-last_updated').first()
    if adviser_loc and adviser_loc.latitude and adviser_loc.longitude:
        ADVISER_COORDS = [float(adviser_loc.latitude), float(adviser_loc.longitude)]

    admin_loc = UserLocation.objects.filter(user__is_superuser=True).order_by('-last_updated').first()
    if admin_loc and admin_loc.latitude and admin_loc.longitude:
        ADMIN_COORDS = [float(admin_loc.latitude), float(admin_loc.longitude)]

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
        # Detect mode if not set
        mode = e.requirement_mode
        if not mode:
            mode = 2 if e.description and "[RESCHEDULE]" in e.description else 4

        pending_data.append({
            'id': e.id,
            'eventName': e.event_title,
            'orgName': e.org_id,
            'mode': mode
        })

    vault_events = Event.objects.filter(org_id=org_acronym, event_status__in=['Permit Verification', 'Final Admin Review', 'Approved']).order_by('-id')
    vault_data = []
    for e in vault_events:
        docs = []
        mode = e.requirement_mode if getattr(e, 'requirement_mode', None) else (2 if e.description and "[RESCHEDULE]" in e.description else 4)

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
            'mode': str(mode),
            'docs': docs,
            # Extra data for Preview Letter
            'description': e.description,
            'requester_name': e.requester_name,
            'adviser_name': e.adviser_name,
            'org': e.org_id,
            'event_date': e.event_date.strftime("%B %d, %Y") if e.event_date else "",
            'start_time': e.start_time.strftime("%I:%M %p") if e.start_time else "",
            'venue': e.venue
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


def gcash_anonymize(name):
    if not name: return "Anonymous"
    words = name.strip().split()
    anon_words = []
    for w in words:
        if len(w) <= 2:
            anon_words.append(w[0] + "*" * (len(w)-1))
        else:
            anon_words.append(w[0] + "*" * (len(w)-2) + w[-1])
    return " ".join(anon_words)

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_feedback_detail(request):
    event_id = request.GET.get('event_id')
    if not event_id:
        return redirect('organizer_analytics')
    
    try:
        event = Event.objects.get(id=event_id)
        org_profile = OrgProfile.objects.get(user=request.user)
        # Ensure organizer can only view their own org's feedback
        if event.org_id != org_profile.organization.strip():
            return redirect('organizer_analytics')
            
        # 1. EVALUATION DATA
        eval_logs = AuditLog.objects.filter(action='EVALUATION', target_id=str(event_id), status='Success')
        total_evals = eval_logs.count()
        
        avg_rating = 0
        pos_count = 0
        criteria_scores = [0, 0, 0, 0, 0] # Match labels in template
        year_dist = {'1st Year': 0, '2nd Year': 0, '3rd Year': 0, '4th Year': 0}
        comments = []

        for log in eval_logs:
            try:
                changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
                r = float(changes.get('rating', 0))
                avg_rating += r
                if r >= 4: pos_count += 1
                
                # Criteria logic (details is a list of dicts from frontend)
                details = changes.get('detailed_scores', [])
                if isinstance(details, list) and len(details) >= 5:
                    criteria_scores[0] += float(details[0].get('average', r))
                    criteria_scores[1] += float(details[1].get('average', r))
                    criteria_scores[2] += float(details[2].get('average', r))
                    criteria_scores[3] += float(details[3].get('average', r))
                    criteria_scores[4] += float(details[4].get('average', r))
                else:
                    criteria_scores[0] += r
                    criteria_scores[1] += r
                    criteria_scores[2] += r
                    criteria_scores[3] += r
                    criteria_scores[4] += r
                
                # Qualitative Comments & VADER Sentiment
                if 'sentiment' in changes and isinstance(changes['sentiment'], dict):
                    sentiment = changes['sentiment'].get('label', 'neutral')
                else:
                    feedback_text = changes.get('feedback', '')
                    sentiment = get_sentiment(feedback_text).get('label', 'neutral')
                
                # Get student year level
                student = Student.objects.filter(user=log.actor).first()
                y_level = student.year_level if student else 'Unknown'
                if y_level in year_dist: year_dist[y_level] += 1
                
                full_name = student.full_name if student and student.full_name else log.actor.get_full_name()
                
                comments.append({
                    'name': gcash_anonymize(full_name),
                    'text': changes.get('feedback', 'No feedback provided.'),
                    'sentiment': sentiment,
                    'year': y_level
                })
            except: continue

        if total_evals > 0:
            avg_rating /= total_evals
            criteria_scores = [round(s/total_evals, 1) for s in criteria_scores]
            pos_sentiment = int((pos_count / total_evals) * 100)
        else:
            pos_sentiment = 0

        # 2. ATTENDANCE DATA (For matching)
        att_count = Attendance.objects.filter(event=event).count()

        # Find highest rated area
        labels = ['Organization', 'Objectives', 'Materials', 'Management Team', 'Venue/Logistics']
        max_idx = criteria_scores.index(max(criteria_scores)) if total_evals > 0 else 0
        highest_area = labels[max_idx]

        context = {
            'event': event,
            'total_evals': total_evals,
            'att_count': att_count,
            'avg_rating': round(avg_rating, 1),
            'pos_sentiment': pos_sentiment,
            'highest_area': highest_area,
            'criteria_scores': json.dumps(criteria_scores),
            'year_dist': json.dumps(list(year_dist.values())),
            'comments_json': json.dumps(comments)
        }
        return render(request, 'organizer/feedback.html', context)
    except Exception as e:
        return redirect('organizer_analytics')

# ==========================================
# 🟢 ADMIN VIEWS (AYOS NA YUNG TIME BUGS!) 🟢
# ==========================================
@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def event_approvals_view(request): 
    # PENDING EVENTS (Action Required)
    pending = Event.objects.filter(event_status__in=['Pending Admin', 'Final Admin Review']).order_by('-created_at')
    pending_data = []
    for e in pending:
        full_org_name = ORG_FULL_NAMES.get(e.org_id, e.org_id)
        pending_data.append({
            'id': e.id, 'org': e.org_id, 'full_org': full_org_name, 'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'status': e.event_status.upper() if e.event_status else '',
            'letter_url': e.letter_of_approval.url if getattr(e, 'letter_of_approval', None) else (e.letter_image.url if getattr(e, 'letter_image', None) else ''),
            'permit_url': e.permit_to_conduct.url if getattr(e, 'permit_to_conduct', None) else (e.permit_image.url if getattr(e, 'permit_image', None) else ''),
            'equipment_url': e.excuse_letter_equipment.url if getattr(e, 'excuse_letter_equipment', None) else (e.equipment_image.url if getattr(e, 'equipment_image', None) else ''),
            'event_cover_photo': e.event_cover_photo.url if getattr(e, 'event_cover_photo', None) else (e.cover_photo.url if getattr(e, 'cover_photo', None) else ''),
            'letter_of_reschedule': e.letter_of_reschedule.url if getattr(e, 'letter_of_reschedule', None) else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if getattr(e, 'reschedule_cover_photo', None) else '',
            'requirement_mode': e.requirement_mode
            })
        
    # ALL EVENTS FOR CONFLICT DETECTION (Global Record Log)
    # Admin wants to see everything to check for date/time conflicts
    history = Event.objects.all().order_by('-created_at')
    history_data = []
    for e in history:
        att_count = Attendance.objects.filter(event=e).count()
        eval_count = AuditLog.objects.filter(action='EVALUATION', target_id=str(e.id)).count()
        full_org_name = ORG_FULL_NAMES.get(e.org_id, e.org_id)

        history_data.append({
            'id': e.id, 'org': e.org_id, 'full_org': full_org_name, 'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'attendance_count': att_count,
            'evaluation_count': eval_count,
            'status': e.event_status.upper() if e.event_status else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'letter_url': e.letter_of_approval.url if getattr(e, 'letter_of_approval', None) else (e.letter_image.url if getattr(e, 'letter_image', None) else ''),
            'permit_url': e.permit_to_conduct.url if getattr(e, 'permit_to_conduct', None) else (e.permit_image.url if getattr(e, 'permit_image', None) else ''),
            'equipment_url': e.excuse_letter_equipment.url if getattr(e, 'excuse_letter_equipment', None) else (e.equipment_image.url if getattr(e, 'equipment_image', None) else ''),
            'event_cover_photo': e.event_cover_photo.url if getattr(e, 'event_cover_photo', None) else (e.cover_photo.url if getattr(e, 'cover_photo', None) else ''),
            'letter_of_reschedule': e.letter_of_reschedule.url if getattr(e, 'letter_of_reschedule', None) else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if getattr(e, 'reschedule_cover_photo', None) else '',
            'requirement_mode': e.requirement_mode,
            'remarks': e.remarks or ''
        })
        
    return render(request, 'admin_dashboard/event_approvals.html', {
        'events_json': json.dumps(pending_data),
        'history_json': json.dumps(history_data)
    })

@login_required
def record_attendance(request):
    if request.method == 'POST':
        try:
            student = Student.objects.filter(user=request.user).first()
            organizer = OrgProfile.objects.filter(user=request.user).first()

            if not student and not organizer:
                return JsonResponse({'status': 'error', 'message': 'Account not authorized for attendance.'})

            event_id = request.POST.get('event_id')
            live_face_b64 = request.POST.get('face_image') # Receives live capture from frontend
            is_valid_location = request.POST.get('is_valid_location') == 'true'
            lat = request.POST.get('latitude')
            lng = request.POST.get('longitude')
            
            event = Event.objects.filter(id=event_id, event_status='Approved').first()
            if not event:
                return JsonResponse({'status': 'error', 'message': 'Event not found or not yet approved.'})

            # 🟢 GLOBAL ATTENDANCE FOR FLAG RAISING 🟢
            if getattr(event, 'is_flag_raising', False):
                is_valid_location = True

            # Check for existing attendance
            # 🟢 HUMAN-READABLE LOCATION (Reverse Geocoding Logic) 🟢
            location_name = "Unknown Location"
            if lat and lng:
                lat_f, lng_f = float(lat), float(lng)
                zones = [
                    {'name': 'Main Building', 'lat': 13.84615, 'lng': 121.96955},
                    {'name': 'Gymnasium', 'lat': 13.84580, 'lng': 121.96980},
                    {'name': 'Covered Court', 'lat': 13.84640, 'lng': 121.96940},
                    {'name': 'Campus Grounds', 'lat': 13.84610, 'lng': 121.96970}
                ]
                closest_zone = zones[0]
                min_dist = float('inf')
                for zone in zones:
                    dist = ((lat_f - zone['lat'])**2 + (lng_f - zone['lng'])**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_zone = zone
                if min_dist < 0.001: location_name = closest_zone['name']
                else: location_name = f"Outside Campus ({lat_f:.4f}, {lng_f:.4f})"

            attendance = None
            if student:
                attendance = Attendance.objects.filter(student=student, event=event).first()
            elif organizer:
                attendance = Attendance.objects.filter(organizer=organizer, event=event).first()

            now = timezone.now()
            start_dt = timezone.make_aware(datetime.combine(event.event_date, event.start_time))
            end_dt = None
            if event.end_time:
                end_dt = timezone.make_aware(datetime.combine(event.event_date, event.end_time))

            # 🟢 TIME OUT LOGIC 🟢
            if attendance:
                if attendance.time_out:
                    return JsonResponse({'status': 'error', 'message': 'Attendance (Time Out) already recorded for this event.'})
                
                # Validation for Time Out (Starting from 15 minutes before end_time)
                if end_dt:
                    timeout_start = end_dt - timedelta(minutes=15)
                    timeout_expiry = end_dt + timedelta(hours=3) # Allow time out up to 3 hours after end_time
                    
                    if now < timeout_start:
                        return JsonResponse({'status': 'error', 'message': f'Time Out window hasn\'t opened yet. Available at {timeout_start.strftime("%I:%M %p")}.'})
                    if now > timeout_expiry:
                        return JsonResponse({'status': 'error', 'message': 'Time Out window has closed for this event.'})
                else:
                    # Fallback if no end_time
                    timeout_start = start_dt + timedelta(hours=2)
                    if now < timeout_start:
                        return JsonResponse({'status': 'error', 'message': 'Time Out not yet available.'})

                # Update for Time Out
                attendance.time_out = now
                attendance.latitude_out = lat
                attendance.longitude_out = lng
                attendance.is_valid_location_out = is_valid_location
                attendance.location_zone = location_name # Save zone on timeout
                attendance.save()

                log_audit_event(request, 'ATTENDANCE', target_model='Event', target_id=str(event.id), status='Success', changes={
                    'type': 'Time Out',
                    'event': event.event_title,
                    'user': student.full_name if student else organizer.user.username,
                    'location_zone': location_name,
                    'location_valid': is_valid_location
                })

                return JsonResponse({'status': 'success', 'message': f'Mission Complete: Time Out verified at {location_name}. Participation synchronized.'})

            # 🟢 TIME IN LOGIC 🟢
            if end_dt:
                expiry_dt = end_dt + timedelta(hours=1)
            else:
                expiry_dt = start_dt + timedelta(hours=4)

            if now < start_dt:
                return JsonResponse({'status': 'error', 'message': f'Authorization window hasn\'t opened yet. Access available at {event.start_time.strftime("%I:%M %p")}.'})
            if now > expiry_dt:
                return JsonResponse({'status': 'error', 'message': 'Authorization window has expired for this activity.'})

            # 🟢 SERVER-SIDE DEEPFACE VERIFICATION 🟢
            face_matched = False
            anchor_b64 = student.face_encoding if student else (organizer.face_encoding if organizer else None)
            
            if live_face_b64 and anchor_b64:
                face_matched, distance = verify_face(live_face_b64, anchor_b64)
            else:
                face_matched = request.POST.get('face_matched') == 'true'

            attendance = Attendance.objects.create(
                student=student,
                organizer=organizer,
                event=event,
                face_matched=face_matched,
                is_valid_location=is_valid_location,
                latitude=lat,
                longitude=lng,
                location_zone=location_name # Save zone on timein
            )

            # 🟢 SAVE CAPTURE IMAGE 🟢
            if live_face_b64:
                try:
                    format, imgstr = live_face_b64.split(';base64,')
                    ext = format.split('/')[-1]
                    data = ContentFile(base64.b64decode(imgstr), name=f'capture_{attendance.id}.{ext}')
                    attendance.capture_image = data
                    attendance.save()
                except Exception as e:
                    print(f"Error saving capture image: {e}")
            
            log_audit_event(request, 'ATTENDANCE', target_model='Event', target_id=str(event.id), status='Success' if face_matched else 'Issue', changes={
                'type': 'Time In',
                'event': event.event_title,
                'user': student.full_name if student else organizer.user.username,
                'location_zone': location_name,
                'face_match': face_matched,
                'location_valid': is_valid_location,
            })
            
            msg = f"Time In verified at {location_name}."
            if not face_matched:
                msg += " Note: Biometric mismatch detected; record flagged for review."

            return JsonResponse({'status': 'success' if face_matched else 'issue', 'message': msg})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return redirect('index')

@user_passes_test(is_organizer_strictly, login_url='/')
def register_organizer_face(request):
    if request.method == 'POST':
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            
            face_data = request.POST.get('face_encoding')
            if not face_data:
                return JsonResponse({'status': 'error', 'message': 'No facial data received.'})
            
            org_profile.face_encoding = face_data
            org_profile.save()
            
            log_audit_event(request, 'UPDATE', target_model='OrgProfile', target_id=str(org_profile.id), status='Success', changes={'face_encoding': 'Updated'})
            return JsonResponse({'status': 'success', 'message': 'Face identity updated successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@user_passes_test(is_student_strictly, login_url='/')
def submit_evaluation(request):
    if request.method == 'POST':
        try:
            student = Student.objects.get(user=request.user)
            event_id = request.POST.get('event_id')
            event_title = request.POST.get('event_title')
            feedback = request.POST.get('feedback') or request.POST.get('comments') or 'No feedback provided.'
            rating = request.POST.get('rating')
            detailed_scores = request.POST.get('detailed_scores')
            total_raw_score = request.POST.get('total_raw_score')

            event = Event.objects.filter(id=event_id, event_status='Approved').first()
            if not event:
                return JsonResponse({'status': 'error', 'message': 'Event not found.'})

            # 🟢 ENFORCE TIME OUT BEFORE EVALUATION 🟢
            attendance = Attendance.objects.filter(student=student, event=event).first()
            if not attendance or not attendance.time_out:
                return JsonResponse({'status': 'error', 'message': 'You must Time Out from the event before submitting an evaluation.'})

            # 🟢 ENFORCE EVALUATION WINDOW (End Time - 1 Hour to 24 Hours after)
            now = timezone.now()
            if event.end_time:
                end_dt = timezone.make_aware(datetime.combine(event.event_date, event.end_time))
                open_dt = end_dt - timedelta(hours=1)
                expiry_dt = end_dt + timedelta(hours=1) # The user said 1 hour grace for attendance, likely same for eval
            else:
                # Fallback if no end time (4 hours after start)
                start_dt = timezone.make_aware(datetime.combine(event.event_date, event.start_time))
                open_dt = start_dt + timedelta(hours=2)
                expiry_dt = start_dt + timedelta(hours=5)

            if now < open_dt:
                return JsonResponse({'status': 'error', 'message': 'Evaluation portal is not yet open.'})
            if now > expiry_dt:
                return JsonResponse({'status': 'error', 'message': 'Evaluation window has closed.'})

            # 🟢 PREVENT DUPLICATE EVALUATION
            already_evaluated = AuditLog.objects.filter(
                actor=request.user, 
                action='EVALUATION', 
                target_id=str(event_id),
                status='Success'
            ).exists()
            
            if already_evaluated:
                return JsonResponse({'status': 'error', 'message': 'Evaluation already submitted for this event.'})

            if not rating:
                return JsonResponse({'status': 'error', 'message': 'Please provide a rating.'})

            # 🟢 VADER SENTIMENT ANALYSIS 🟢
            feedback_sentiment = get_sentiment(feedback)
            
            # Map detailed scores to synthetic sentiment
            synthetic_scores = {}
            if detailed_scores:
                try:
                    scores_dict = json.loads(detailed_scores)
                    for key, val in scores_dict.items():
                        synthetic_scores[key] = get_rating_sentiment(val)
                except: pass

            changes = {
                'event': event_title, 
                'rating': rating,
                'feedback': feedback,
                'sentiment': feedback_sentiment, # Store full VADER result
                'detailed_sentiments': synthetic_scores,
                'ai_analyzed': True
            }
            if detailed_scores:
                try:
                    changes['detailed_scores'] = json.loads(detailed_scores)
                except: pass
            if total_raw_score:
                changes['total_raw_score'] = total_raw_score

            log_audit_event(request, 'EVALUATION', target_model='Event', target_id=str(event_id), status='Success', changes=changes)
            return JsonResponse({'status': 'success', 'message': 'Evaluation submitted successfully!'})
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
                    
                    event.save() # Save before potentially swapping

                    # 🟢 MAGIC SWAP LOGIC FOR RESCHEDULING 🟢
                    # Check if this is a reschedule by parsing the description for 'OrigID:'
                    desc = event.description or ""
                    is_reschedule = "[RESCHEDULE]" in desc and "OrigID:" in desc
                    final_event_to_announce = event

                    if is_reschedule:
                        try:
                            # Extract Original ID (e.g., ... | OrigID: 123 | ...)
                            orig_id_str = desc.split("OrigID:")[1].split("|")[0].strip()
                            orig_event = Event.objects.get(id=int(orig_id_str))
                            
                            # 1. Update the Original Event with new info
                            orig_event.event_date = event.event_date
                            orig_event.start_time = event.start_time
                            orig_event.end_time = event.end_time
                            orig_event.venue = event.venue
                            
                            # Update metadata if needed (copy cover photo if new one was uploaded)
                            if event.reschedule_cover_photo:
                                orig_event.event_cover_photo = event.reschedule_cover_photo
                            
                            orig_event.save()
                            
                            # 2. Redirect announcements to the original event
                            final_event_to_announce = orig_event
                            
                            # 3. DELETE the reschedule proposal record to avoid duplicates
                            # (Wait until after email sending to be safe with references)
                            reschedule_proposal_id = event.id
                            
                            message = f"Reschedule approved! '{orig_event.event_title}' has been updated to {orig_event.event_date.strftime('%B %d')}."
                        except Exception as swap_err:
                            print(f"Swap Error: {swap_err}")
                            # Fallback: Just approve the new one if swap fails

                    # 🟢 SEND EVENT ALERT TO ALL STUDENTS OF THE ORG
                    students = Student.objects.filter(organization__iexact=final_event_to_announce.org_id, is_verified=True, email_notifications=True)
                    for s in students:
                        send_student_email(s, 'event_alert', {
                            'event_title': final_event_to_announce.event_title,
                            'org_name': ORG_FULL_NAMES.get(final_event_to_announce.org_id, final_event_to_announce.org_id),
                            'event_date': final_event_to_announce.event_date.strftime('%B %d, %Y'),
                            'start_time': final_event_to_announce.start_time.strftime('%I:%M %p'),
                            'venue': final_event_to_announce.venue
                        })

                    # Cleanup if swap happened
                    if is_reschedule and 'reschedule_proposal_id' in locals():
                         Event.objects.filter(id=reschedule_proposal_id).delete()

                    if not is_reschedule:
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

def get_all_admin_notifications():
    notifications = []
    now = timezone.now()
    
    # 1. Password Reset Requests
    try:
        reset_logs = AuditLog.objects.filter(action='PASSWORD_RESET_REQUEST').order_by('-timestamp')[:20]
        for log in reset_logs:
            # We want to link to manage accounts page
            url = '/admin/manage-organizers/'
            changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes) if log.changes else {}
            msg = changes.get('message', 'An organizer requested a password reset.')
            
            notifications.append({
                'id': f"reset_{log.id}", 'type': 'alert', 'title': 'Password Reset Request',
                'message': msg,
                'sender': 'System', 'date': log.timestamp.strftime('%b %d, %Y'), 'timestamp': log.timestamp.timestamp(),
                'url': url
            })
    except Exception: pass

    # 2. Events pending Admin actions
    try:
        pending_events = Event.objects.filter(event_status__in=['Pending Admin', 'Final Admin Review']).order_by('-id')
        for e in pending_events:
            dt = getattr(e, 'created_at', None) or now
            
            if e.event_status == 'Pending Admin':
                msg = f"Event '{e.event_title}' by {e.org_id} is awaiting Initial Admin Clearance."
            else:
                msg = f"Event '{e.event_title}' by {e.org_id} is awaiting Final Admin Review."
                
            notifications.append({
                'id': f"event_{e.id}_{e.event_status.replace(' ', '')}", 'type': 'event', 'title': 'Pending Event Approval',
                'message': msg,
                'sender': 'Event Portal', 'date': dt.strftime('%b %d, %Y'), 'timestamp': dt.timestamp(), 
                'url': '/admin/event-approvals/'
            })
    except Exception: pass

    notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    return notifications

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def get_admin_notifications_api(request):
    try:
        notifications = get_all_admin_notifications()
        return JsonResponse({'status': 'success', 'notifications': notifications})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def admin_notifications_view(request):
    notifications = get_all_admin_notifications()
    context = {
        'notifications_json': json.dumps(notifications)
    }
    return render(request, 'admin_dashboard/notifications.html', context)

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
        
    return render(request, 'admin_dashboard/manage_accounts.html', {'students_json': json.dumps(student_data)})


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
    return render(request, 'admin_dashboard/student_org.html', {'organizers_json': json.dumps(org_data)})


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
    return render(request, 'admin_dashboard/account_history.html', {'history_json': json.dumps(history_data)})

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
                if data.get('password'): 
                    user.set_password(data.get('password'))
                    # Store plain-text password temporarily for the "Forgot Password" auto-fill feature (expires in 5 mins)
                    cache.set(f'reset_pwd_{user.username}', data.get('password'), timeout=300)
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
    # Fetch all approved events
    org_events = Event.objects.filter(event_status='Approved').order_by('-event_date', '-start_time')
    event_ids = [str(e.id) for e in org_events]
    
    # Fetch evaluations from AuditLog
    eval_logs = AuditLog.objects.filter(action='EVALUATION', target_id__in=event_ids, status='Success')
    
    history_data = []
    for e in org_events:
        e_logs = [log for log in eval_logs if log.target_id == str(e.id)]
        e_count = len(e_logs)
        e_rating = 0
        e_pos = 0
        e_dist = [0, 0, 0, 0, 0]
        
        if e_count > 0:
            e_total_rating = 0
            for log in e_logs:
                try:
                    changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
                    r = float(changes.get('rating', 0))
                    e_total_rating += r
                    idx = int(round(r)) - 1
                    if 0 <= idx <= 4:
                        e_dist[idx] += 1
                    
                    if 'sentiment' in changes:
                        if changes['sentiment'].get('label') == 'positive': e_pos += 1
                    else:
                        if r >= 4: e_pos += 1
                except: continue
            
            e_rating = e_total_rating / e_count
            
        history_data.append({
            'id': e.id,
            'org': e.org_id,
            'title': e.event_title,
            'date': e.event_date.strftime('%b %d, %Y') if e.event_date else '',
            'respondents': e_count,
            'score': round(e_rating, 1),
            'sentiment': int((e_pos / e_count * 100)) if e_count > 0 else 0,
            'dist': e_dist
        })

    context = {
        'history_data_json': json.dumps(history_data),
    }
    return render(request, 'admin_dashboard/org_monitor.html', context)

@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def admin_feedback_detail(request):
    event_id = request.GET.get('event_id')
    if not event_id: return redirect('org_monitor')

    try:
        event = Event.objects.get(id=event_id)
        
        # 1. EVALUATION LOGS & SENTIMENT
        eval_logs = AuditLog.objects.filter(action='EVALUATION', target_id=str(event.id), status='Success')
        total_evals = eval_logs.count()
        
        avg_rating = 0
        pos_count = 0
        criteria_scores = [0, 0, 0, 0, 0] # Match labels in template
        year_dist = {'1st Year': 0, '2nd Year': 0, '3rd Year': 0, '4th Year': 0}
        comments = []

        for log in eval_logs:
            try:
                changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
                r = float(changes.get('rating', 0))
                avg_rating += r
                if r >= 4: pos_count += 1
                
                # Criteria logic (details is a list of dicts from frontend)
                details = changes.get('detailed_scores', [])
                if isinstance(details, list) and len(details) >= 5:
                    criteria_scores[0] += float(details[0].get('average', r))
                    criteria_scores[1] += float(details[1].get('average', r))
                    criteria_scores[2] += float(details[2].get('average', r))
                    criteria_scores[3] += float(details[3].get('average', r))
                    criteria_scores[4] += float(details[4].get('average', r))
                else:
                    criteria_scores[0] += r
                    criteria_scores[1] += r
                    criteria_scores[2] += r
                    criteria_scores[3] += r
                    criteria_scores[4] += r
                
                # Qualitative Comments & VADER Sentiment
                if 'sentiment' in changes and isinstance(changes['sentiment'], dict):
                    sentiment = changes['sentiment'].get('label', 'neutral')
                else:
                    feedback_text = changes.get('feedback', '')
                    sentiment = get_sentiment(feedback_text).get('label', 'neutral')
                
                # Get student year level
                student = Student.objects.filter(user=log.actor).first()
                y_level = student.year_level if student else 'Unknown'
                if y_level in year_dist: year_dist[y_level] += 1
                
                full_name = student.full_name if student and student.full_name else log.actor.get_full_name()
                
                def gcash_anonymize(name):
                    if not name: return "Anonymous"
                    parts = name.split()
                    res = []
                    for p in parts:
                        if len(p) <= 2: res.append(p)
                        else: res.append(p[0] + "*" * (len(p)-2) + p[-1])
                    return " ".join(res)

                comments.append({
                    'name': gcash_anonymize(full_name),
                    'text': changes.get('feedback', 'No feedback provided.'),
                    'sentiment': sentiment,
                    'year': y_level
                })
            except: continue

        if total_evals > 0:
            avg_rating /= total_evals
            criteria_scores = [round(s/total_evals, 1) for s in criteria_scores]
            pos_sentiment = int((pos_count / total_evals) * 100)
        else:
            pos_sentiment = 0

        # 2. ATTENDANCE DATA (For matching)
        att_count = Attendance.objects.filter(event=event).count()

        # Find highest rated area
        labels = ['Organization', 'Objectives', 'Materials', 'Management Team', 'Venue/Logistics']
        max_idx = criteria_scores.index(max(criteria_scores)) if total_evals > 0 else 0
        highest_area = labels[max_idx]

        context = {
            'event': event,
            'total_evals': total_evals,
            'att_count': att_count,
            'avg_rating': round(avg_rating, 1),
            'pos_sentiment': pos_sentiment,
            'highest_area': highest_area,
            'criteria_scores': json.dumps(criteria_scores),
            'year_dist': json.dumps(list(year_dist.values())),
            'comments_json': json.dumps(comments)
        }
        return render(request, 'admin_dashboard/feedback.html', context)
    except Exception as e:
        return redirect('org_monitor')

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
        events_qs = Event.objects.filter(org_id__iexact=assigned_org)
    else:
        events_qs = Event.objects.all()

    # Current month stats
    now = timezone.now()
    monthly_approved = events_qs.filter(
        event_status='Approved',
        event_date__month=now.month,
        event_date__year=now.year
    ).count()

    # Pending Admin stats (Forwarded from Adviser)
    pending_admin = events_qs.filter(
        event_status__in=['Pending Admin', 'Final Admin Review']
    ).count()

    # Actionable events for dashboard
    dashboard_events = events_qs.filter(
        event_status__in=['Pending Adviser', 'Permit Verification']
    ).order_by('-created_at')

    events_data = []
    for e in dashboard_events:
        events_data.append({
            'id': e.id, 'org': e.org_id, 
            'full_org': ORG_FULL_NAMES.get(e.org_id, e.org_id),
            'title': e.event_title or '',
            'date': e.event_date.strftime('%B %d, %Y') if e.event_date else '',
            'time': e.start_time.strftime('%I:%M %p') if e.start_time else '',
            'end_time': e.end_time.strftime('%I:%M %p') if getattr(e, 'end_time', None) else '',
            'requester_name': getattr(e, 'requester_name', '') or '',
            'adviser_name': getattr(e, 'adviser_name', '') or '',
            'venue': e.venue or '', 'description': e.description or '',
            'equipment': getattr(e, 'equipment_needed', '') or '', 'status': e.event_status.upper() if e.event_status else '',
            'letter_url': e.letter_image.url if e.letter_image else '',
            'permit_url': e.permit_image.url if e.permit_image else '',
            'equipment_url': e.equipment_image.url if e.equipment_image else '',
            'event_cover_photo': e.event_cover_photo.url if e.event_cover_photo else '',
            'letter_of_reschedule': e.letter_image.url if e.letter_image and e.requirement_mode == 2 else '',
            'reschedule_cover_photo': e.reschedule_cover_photo.url if e.reschedule_cover_photo else (e.event_cover_photo.url if e.event_cover_photo and e.requirement_mode == 2 else ''),
            'requirement_mode': e.requirement_mode
        })
    
    context = {
        'events_json': json.dumps(events_data),
        'monthly_approved_count': monthly_approved,
        'pending_admin_count': pending_admin,
        'assigned_org': assigned_org or "All Organizations"
    }
    return render(request, 'organization adviser/dashboard.html', context)

@user_passes_test(is_adviser_strictly, login_url='/admin/login/')
def adviser_history(request):
    assigned_org = None
    user_str = f"{request.user.username} {request.user.first_name} {request.user.last_name}".lower()
    for org in ORG_FULL_NAMES.keys():
        if org.lower() in user_str:
            assigned_org = org
            break
            
    # History includes everything EXCEPT the very initial review stages (unless already acted upon)
    # Actually, the user wants to see what they've approved. 
    # Events move to 'Pending Admin' after Adviser approval.
    if assigned_org:
        events = Event.objects.filter(org_id__iexact=assigned_org).exclude(event_status='Pending Adviser').order_by('-created_at')
    else:
        events = Event.objects.exclude(event_status='Pending Adviser').order_by('-created_at')

    events_data = []
    for e in events:
        full_org_name = ORG_FULL_NAMES.get(e.org_id, e.org_id)
        events_data.append({
            'id': e.id, 'org': e.org_id, 'full_org': full_org_name, 'title': e.event_title or '',
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
            action = data.get('action')
            
            if action == 'approve':
                old_status = event.event_status
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
                
                # 🟢 LOG AUDIT
                log_audit_event(request, 'ADVISER_APPROVE', target_model='Event', target_id=str(event.id), status='Success', 
                                changes={'from': old_status, 'to': event.event_status, 'title': event.event_title})
                
                return JsonResponse({"status": "success", "message": message})
            
            elif action == 'reject':
                old_status = event.event_status
                event.event_status = 'Rejected'
                event.remarks = data.get('remarks')
                event.save()
                
                # 🟢 LOG AUDIT
                log_audit_event(request, 'ADVISER_REJECT', target_model='Event', target_id=str(event.id), status='Success', 
                                changes={'from': old_status, 'reason': event.remarks, 'title': event.event_title})
                
                return JsonResponse({"status": "success", "message": "Event Rejected."})
                
        except Exception as e: return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})

@user_passes_test(is_adviser_strictly, login_url='/admin/login/')
def get_adviser_notifications_api(request):
    """
    Real-time API for Adviser notifications.
    Tracks event proposals and document verifications.
    """
    try:
        assigned_org = None
        # Improved org matching: checks username, first_name, last_name
        user_str = f"{request.user.username} {request.user.first_name} {request.user.last_name}".lower()
        for org in ORG_FULL_NAMES.keys():
            if org.lower() in user_str:
                assigned_org = org
                break
        
        if assigned_org:
            events = Event.objects.filter(org_id__iexact=assigned_org).order_by('-created_at')
        else:
            # If no specific org, fetch all relevant for staff
            events = Event.objects.all().order_by('-created_at')

        notifications = []
        for e in events:
            # 1. New Proposal Notification (Pending Initial Review)
            if e.event_status == 'Pending Adviser':
                notifications.append({
                    'id': f"prop_{e.id}",
                    'type': 'proposal',
                    'title': 'New Event Proposal',
                    'message': f"Initial Review Needed: '{e.event_title}' from {e.org_id} is waiting for your approval.",
                    'sender': e.org_id,
                    'date': e.created_at.strftime('%b %d, %Y'),
                    'timestamp': e.created_at.timestamp(),
                    'url': f"/adviser/dashboard/?id={e.id}"
                })
            
            # 2. Permit Verification Notification (Signed Documents)
            elif e.event_status == 'Permit Verification':
                notifications.append({
                    'id': f"verify_{e.id}",
                    'type': 'verification',
                    'title': 'Signature Verification',
                    'message': f"Verify Signatures: Signed permits for '{e.event_title}' have been uploaded by {e.org_id}.",
                    'sender': e.org_id,
                    'date': e.created_at.strftime('%b %d, %Y'),
                    'timestamp': e.created_at.timestamp(),
                    'url': f"/adviser/dashboard/?id={e.id}"
                })
            
            # 3. Rejected by Admin (Adviser should know)
            elif e.event_status == 'Rejected' and e.remarks:
                notifications.append({
                    'id': f"rej_{e.id}",
                    'type': 'rejection',
                    'title': 'Proposal Rejected',
                    'message': f"Notice: '{e.event_title}' was rejected by Admin. Reason: {e.remarks[:50]}...",
                    'sender': 'Admin Office',
                    'date': e.created_at.strftime('%b %d, %Y'),
                    'timestamp': e.created_at.timestamp(),
                    'url': f"/adviser/history/?id={e.id}"
                })
            
            # 4. Final Approval
            elif e.event_status == 'Approved':
                notifications.append({
                    'id': f"appr_{e.id}",
                    'type': 'approval',
                    'title': 'Event Fully Published',
                    'message': f"Success: '{e.event_title}' is now live and published to the student portal.",
                    'sender': 'Admin Office',
                    'date': e.created_at.strftime('%b %d, %Y'),
                    'timestamp': e.created_at.timestamp(),
                    'url': f"/adviser/history/?id={e.id}"
                })

        # Sort by latest and limit
        notifications.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return JsonResponse({'status': 'success', 'notifications': notifications[:20]})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

# ==========================================
# 🟢 ADMIN DASHBOARD (REAL DATA AGGREGATION) 🟢
# ==========================================
@user_passes_test(is_admin_strictly, login_url='/admin/login/')
def admin_dashboard(request):
    """
    Main entry point for the Admin Panel.
    Aggregates real-time statistics and historical data for analytics.
    """
    # 1. Stats Grid Data
    total_events = Event.objects.count()
    pending_approval = Event.objects.filter(event_status__in=['Pending Admin', 'Final Admin Review']).count()
    active_orgs = OrgProfile.objects.count()
    engaged_students = Student.objects.filter(is_verified=True).count()
    total_attendances = Attendance.objects.count()

    # 2. Recent Event Requests (Top 5)
    recent_events = Event.objects.order_by('-created_at')[:5]
    
    # 3. Chart Data: Ratings Overview (Aggregated from AuditLog)
    ratings_data = [0, 0, 0, 0, 0] # [1 Star, 2 Star, 3 Star, 4 Star, 5 Star]
    eval_logs = AuditLog.objects.filter(action='EVALUATION', status='Success')
    
    pos_count = 0
    neu_count = 0
    neg_count = 0

    for log in eval_logs:
        try:
            # log.changes might be a dict or a JSON string depending on how it was saved
            changes = log.changes if isinstance(log.changes, dict) else json.loads(log.changes)
            rating = float(changes.get('rating', 0))
            idx = int(round(rating)) - 1
            if 0 <= idx <= 4:
                ratings_data[idx] += 1
            
            # 🟢 AI-BASED SENTIMENT CHECK FOR ADMIN 🟢
            if 'sentiment' in changes:
                lbl = changes['sentiment'].get('label')
                if lbl == 'positive': pos_count += 1
                elif lbl == 'negative': neg_count += 1
                else: neu_count += 1
            else:
                # Fallback to rating
                if rating >= 4: pos_count += 1
                elif rating <= 2: neg_count += 1
                else: neu_count += 1
        except: continue

    # 4. Chart Data: Sentiment
    sentiment_data = [pos_count, neu_count, neg_count]

    # 5. Chart Data: Event Frequency (Last 6 Months)
    event_freq_labels = []
    event_freq_values = []
    today = timezone.now().date()
    
    for i in range(5, -1, -1):
        first_day = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_label = first_day.strftime('%b')
        month_count = Event.objects.filter(event_date__month=first_day.month, event_date__year=first_day.year).count()
        
        event_freq_labels.append(month_label)
        event_freq_values.append(month_count)

    context = {
        'total_events': total_events,
        'pending_approval': pending_approval,
        'active_orgs': active_orgs,
        'engaged_students': engaged_students,
        'total_attendances': total_attendances,
        'recent_events': recent_events,
        'ratings_data': json.dumps(list(reversed(ratings_data))), # Reverse for 5 to 1 order in chart
        'sentiment_data': json.dumps(sentiment_data),
        'event_freq_labels': json.dumps(event_freq_labels),
        'event_freq_values': json.dumps(event_freq_values),
    }
    return render(request, 'admin_dashboard/index.html', context)

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
        
        # 🟢 Determine Actor Name with Fallback
        changes = log.changes if isinstance(log.changes, dict) else (json.loads(log.changes) if log.changes else {})
        actor_name = log.actor.username if log.actor else (changes.get('username', 'Anonymous') if changes.get('reason') != 'Account does not exist' else 'Anonymous')

        logs_data.append({
            'id': log.id,
            'actor': actor_name,
            'action': log.action,
            'target': log.target_model or 'System',
            'status': log.status,
            'ip': log.ip_address,
            'ua': log.user_agent,
            # 🟢 12-hour format with AM/PM for accuracy and readability
            'timestamp': local_time.strftime('%Y-%m-%d %I:%M:%S %p'),
            'changes': changes
        })
        
    return render(request, 'admin_dashboard/audit_logs.html', {
        'logs_json': json.dumps(logs_data)
    })

def staff_login_view(request):
    if request.method == 'POST':
        is_locked, remaining = check_lockout(request, type='staff')
        if is_locked:
            return JsonResponse({"status": "lockout", "message": "Too many attempts.", "remaining": remaining})

        u = request.POST.get('username')
        p = request.POST.get('password')
        
        # Check if user exists BEFORE applying lockout logic
        if not User.objects.filter(username=u).exists():
            log_audit_event(request, 'LOGIN_FAILED', status='Failed', changes={'reason': 'Account does not exist', 'username': u})
            return JsonResponse({"status": "error", "message": "Account does not exist."})

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
            
            # Since we checked existence above, we can attribute this to the user
            existing_user = User.objects.filter(username=u).first()
            log_audit_event(request, 'LOGIN_FAILED', status='Failed', changes={'username': u, 'attempt_count': total_attempts}, actor=existing_user)
            
            if is_locked_now:
                request.session['lockout_until_staff'] = (timezone.now() + timedelta(seconds=lock_time)).isoformat()
                return JsonResponse({
                    "status": "lockout", 
                    "message": f"Too many failed attempts ({total_attempts}). Please wait.", 
                    "remaining": lock_time
                })
                
            return JsonResponse({"status": "error", "message": f"Invalid credentials. Attempt {total_attempts % 5} of 5."})
            
    is_locked, remaining = check_lockout(request, type='staff')
    return render(request, 'admin_dashboard/login.html', {'is_locked': is_locked, 'remaining': remaining})

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


from .models import UserLocation

def update_user_location(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lng = data.get('longitude')
            
            if lat is not None and lng is not None:
                # Update or create location
                location, created = UserLocation.objects.get_or_create(user=request.user)
                location.latitude = lat
                location.longitude = lng
                location.save()
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})



