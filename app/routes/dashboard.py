from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func
from ..models import (
    Complaint, Status, Priority, Department, Software, User,
    ComplaintAssignment, SLAPolicy
)
from ..extensions import db

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Render the dashboard with KPIs and chart data."""
    
    # --- KPI CALCULATIONS ---
    total_complaints = Complaint.query.count()
    
    # Status-based counts
    new_count = Complaint.query.join(Status).filter(Status.name == 'New').count()
    assigned_count = Complaint.query.join(Status).filter(Status.name == 'Assigned').count()
    in_progress_count = Complaint.query.join(Status).filter(Status.name == 'In Progress').count()
    pending_count = Complaint.query.join(Status).filter(Status.name == 'Pending Information').count()
    on_hold_count = Complaint.query.join(Status).filter(Status.name == 'On Hold').count()
    resolved_count = Complaint.query.join(Status).filter(Status.name == 'Resolved').count()
    closed_count = Complaint.query.join(Status).filter(Status.name == 'Closed').count()
    rejected_count = Complaint.query.join(Status).filter(Status.name == 'Rejected').count()
    
    # Open = all non-closed, non-rejected
    open_count = total_complaints - closed_count - rejected_count
    
    # Overdue = open complaints past SLA resolution deadline
    now = datetime.utcnow()
    overdue_count = Complaint.query.filter(
        Complaint.sla_resolution_deadline < now,
        Complaint.resolved_at.is_(None),
        Complaint.closed_at.is_(None)
    ).count()
    
    # SLA Compliance = (resolved within deadline / total resolved) * 100
    total_resolved = Complaint.query.filter(Complaint.resolved_at.isnot(None)).count()
    resolved_on_time = Complaint.query.filter(
        Complaint.resolved_at.isnot(None),
        Complaint.sla_resolution_deadline.isnot(None),
        Complaint.resolved_at <= Complaint.sla_resolution_deadline
    ).count()
    
    sla_compliance = round((resolved_on_time / total_resolved * 100), 1) if total_resolved > 0 else 100.0
    
    kpis = {
        'total': total_complaints,
        'new': new_count,
        'assigned': assigned_count,
        'in_progress': in_progress_count,
        'pending': pending_count,
        'on_hold': on_hold_count,
        'open': open_count,
        'resolved': resolved_count,
        'closed': closed_count,
        'rejected': rejected_count,
        'overdue': overdue_count,
        'sla_compliance': sla_compliance
    }
    
    # --- CHART DATA ---
    
    # 1. Complaints by Status
    status_data = db.session.query(Status.name, func.count(Complaint.id))\
        .outerjoin(Complaint).group_by(Status.id).all()
    status_labels = [s[0] for s in status_data]
    status_values = [s[1] for s in status_data]
    status_colors = ['#007bff', '#17a2b8', '#ffc107', '#6c757d', '#6f42c1', '#28a745', '#343a40', '#dc3545']
    
    # 2. Complaints by Priority
    priority_data = db.session.query(Priority.name, func.count(Complaint.id))\
        .outerjoin(Complaint).group_by(Priority.id).all()
    priority_labels = [p[0] for p in priority_data]
    priority_values = [p[1] for p in priority_data]
    priority_colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745']
    
    # 3. Complaints by Department
    dept_data = db.session.query(Department.name, func.count(Complaint.id))\
        .outerjoin(Complaint).group_by(Department.id).all()
    dept_labels = [d[0] for d in dept_data]
    dept_values = [d[1] for d in dept_data]
    
    # 4. Complaints by Software
    sw_data = db.session.query(Software.name, func.count(Complaint.id))\
        .outerjoin(Complaint).group_by(Software.id).all()
    sw_labels = [s[0] for s in sw_data]
    sw_values = [s[1] for s in sw_data]
    
    # 5. Daily Trend (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    trend_data = db.session.query(
        func.date(Complaint.created_at),
        func.count(Complaint.id)
    ).filter(Complaint.created_at >= thirty_days_ago)\
     .group_by(func.date(Complaint.created_at))\
     .order_by(func.date(Complaint.created_at)).all()
    
    # Fill in missing dates with 0
    trend_dict = {str(row[0]): row[1] for row in trend_data}
    trend_labels = []
    trend_values = []
    for i in range(30):
        day = (now - timedelta(days=29-i)).date()
        trend_labels.append(day.strftime('%m-%d'))
        trend_values.append(trend_dict.get(str(day), 0))
    
    # 6. Top 5 Engineers by workload
    engineer_data = db.session.query(
        User.username,
        func.count(Complaint.id)
    ).join(Complaint, Complaint.assigned_to_user_id == User.id)\
     .filter(Complaint.status_id.in_(
         db.session.query(Status.id).filter(Status.name.in_(['Assigned', 'In Progress']))
     ))\
     .group_by(User.id).order_by(func.count(Complaint.id).desc()).limit(5).all()
    engineer_labels = [e[0] for e in engineer_data]
    engineer_values = [e[1] for e in engineer_data]
    
    return render_template(
        'dashboard.html',
        kpis=kpis,
        status_labels=status_labels,
        status_values=status_values,
        status_colors=status_colors[:len(status_labels)],
        priority_labels=priority_labels,
        priority_values=priority_values,
        priority_colors=priority_colors[:len(priority_labels)],
        dept_labels=dept_labels,
        dept_values=dept_values,
        sw_labels=sw_labels,
        sw_values=sw_values,
        trend_labels=trend_labels,
        trend_values=trend_values,
        engineer_labels=engineer_labels,
        engineer_values=engineer_values
    )