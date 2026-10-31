from ..extensions import db
from datetime import datetime

class ComplaintSequence(db.Model):
    """Thread-safe sequence generator for complaint numbers."""
    __tablename__ = 'complaint_sequence'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, unique=True, nullable=False)
    current_number = db.Column(db.Integer, default=0)

class Complaint(db.Model):
    __tablename__ = 'complaints'
    id = db.Column(db.Integer, primary_key=True)
    complaint_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Relationships to Config
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    software_id = db.Column(db.Integer, db.ForeignKey('software_catalog.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    priority_id = db.Column(db.Integer, db.ForeignKey('priorities.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    
    # User Relationships
    reported_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Incident Details
    severity = db.Column(db.String(50), default='Medium')
    affected_location = db.Column(db.String(100))
    affected_device = db.Column(db.String(100))
    incident_started_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Timestamps & SLA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_response_at = db.Column(db.DateTime, nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    sla_response_deadline = db.Column(db.DateTime, nullable=True)
    sla_resolution_deadline = db.Column(db.DateTime, nullable=True)
    sla_paused_at = db.Column(db.DateTime, nullable=True)
    
    # Resolution
    resolution_summary = db.Column(db.Text, nullable=True)
    root_cause = db.Column(db.Text, nullable=True)
    
    version = db.Column(db.Integer, default=1) # Optimistic locking

    # Backrefs for easy querying
    department = db.relationship('Department', backref='complaints')
    software = db.relationship('Software', backref='complaints')
    priority = db.relationship('Priority', backref='complaints')
    status = db.relationship('Status', backref='complaints')
    reported_by = db.relationship('User', foreign_keys=[reported_by_user_id], backref='reported_complaints')
    created_by = db.relationship('User', foreign_keys=[created_by_user_id], backref='created_complaints')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_user_id], backref='assigned_complaints')

class ComplaintAssignment(db.Model):
    __tablename__ = 'complaint_assignments'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    previous_assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    new_assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text)

    # --- ADDED RELATIONSHIPS ---
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_user_id])
    new_assignee = db.relationship('User', foreign_keys=[new_assignee_id])
    previous_assignee = db.relationship('User', foreign_keys=[previous_assignee_id])

class ComplaintStatusHistory(db.Model):
    __tablename__ = 'complaint_status_history'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    previous_status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=True)
    new_status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # --- ADDED RELATIONSHIPS ---
    changed_by = db.relationship('User', foreign_keys=[changed_by_user_id])
    previous_status = db.relationship('Status', foreign_keys=[previous_status_id])
    new_status = db.relationship('Status', foreign_keys=[new_status_id])