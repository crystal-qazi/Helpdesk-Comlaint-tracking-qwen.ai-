from ..extensions import db
from datetime import datetime

class SLAPolicy(db.Model):
    __tablename__ = 'sla_policies'
    id = db.Column(db.Integer, primary_key=True)
    priority_id = db.Column(db.Integer, db.ForeignKey('priorities.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True) # Null = Global policy for this priority
    response_time_minutes = db.Column(db.Integer, nullable=False)
    resolution_time_minutes = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    priority = db.relationship('Priority', backref='sla_policies')
    department = db.relationship('Department', backref='sla_policies')

class Holiday(db.Model):
    __tablename__ = 'holidays'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class WorkingSchedule(db.Model):
    __tablename__ = 'working_schedules'
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False) # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    is_working_day = db.Column(db.Boolean, default=True)

class SLAHistory(db.Model):
    __tablename__ = 'sla_history'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False) # created, paused, resumed, recalculated
    previous_response_deadline = db.Column(db.DateTime, nullable=True)
    new_response_deadline = db.Column(db.DateTime, nullable=True)
    previous_resolution_deadline = db.Column(db.DateTime, nullable=True)
    new_resolution_deadline = db.Column(db.DateTime, nullable=True)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

class EscalationHistory(db.Model):
    __tablename__ = 'escalation_history'
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    escalated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    escalated_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason = db.Column(db.Text)
    escalated_at = db.Column(db.DateTime, default=datetime.utcnow)