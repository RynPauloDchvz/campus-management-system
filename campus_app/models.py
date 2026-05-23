from django.db import models
from django.contrib.auth.models import User 
from django.contrib.auth.hashers import make_password 

# 1. ORGANIZATION PROFILE
class OrgProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.CharField(max_length=50) 

    def __str__(self):
        return f"{self.user.username} - {self.organization}"

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

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'): 
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.student_number})"

# 4. ATTENDANCE MODEL
class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    time_in = models.DateTimeField(auto_now_add=True)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    face_matched = models.BooleanField(default=False) 
    is_valid_location = models.BooleanField(default=False) 
    
    def __str__(self):
        return f"{self.student.student_number} - {self.event.event_title}"