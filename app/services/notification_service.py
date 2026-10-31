from ..extensions import db
from ..models import Notification, User, Complaint

def create_notification(user_id, notification_type, title, message, complaint_id=None, link=None):
    """Create a notification for a specific user."""
    notification = Notification(
        user_id=user_id,
        complaint_id=complaint_id,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    db.session.add(notification)
    return notification


def notify_assignment(complaint, assignee, assigned_by):
    """Notify the assignee about a new assignment."""
    if assignee.id == assigned_by.id:
        return  # Don't notify yourself
    
    create_notification(
        user_id=assignee.id,
        notification_type='assignment',
        title=f'New Assignment: {complaint.complaint_number}',
        message=f'{assigned_by.username} assigned complaint "{complaint.title}" to you.',
        complaint_id=complaint.id,
        link=f'/complaints/{complaint.id}'
    )
    db.session.commit()


def notify_status_change(complaint, old_status_name, new_status_name, changed_by):
    """Notify relevant users about a status change."""
    # Notify the reporter (if different from the person who changed status)
    if complaint.reported_by_user_id != changed_by.id:
        create_notification(
            user_id=complaint.reported_by_user_id,
            notification_type='status_change',
            title=f'Status Update: {complaint.complaint_number}',
            message=f'Your complaint "{complaint.title}" status changed from {old_status_name} to {new_status_name}.',
            complaint_id=complaint.id,
            link=f'/complaints/{complaint.id}'
        )
    
    # Notify the assignee (if different from reporter and changer)
    if complaint.assigned_to_user_id and \
       complaint.assigned_to_user_id != changed_by.id and \
       complaint.assigned_to_user_id != complaint.reported_by_user_id:
        create_notification(
            user_id=complaint.assigned_to_user_id,
            notification_type='status_change',
            title=f'Status Update: {complaint.complaint_number}',
            message=f'Complaint "{complaint.title}" status changed to {new_status_name}.',
            complaint_id=complaint.id,
            link=f'/complaints/{complaint.id}'
        )
    
    db.session.commit()


def notify_new_comment(complaint, commenter, comment_visibility):
    """Notify relevant users about a new comment."""
    notified_user_ids = set()
    
    # Notify assignee
    if complaint.assigned_to_user_id and complaint.assigned_to_user_id != commenter.id:
        notified_user_ids.add(complaint.assigned_to_user_id)
    
    # Notify reporter (only for reporter_visible comments)
    if comment_visibility == 'reporter_visible' and \
       complaint.reported_by_user_id != commenter.id:
        notified_user_ids.add(complaint.reported_by_user_id)
    
    for user_id in notified_user_ids:
        create_notification(
            user_id=user_id,
            notification_type='comment',
            title=f'New Comment: {complaint.complaint_number}',
            message=f'{commenter.username} added a comment on "{complaint.title}".',
            complaint_id=complaint.id,
            link=f'/complaints/{complaint.id}'
        )
    
    db.session.commit()


def notify_resolution(complaint, resolved_by):
    """Notify the reporter that their complaint has been resolved."""
    if complaint.reported_by_user_id != resolved_by.id:
        create_notification(
            user_id=complaint.reported_by_user_id,
            notification_type='resolution',
            title=f'Resolved: {complaint.complaint_number}',
            message=f'Your complaint "{complaint.title}" has been resolved.',
            complaint_id=complaint.id,
            link=f'/complaints/{complaint.id}'
        )
        db.session.commit()


def notify_sla_breach(complaint):
    """Notify the assignee and relevant users about an SLA breach."""
    notified_user_ids = set()
    
    if complaint.assigned_to_user_id:
        notified_user_ids.add(complaint.assigned_to_user_id)
    
    # Also notify all Admins
    from ..models import Role
    admin_role = Role.query.filter_by(name='Admin').first()
    if admin_role:
        for admin in admin_role.users:
            notified_user_ids.add(admin.id)
    
    for user_id in notified_user_ids:
        create_notification(
            user_id=user_id,
            notification_type='sla_breach',
            title=f'🚨 SLA Breach: {complaint.complaint_number}',
            message=f'Complaint "{complaint.title}" has breached its SLA deadline.',
            complaint_id=complaint.id,
            link=f'/complaints/{complaint.id}'
        )
    
    db.session.commit()


def get_unread_count(user_id):
    """Get the count of unread notifications for a user."""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()