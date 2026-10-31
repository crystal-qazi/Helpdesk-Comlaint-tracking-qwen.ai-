from flask import Blueprint, render_template, jsonify, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from ..models import Notification
from ..extensions import db

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
@login_required
def list_notifications():
    """Display all notifications for the current user."""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(100).all()
    
    # Mark all as read
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    response = make_response(render_template('notifications/list.html', notifications=notifications))
    # Prevent browser caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@notifications_bp.route('/notifications/unread-count')
@login_required
def unread_count():
    """API endpoint to get unread notification count (for AJAX polling)."""
    from ..services.notification_service import get_unread_count
    count = get_unread_count(current_user.id)
    return jsonify({'count': count})


@notifications_bp.route('/notifications/<int:notification_id>/read')
@login_required
def mark_read(notification_id):
    """Mark a single notification as read and redirect to its link."""
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('notifications.list_notifications'))
    
    notification.mark_as_read()
    db.session.commit()
    
    if notification.link:
        return redirect(notification.link)
    return redirect(url_for('notifications.list_notifications'))