from django.db import models
from django.contrib.auth.models import User 
from django.contrib.auth.hashers import make_password 

# 1. ORGANIZATION PROFILE
class OrgProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.CharField(max_length=50)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='covers/', null=True, blank=True)
    face_encoding = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.organization}"

class UserLocation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Location"

# 2. EVENT MODEL (UPDATED PARA SA 6-STEP APPROVAL AT DOCUMENT TRACKING)
class Event(models.Model):
    STATUS_CHOICES = [
        ('Pending Adviser', 'Pending Adviser Approval'),
        ('Pending Admin', 'Pending Admin Initial Clearance'),
        ('Admin Approved', 'Admin Approved (Awaiting Documents)'),
        ('Permit Verification', 'Permit Verification (Adviser)'),
        ('Final Admin Review', 'Final Admin Review'),
        ('Approved', 'Approved / Published'),
        ('Rejected', 'Rejected'),
    ]

    # Organizer Details
    org_id = models.CharField(max_length=50) # Acronym ng Org (e.g., ITO)
    proposal_by_user_id = models.CharField(max_length=100) # User ID ng nag-submit
    requester_name = models.CharField(max_length=255, null=True, blank=True) # Pangalan sa form
    
    # 🟢 Adviser Name
    adviser_name = models.CharField(max_length=255, null=True, blank=True) 
    
    # Event Details
    event_title = models.CharField(max_length=200)
    description = models.TextField()
    venue = models.CharField(max_length=200)
    
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True) # 🟢 PERPEKTONG NAKALAPAT AT HINDI KULANG!
    
    # Needs & Media (Tinanggal na ang equipment_needed gaya ng bilin mo)
    thumbnail = models.ImageField(upload_to='event_thumbnails/', null=True, blank=True) 
    
    # 🟢 MGA UPLOADS SA DOCUMENT VAULT (LETTER, PERMIT, AT EQUIPMENT IMAGE)
    letter_image = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    permit_image = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    equipment_image = models.ImageField(upload_to='event_documents/', null=True, blank=True) 
    other_attachments = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    
    # 🟢 4-File System Fields
    letter_of_approval = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    permit_to_conduct = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    excuse_letter_equipment = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    event_cover_photo = models.ImageField(upload_to='event_documents/', null=True, blank=True)

    # 🟢 2-File System Fields (Reschedule)
    letter_of_reschedule = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    reschedule_cover_photo = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    
    # Keep legacy fields for backward compatibility during migration if needed
    cover_photo = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    reschedule_cover_photo_legacy = models.ImageField(upload_to='event_documents/', null=True, blank=True)
    
    requirement_mode = models.IntegerField(null=True, blank=True, choices=[(2, '2 Documents'), (4, '4 Documents')])

    # Geofencing
    target_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    target_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # 🟢 6-Step Approval & Tracking Fields
    event_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending Adviser')
    current_location = models.CharField(max_length=100, default='Office of the Adviser')
    remarks = models.TextField(null=True, blank=True) 
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.org_id}] {self.event_title} - {self.event_status}"

# 3. STUDENT MODEL 
class Student(models.Model):
    YEAR_CHOICES = [
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) 
    
    # NILAGYAN NG DEFAULT VALUES PARA HINDI MAG-ERROR SA MIGRATION
    full_name = models.CharField(max_length=255, default='No Name') 
    student_number = models.CharField(max_length=20, unique=True)
    email_address = models.EmailField(unique=True, null=True, blank=True) 
    password = models.CharField(max_length=128, null=True, blank=True) 
    
    organization = models.CharField(max_length=50) 
    program = models.CharField(max_length=100, default='Not Assigned') 
    year_level = models.CharField(max_length=20, choices=YEAR_CHOICES)
    birthdate = models.DateField(null=True, blank=True)
    
    role = models.CharField(max_length=50, default='Student')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='covers/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    is_verified = models.BooleanField(default=False) 
    face_encoding = models.TextField(null=True, blank=True) 
    email_notifications = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'): 
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.student_number})"

# 4. ATTENDANCE MODEL
class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    organizer = models.ForeignKey(OrgProfile, on_delete=models.CASCADE, null=True, blank=True)
    
    # Time In Data
    time_in = models.DateTimeField(auto_now_add=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_valid_location = models.BooleanField(default=False)
    
    # Time Out Data
    time_out = models.DateTimeField(null=True, blank=True)
    latitude_out = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_out = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_valid_location_out = models.BooleanField(default=False)
    
    face_matched = models.BooleanField(default=False) 
    
    def __str__(self):
        target = self.student.student_number if self.student else (self.organizer.user.username if self.organizer else "Unknown")
        return f"{target} - {self.event.event_title}"

# 5. LOGIN LOCKOUT TRACKER
class LoginLockout(models.Model):
    identifier = models.CharField(max_length=100, unique=True) # student_number or username
    failed_attempts = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.identifier} - {self.failed_attempts} attempts"

# 6. AUDIT LOG MODEL (WATCHDOG)
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN_SUCCESS', 'Successful Login'),
        ('LOGIN_FAILED', 'Failed Login'),
        ('LOGOUT', 'Logout'),
        ('UNAUTHORIZED', 'Unauthorized Access Attempt'),
        ('SYSTEM_ERROR', 'System Error'),
        ('FILE_UPLOAD', 'File Uploaded'),
        ('STATUS_CHANGE', 'Approval Status Change'),
        ('ATTENDANCE', 'Attendance Recorded'),
        ('EVALUATION', 'Evaluation Submitted'),
        ('REGISTRATION', 'Account Registered'),
        ('VERIFICATION', 'Account Verified'),
    ]

    STATUS_CHOICES = [
        ('Success', 'Success'),
        ('Failed', 'Failed'),
        ('Denied', 'Denied'),
        ('Warning', 'Warning'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=100, null=True, blank=True)
    target_id = models.CharField(max_length=100, null=True, blank=True) # ID of the object being acted upon
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Success')
    
    # Context Details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    # State Tracking (Old vs New)
    changes = models.JSONField(null=True, blank=True) 
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "Anonymous"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {actor_name} -> {self.action} ({self.status})"