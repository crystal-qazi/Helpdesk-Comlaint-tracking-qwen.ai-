from datetime import datetime, timedelta
from sqlalchemy import func, and_
from ..extensions import db
from ..models import (
    Complaint, Status, Priority, Department, Software, User, Category
)


def get_date_range(report_type, custom_start=None, custom_end=None):
    """Returns (start_date, end_date) based on report type."""
    now = datetime.utcnow()
    
    if report_type == 'daily':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif report_type == 'weekly':
        start = now - timedelta(days=7)
        end = now
    elif report_type == 'monthly':
        start = now - timedelta(days=30)
        end = now
    elif report_type == 'custom' and custom_start and custom_end:
        start = datetime.strptime(custom_start, '%Y-%m-%d')
        end = datetime.strptime(custom_end, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    else:
        # Default: all time
        start = None
        end = None
    
    return start, end


def build_complaint_query(start_date=None, end_date=None, department_id=None,
                          software_id=None, priority_id=None, status_id=None,
                          assigned_to_user_id=None, resolved_by_user_id=None,
                          sla_breached_only=False, overdue_only=False):
    """Builds a base query with all common filters."""
    query = Complaint.query
    
    if start_date:
        query = query.filter(Complaint.created_at >= start_date)
    if end_date:
        query = query.filter(Complaint.created_at <= end_date)
    if department_id:
        query = query.filter(Complaint.department_id == department_id)
    if software_id:
        query = query.filter(Complaint.software_id == software_id)
    if priority_id:
        query = query.filter(Complaint.priority_id == priority_id)
    if status_id:
        query = query.filter(Complaint.status_id == status_id)
    if assigned_to_user_id:
        query = query.filter(Complaint.assigned_to_user_id == assigned_to_user_id)
    if resolved_by_user_id:
        # We need to join status history to find who resolved it
        # For simplicity, we'll use a subquery approach
        resolved_complaint_ids = db.session.query(
            ComplaintStatusHistory.complaint_id
        ).join(Status, ComplaintStatusHistory.new_status_id == Status.id
        ).filter(Status.name == 'Resolved').subquery()
        query = query.filter(Complaint.id.in_(resolved_complaint_ids))
    if sla_breached_only:
        now = datetime.utcnow()
        query = query.filter(
            Complaint.sla_resolution_deadline < now,
            Complaint.resolved_at.is_(None),
            Complaint.closed_at.is_(None)
        )
    if overdue_only:
        now = datetime.utcnow()
        query = query.filter(
            Complaint.sla_resolution_deadline < now,
            Complaint.resolved_at.is_(None)
        )
    
    return query.order_by(Complaint.created_at.desc())


def get_complaints_for_report(report_type='custom', start_date=None, end_date=None,
                               department_id=None, software_id=None, priority_id=None,
                               status_id=None, assigned_to_user_id=None,
                               sla_breached_only=False, overdue_only=False):
    """Main entry point for getting filtered complaints."""
    if report_type in ['daily', 'weekly', 'monthly']:
        start_date, end_date = get_date_range(report_type)
    
    return build_complaint_query(
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        software_id=software_id,
        priority_id=priority_id,
        status_id=status_id,
        assigned_to_user_id=assigned_to_user_id,
        sla_breached_only=sla_breached_only,
        overdue_only=overdue_only
    ).all()


def get_report_summary(complaints):
    """Generates summary statistics for a set of complaints."""
    if not complaints:
        return {
            'total': 0, 'new': 0, 'open': 0, 'resolved': 0, 'closed': 0,
            'rejected': 0, 'overdue': 0, 'sla_compliance': 0
        }
    
    now = datetime.utcnow()
    total = len(complaints)
    
    new_count = sum(1 for c in complaints if c.status.name == 'New')
    resolved_count = sum(1 for c in complaints if c.status.name == 'Resolved')
    closed_count = sum(1 for c in complaints if c.status.name == 'Closed')
    rejected_count = sum(1 for c in complaints if c.status.name == 'Rejected')
    
    open_count = total - closed_count - rejected_count
    overdue_count = sum(1 for c in complaints 
                        if c.sla_resolution_deadline and 
                        c.sla_resolution_deadline < now and 
                        not c.resolved_at and not c.closed_at)
    
    resolved_complaints = [c for c in complaints if c.resolved_at]
    if resolved_complaints:
        on_time = sum(1 for c in resolved_complaints 
                      if c.sla_resolution_deadline and c.resolved_at <= c.sla_resolution_deadline)
        sla_compliance = round((on_time / len(resolved_complaints)) * 100, 1)
    else:
        sla_compliance = 100.0
    
    return {
        'total': total,
        'new': new_count,
        'open': open_count,
        'resolved': resolved_count,
        'closed': closed_count,
        'rejected': rejected_count,
        'overdue': overdue_count,
        'sla_compliance': sla_compliance
    }


def get_grouped_stats(complaints, group_by_field):
    """Groups complaints by a field and returns counts."""
    from collections import defaultdict
    groups = defaultdict(int)
    
    for c in complaints:
        if group_by_field == 'status':
            key = c.status.name if c.status else 'Unknown'
        elif group_by_field == 'priority':
            key = c.priority.name if c.priority else 'Unknown'
        elif group_by_field == 'department':
            key = c.department.name if c.department else 'Unknown'
        elif group_by_field == 'software':
            key = c.software.name if c.software else 'Unknown'
        elif group_by_field == 'assigned_to':
            key = c.assigned_to.username if c.assigned_to else 'Unassigned'
        elif group_by_field == 'category':
            key = c.category.name if c.category else 'Uncategorized'
        else:
            key = 'Unknown'
        groups[key] += 1
    
    return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))