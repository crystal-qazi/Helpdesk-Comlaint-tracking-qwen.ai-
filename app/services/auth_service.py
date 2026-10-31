from datetime import datetime, timedelta
from flask import current_app
from ..extensions import db
from ..models import LoginAttempt


def _cfg(key, default):
    try:
        return current_app.config.get(key, default)
    except RuntimeError:
        return default


def _last_success_time(username):
    row = (LoginAttempt.query
           .filter_by(attempted_username=username, success=True)
           .order_by(LoginAttempt.attempted_at.desc())
           .first())
    return row.attempted_at if row else None


def get_failed_attempts_count(username):
    if not username:
        return 0
    window_start = datetime.utcnow() - timedelta(minutes=_cfg('LOGIN_ATTEMPT_WINDOW_MINUTES', 30))
    last_success = _last_success_time(username)
    if last_success and last_success > window_start:
        window_start = last_success

    return (LoginAttempt.query
            .filter(LoginAttempt.attempted_username == username,
                    LoginAttempt.success.is_(False),
                    LoginAttempt.attempted_at >= window_start)
            .count())


def is_account_locked(username):
    if not username:
        return False
    max_attempts = _cfg('MAX_FAILED_LOGIN_ATTEMPTS', 5)
    if get_failed_attempts_count(username) < max_attempts:
        return False

    last_failure = (LoginAttempt.query
                    .filter_by(attempted_username=username, success=False)
                    .order_by(LoginAttempt.attempted_at.desc())
                    .first())
    if not last_failure:
        return False

    lockout_end = last_failure.attempted_at + timedelta(minutes=_cfg('LOGIN_LOCKOUT_MINUTES', 15))
    return datetime.utcnow() < lockout_end


def get_lockout_remaining_minutes(username):
    last_failure = (LoginAttempt.query
                    .filter_by(attempted_username=username, success=False)
                    .order_by(LoginAttempt.attempted_at.desc())
                    .first())
    if not last_failure:
        return 0
    lockout_end = last_failure.attempted_at + timedelta(minutes=_cfg('LOGIN_LOCKOUT_MINUTES', 15))
    remaining = (lockout_end - datetime.utcnow()).total_seconds() / 60
    return max(0, int(remaining) + (1 if remaining % 1 else 0))


def record_login_attempt(username, user_id, ip_address, success):
    attempt = LoginAttempt(
        user_id=user_id,
        ip_address=ip_address,
        attempted_username=(username or '')[:80],
        success=success,
        attempted_at=datetime.utcnow(),
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def is_safe_redirect_url(target):
    if not target:
        return False
    from urllib.parse import urlsplit
    parts = urlsplit(target.replace('\\', ''))
    return (not parts.scheme and not parts.netloc and target.startswith('/')
            and not target.startswith('//'))