from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app)
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db
from ..models import User
from ..services.auth_service import (
    is_account_locked, get_lockout_remaining_minutes, record_login_attempt,
    get_failed_attempts_count, is_safe_redirect_url
)
from ..services.audit_service import log_login, log_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        ip_address = request.remote_addr
        
        # Get configuration values from app config
        max_attempts = current_app.config.get('MAX_FAILED_LOGIN_ATTEMPTS', 5)
        lockout_minutes = current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15)

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('auth/login.html'), 400

        if is_account_locked(username):
            remaining = get_lockout_remaining_minutes(username)
            log_login(username, None, False, ip_address, 'Login blocked: account temporarily locked')
            db.session.commit()
            flash(f'Account locked due to too many failed attempts. Try again in {remaining} minute(s).', 'danger')
            return render_template('auth/login.html'), 429

        user = User.query.filter_by(username=username).first()
        valid = bool(user and user.check_password(password) and user.is_active)

        if valid:
            # Session fixation protection: drop any pre-auth session data
            session.clear()
            login_user(user, remember=False)
            session.permanent = True

            record_login_attempt(username, user.id, ip_address, True)
            log_login(username, user.id, True, ip_address)
            db.session.commit()

            next_page = request.args.get('next') or request.form.get('next')
            if not is_safe_redirect_url(next_page):
                next_page = url_for('dashboard.index')
            return redirect(next_page)

        record_login_attempt(username, user.id if user else None, ip_address, False)
        log_login(username, user.id if user else None, False, ip_address,
                  'Invalid credentials' if user else 'Unknown username')
        db.session.commit()

        attempts = get_failed_attempts_count(username)
        remaining_attempts = max(0, max_attempts - attempts)
        if remaining_attempts > 0:
            flash(f'Invalid username or password. {remaining_attempts} attempt(s) remaining before lockout.', 'danger')
        else:
            flash(f'Account locked due to too many failed attempts. Try again in {lockout_minutes} minute(s).', 'danger')
        return render_template('auth/login.html'), 401

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    log_action('LOGOUT', 'authentication', current_user.id, current_user.username,
               details=f'User {current_user.username} logged out')
    db.session.commit()
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password') or ''
        new_password = request.form.get('new_password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html'), 400

        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'danger')
            return render_template('auth/change_password.html'), 400

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('auth/change_password.html'), 400

        if new_password == current_password:
            flash('New password must be different from the current password.', 'danger')
            return render_template('auth/change_password.html'), 400

        current_user.set_password(new_password)
        log_action('UPDATE', 'user', current_user.id, current_user.username,
                   details='Password changed by owner')
        db.session.commit()

        flash('Password changed successfully.', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/change_password.html')