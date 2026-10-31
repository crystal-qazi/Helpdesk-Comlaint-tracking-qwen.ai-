from functools import wraps
from flask import abort, current_app
from flask_login import current_user
from ..services.audit_service import log_access_denied


def permission_required(*permission_names, require_all=False):
    """Server-side permission enforcement + audit of denied attempts."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()

            checks = [current_user.has_permission(p) for p in permission_names]
            allowed = all(checks) if require_all else any(checks)

            if not allowed:
                log_access_denied(
                    entity_type='route',
                    reason=f"Missing permission(s): {', '.join(permission_names)} on {f.__name__}"
                )
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def can_view_complaint(user, complaint):
    """Ownership / permission based access rule (IDOR protection)."""
    if not user.is_authenticated:
        return False
    if user.has_permission('view_complaints'):
        return True
    if complaint.reported_by_user_id == user.id:
        return True
    if complaint.created_by_user_id == user.id:
        return True
    if complaint.assigned_to_user_id == user.id:
        return True
    return False


def complaint_access_required(f):
    """Load complaint by <complaint_id> then enforce access."""
    @wraps(f)
    def wrapper(complaint_id, *args, **kwargs):
        print(f"\n[DEBUG DECORATOR] complaint_access_required WRAPPER EXECUTING for ID: {complaint_id}")
        from ..models import Complaint
        complaint = Complaint.query.get_or_404(complaint_id)
        
        print(f"[DEBUG DECORATOR] current_user.is_authenticated: {current_user.is_authenticated}")
        print(f"[DEBUG DECORATOR] current_user.id: {getattr(current_user, 'id', 'NO ID')}")
        
        if not current_user.is_authenticated:
            print("[DEBUG DECORATOR] -> Not authenticated, returning unauthorized")
            return current_app.login_manager.unauthorized()
            
        if not can_view_complaint(current_user, complaint):
            print("[DEBUG DECORATOR] -> can_view_complaint returned False, aborting 403")
            log_access_denied('complaint', complaint_id, 'Complaint access denied (IDOR attempt)')
            abort(403)
            
        print("[DEBUG DECORATOR] -> Access granted, proceeding to route")
        return f(complaint_id, *args, **kwargs)
    return wrapper