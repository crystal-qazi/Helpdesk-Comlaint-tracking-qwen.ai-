import json
from flask import request
from flask_login import current_user
from ..extensions import db
from ..models import AuditLog

SENSITIVE_FIELDS = {'password', 'password_hash', 'secret', 'secret_key', 'token', 'csrf_token'}


def _sanitize(values):
    if values is None:
        return None
    if isinstance(values, dict):
        return {k: v for k, v in values.items() if str(k).lower() not in SENSITIVE_FIELDS}
    return values


def _actor():
    try:
        if current_user.is_authenticated:
            return current_user.id, current_user.username
        return None, 'anonymous'
    except RuntimeError:
        return None, 'system'


def log_action(action, entity_type, entity_id=None, entity_name=None,
               old_values=None, new_values=None, details=None, commit=False):
    user_id, username = _actor()

    try:
        ip_address = request.remote_addr
        user_agent = (request.headers.get('User-Agent') or '')[:500]
        path = (request.full_path or request.path)[:500]
    except RuntimeError:
        ip_address = user_agent = path = None

    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=(str(entity_name)[:255] if entity_name is not None else None),
        old_values=json.dumps(_sanitize(old_values), default=str) if old_values else None,
        new_values=json.dumps(_sanitize(new_values), default=str) if new_values else None,
        ip_address=ip_address,
        user_agent=user_agent,
        request_path=path,
        details=details,
    )
    db.session.add(entry)
    if commit:
        db.session.commit()
    return entry


def log_login(username, user_id, success, ip_address=None, details=None):
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action='LOGIN_SUCCESS' if success else 'LOGIN_FAILURE',
        entity_type='authentication',
        entity_name=username,
        ip_address=ip_address,
        details=details or f"Login {'successful' if success else 'failed'} for '{username}'",
    )
    db.session.add(entry)
    return entry


def log_access_denied(entity_type, entity_id=None, reason=None):
    return log_action(
        action='ACCESS_DENIED',
        entity_type=entity_type,
        entity_id=entity_id,
        details=reason or 'Unauthorized access attempt blocked',
        commit=True,
    )