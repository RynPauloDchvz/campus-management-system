from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User 
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail 
from django.conf import settings 
from django.core.serializers import serialize 
from django.template.loader import render_to_string 
from django.utils.html import strip_tags           
from django.utils import timezone
from datetime import timedelta, datetime
import json 
import string 
import random 
import os 
from docxtpl import DocxTemplate 
from .models import OrgProfile, Student, Attendance, Event, LoginLockout

# ==========================================
# 🟢 4 STRICT RBAC GUARDS (PAM-BLOCK SA MALING URL ACCESS) 🟢
# ==========================================
def is_admin_strictly(user):
    return user.is_authenticated and user.is_superuser

def is_adviser_strictly(user):
    return user.is_authenticated and user.is_staff and not user.is_superuser

def is_organizer_strictly(user):
    return user.is_authenticated and OrgProfile.objects.filter(user=user).exists()

def is_student_strictly(user):
    return user.is_authenticated and Student.objects.filter(user=user).exists()

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
                return JsonResponse({"status": "error", "message": "Admin/Adviser accounts must login through the Staff Portal (/admin/login/)."})

            # Success - reset attempts
            request.session['failed_attempts_portal'] = 0
            if 'lockout_until_portal' in request.session: del request.session['lockout_until_portal']
            reset_account_lockout(student_number)
            
            if OrgProfile.objects.filter(user=user).exists():
                login(request, user)
                return JsonResponse({"status": "success", "redirect_url": "/organizer/homepage"})
            elif Student.objects.filter(user=user).exists():
                student = Student.objects.get(user=user)
                if not student.is_verified:
                    return JsonResponse({"status": "error", "message": "Account is still pending approval. Please wait for your Organizer."})
                else:
                    login(request, user)
                    return JsonResponse({"status": "success", "redirect_url": "/student/dashboard"})
            else:
                return JsonResponse({"status": "error", "message": "Account is neither a registered Student nor an Organizer."})
        else:
            # Failed attempt logic
            is_locked_now, lock_time, total_attempts = record_failed_attempt(student_number)
            
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
    return render(request, 'student/profile.html', {'student': student})

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
def student_homepage(request): return render(request, 'student/homepage.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_school_events(request): return render(request, 'student/school_events.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_event_calendar(request): return render(request, 'student/event_calendar.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_evaluation(request): return render(request, 'student/evaluation.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_evaluation_form(request): return render(request, 'student/evaluation_form.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_event_history(request): return render(request, 'student/event_history.html')
@user_passes_test(is_student_strictly, login_url='/')
def student_messages(request): return render(request, 'student/messages.html')


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
    return render(request, 'organizer/homepage.html', {'org_acronym': org_acronym, 'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym)})

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
            
            send_mail(
                f"Account Approved - {student.organization} Student Portal",
                f"Hello {student.full_name},\n\nCongratulations! Your account for the Student Portal has been approved.\n\nYou can now log in using your Student Number: {student.student_number}.\n\nThank you!",
                settings.EMAIL_HOST_USER,
                [student.email_address],
                fail_silently=True, 
            )
            messages.success(request, f"Successfully assigned {student.full_name} to {student.organization}!")
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")
    return redirect('organizer_manage_students')

@user_passes_test(is_organizer_strictly, login_url='/')
def organizer_manage_attendance(request): 
    try:
        org_profile = OrgProfile.objects.get(user=request.user)
        org_acronym = org_profile.organization.strip()
    except OrgProfile.DoesNotExist:
        org_acronym = "UNKNOWN"
    return render(request, 'organizer/manage_attendance.html', {'org_acronym': org_acronym, 'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym)})

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

    full_name = request.user.first_name if request.user.first_name else request.user.username
    
    recent_events = Event.objects.filter(org_id=org_acronym).order_by('-created_at')[:4]
    completed_events = Event.objects.filter(org_id=org_acronym, event_status='Approved').order_by('-created_at')
    pending_students = Student.objects.filter(organization__iexact=org_acronym, is_verified=False).order_by('-created_at')

    context = {
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
            data = json.loads(request.body)
            new_name = data.get('full_name')
            
            if new_name:
                request.user.first_name = new_name
                request.user.save()
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
    return render(request, 'organizer/attendance_history.html', {'org_acronym': org_acronym, 'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym)})

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
    
    for e in events:
        if e.event_status == 'Pending Adviser':
            loc = "Office of the Org Adviser (Initial Review)"
            coords = [13.8402, 121.9958] 
            progress = 1 
        elif e.event_status == 'Pending Admin':
            loc = "Admin Office (Initial Request Clearance)"
            coords = [13.8406, 121.9963] 
            progress = 2 
        elif e.event_status == 'Admin Approved':
            loc = "With Student Org (For Printing & Manual Signatures)"
            coords = [13.8408, 121.9965] 
            progress = 3 
        elif e.event_status == 'Permit Verification':
            loc = "Office of the Org Adviser (Signature Verification)"
            coords = [13.8402, 121.9958] 
            progress = 4 
        elif e.event_status == 'Final Admin Review':
            loc = "Admin Office (Final Clearance for Publication)"
            coords = [13.8406, 121.9963] 
            progress = 5 
        elif e.event_status == 'Approved':
            loc = "System Published (Live in Portal)"
            coords = [13.8408, 121.9965] 
            progress = 6 
        elif e.event_status == 'Rejected':
            loc = "Returned to Organizer"
            coords = [13.8400, 121.9955]
            progress = -1
        else:
            loc = "Unknown Location"
            coords = [13.8405, 121.9960]
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
    
    ready_events = Event.objects.filter(org_id=org_acronym, event_status='Admin Approved')
    vault_data = []
    
    for e in ready_events:
        vault_data.append({
            'id': e.id,
            'eventName': e.event_title,
            'orgName': e.org_id
        })

    context = {
        'org_acronym': org_acronym,
        'full_org_name': ORG_FULL_NAMES.get(org_acronym, org_acronym),
        'vault_json': json.dumps(vault_data)
    }
    return render(request, 'organizer/event_documents.html', context)

# 🟢 IN-UPDATE PARA SALUHIN AT I-SAVE ANG IKATLONG LARAWAN (EQUIPMENT IMAGE) 🟢
@user_passes_test(is_organizer_strictly, login_url='/')
def upload_signed_permit(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        try:
            org_profile = OrgProfile.objects.get(user=request.user)
            org_acronym = org_profile.organization.strip()
            
            event = Event.objects.get(id=event_id, org_id=org_acronym)
            event.event_status = 'Permit Verification' 
            
            if request.FILES.get('letter_image'):
                event.letter_image = request.FILES.get('letter_image')
            if request.FILES.get('permit_image'):
                event.permit_image = request.FILES.get('permit_image')
            if request.FILES.get('equipment_image'):
                event.equipment_image = request.FILES.get('equipment_image')
                
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
            'letter_url': e.letter_image.url if getattr(e, 'letter_image', None) and hasattr(e.letter_image, 'url') else '',
            'permit_url': e.permit_image.url if getattr(e, 'permit_image', None) and hasattr(e.permit_image, 'url') else '',
            'equipment_url': e.equipment_image.url if getattr(e, 'equipment_image', None) and hasattr(e.equipment_image, 'url') else ''
        })
        
    # HISTORY EVENTS (Transaction Log)
    history = Event.objects.filter(event_status__in=['Approved', 'Rejected']).order_by('-created_at')
    history_data = []
    for e in history:
        # 🟢 Idinagdag ang equipment_url pati 12-hour format sa History 🟢
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
            'letter_url': e.letter_image.url if getattr(e, 'letter_image', None) and hasattr(e.letter_image, 'url') else '',
            'permit_url': e.permit_image.url if getattr(e, 'permit_image', None) and hasattr(e.permit_image, 'url') else '',
            'equipment_url': e.equipment_image.url if getattr(e, 'equipment_image', None) and hasattr(e.equipment_image, 'url') else ''
        })
        
    return render(request, 'admin/event_approvals.html', {
        'events_json': json.dumps(pending_data),
        'history_json': json.dumps(history_data)
    })

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
            'letter_url': e.letter_image.url if getattr(e, 'letter_image', None) and hasattr(e.letter_image, 'url') else '',
            'permit_url': e.permit_image.url if getattr(e, 'permit_image', None) and hasattr(e.permit_image, 'url') else '',
            'equipment_url': e.equipment_image.url if getattr(e, 'equipment_image', None) and hasattr(e.equipment_image, 'url') else ''
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
            'letter_url': e.letter_image.url if getattr(e, 'letter_image', None) and hasattr(e.letter_image, 'url') else '',
            'permit_url': e.permit_image.url if getattr(e, 'permit_image', None) and hasattr(e.permit_image, 'url') else '',
            'equipment_url': e.equipment_image.url if getattr(e, 'equipment_image', None) and hasattr(e.equipment_image, 'url') else ''
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
# DEBUG & AUTH VIEWS
# ==========================================
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
                return JsonResponse({"status": "error", "message": "Student/Organizer accounts must login through the Student Portal (/)."})

            if user.is_staff or user.is_superuser:
                request.session['failed_attempts_staff'] = 0
                if 'lockout_until_staff' in request.session: del request.session['lockout_until_staff']
                reset_account_lockout(u)
                
                login(request, user)
                
                redirect_url = '/admin/' if user.is_superuser else '/adviser/dashboard/'
                return JsonResponse({"status": "success", "redirect_url": redirect_url})
            else:
                return JsonResponse({"status": "error", "message": "Access Denied. You do not have staff privileges."})
        else:
            is_locked_now, lock_time, total_attempts = record_failed_attempt(u)
            
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