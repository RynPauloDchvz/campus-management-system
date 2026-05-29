import json
from .models import AuditLog
from django.utils import timezone

def get_client_ip(request):
    """Extracts the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_audit_event(request, action, target_model=None, target_id=None, status='Success', changes=None, actor=None):
    """
    Helper function to manually log an audit event.
    Can be called from views, middleware, or guards.
    """
    try:
        if not actor:
            actor = request.user if request and request.user.is_authenticated else None
            
        ip = get_client_ip(request) if request else None
        ua = request.META.get('HTTP_USER_AGENT') if request else "System/Signal"

        # Ensure changes is a JSON-serializable dict
        if changes and not isinstance(changes, dict):
            try:
                changes = json.loads(changes)
            except:
                changes = {"raw_data": str(changes)}

        AuditLog.objects.create(
            actor=actor,
            action=action,
            target_model=target_model,
            target_id=str(target_id) if target_id else None,
            status=status,
            ip_address=ip,
            user_agent=ua,
            changes=changes
        )
    except Exception as e:
        # We don't want audit logging to crash the main app flow
        print(f"CRITICAL: Failed to log audit event: {str(e)}")
