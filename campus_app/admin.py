from django.contrib import admin
from .models import OrgProfile, UserLocation, Event, Student, Attendance, LoginLockout, AuditLog

@admin.register(OrgProfile)
class OrgProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization')
    search_fields = ('organization',)

@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'last_updated')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_title', 'org_id', 'event_date', 'event_status')
    list_filter = ('event_status', 'org_id')
    search_fields = ('event_title', 'description')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_number', 'full_name', 'organization', 'is_verified')
    list_filter = ('is_verified', 'organization', 'year_level')
    search_fields = ('student_number', 'full_name')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'event', 'time_in', 'time_out', 'face_matched', 'is_valid_location')
    list_filter = ('face_matched', 'is_valid_location', 'event')

@admin.register(LoginLockout)
class LoginLockoutAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'failed_attempts', 'lockout_until')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'actor', 'target_model')
    list_filter = ('action', 'target_model')
