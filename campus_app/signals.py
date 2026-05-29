from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Event, AuditLog
from .middleware import get_current_request
from .utils import get_client_ip
import json

@receiver(pre_save, sender=Event)
def track_event_changes(sender, instance, **kwargs):
    """
    Automated watchdog for Event model updates.
    Compares old vs new state before saving.
    """
    if not instance.pk:
        return

    try:
        old_instance = Event.objects.get(pk=instance.pk)
    except Event.DoesNotExist:
        return

    changes = {}
    monitored_fields = ['event_status', 'venue', 'event_date', 'event_title', 'current_location']

    for field in monitored_fields:
        old_val = getattr(old_instance, field)
        new_val = getattr(instance, field)

        if old_val != new_val:
            changes[field] = {
                "old": str(old_val),
                "new": str(new_val)
            }

    if changes:
        request = get_current_request()
        actor = request.user if request and request.user.is_authenticated else None
        ip = get_client_ip(request) if request else None
        ua = request.META.get('HTTP_USER_AGENT') if request else "Django Signal (Automated Watchdog)"

        AuditLog.objects.create(
            actor=actor,
            action='UPDATE',
            target_model='Event',
            target_id=str(instance.pk),
            status='Success',
            changes=changes,
            ip_address=ip,
            user_agent=ua
        )

@receiver(post_save, sender=Event)
def log_event_creation(sender, instance, created, **kwargs):
    """Logs the initial creation of an event."""
    if created:
        request = get_current_request()
        actor = request.user if request and request.user.is_authenticated else None
        ip = get_client_ip(request) if request else None
        ua = request.META.get('HTTP_USER_AGENT') if request else "Django Signal (Automated Watchdog)"

        AuditLog.objects.create(
            actor=actor,
            action='CREATE',
            target_model='Event',
            target_id=str(instance.pk),
            status='Success',
            changes={"initial_data": {"title": instance.event_title, "org": instance.org_id}},
            ip_address=ip,
            user_agent=ua
        )
