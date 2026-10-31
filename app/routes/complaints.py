from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from ..models import (
    Complaint, Department, Software, Category, Priority, Status, 
    ComplaintAssignment, ComplaintStatusHistory, User, Comment, Attachment
)
from ..extensions import db
from ..permissions.decorators import permission_required, complaint_access_required
from ..services.complaint_service import generate_complaint_number
from ..services.file_service import save_upload
from ..services.sla_service import calculate_initial_sla
from ..models import SLAHistory
from ..services.notification_service import (
    notify_assignment, notify_status_change, notify_new_comment, notify_resolution
)

complaints_bp = Blueprint('complaints', __name__)


@complaints_bp.route('/complaints')
@login_required
@permission_required('view_complaints')
def list_complaints():
    """List all complaints with basic ordering."""
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('complaints/list.html', complaints=complaints)


@complaints_bp.route('/complaints/new', methods=['GET', 'POST'])
@login_required
@permission_required('create_complaint')
def create_complaint():
    """Register a new complaint with automatic number generation."""
    if request.method == 'POST':
        comp_number = generate_complaint_number()
        
        new_complaint = Complaint(
            complaint_number=comp_number,
            title=request.form.get('title'),
            description=request.form.get('description'),
            department_id=request.form.get('department_id'),
            software_id=request.form.get('software_id'),
            category_id=request.form.get('category_id') or None,
            priority_id=request.form.get('priority_id'),
            status_id=Status.query.filter_by(name='New').first().id,
            reported_by_user_id=request.form.get('reported_by_user_id') or current_user.id,
            created_by_user_id=current_user.id,
            severity=request.form.get('severity', 'Medium'),
            affected_location=request.form.get('affected_location'),
            affected_device=request.form.get('affected_device')
        )
        
        db.session.add(new_complaint)
        db.session.flush()

                # Calculate and set SLA deadlines
        response_deadline, resolution_deadline = calculate_initial_sla(new_complaint)
        new_complaint.sla_response_deadline = response_deadline
        new_complaint.sla_resolution_deadline = resolution_deadline
        db.session.add(new_complaint) # Re-add to update SLA fields
        
        # Record initial status history
        history = ComplaintStatusHistory(
            complaint_id=new_complaint.id,
            new_status_id=new_complaint.status_id,
            changed_by_user_id=current_user.id,
            notes="Complaint created."
        )
        db.session.add(history)
        db.session.commit()
        
        flash(f'Complaint {comp_number} created successfully!', 'success')
        return redirect(url_for('complaints.view_complaint', complaint_id=new_complaint.id))

    # GET request: show form
    departments = Department.query.filter_by(is_active=True).all()
    softwares = Software.query.filter_by(is_active=True).all()
    categories = Category.query.filter_by(is_active=True).all()
    priorities = Priority.query.filter_by(is_active=True).all()
    
    return render_template(
        'complaints/create.html',
        departments=departments,
        softwares=softwares,
        categories=categories,
        priorities=priorities
    )


@complaints_bp.route('/complaints/<int:complaint_id>')
@login_required
# @permission_required('view_complaints')
@complaint_access_required   # <--- MUST BE THIS, NOT @permission_required

def view_complaint(complaint_id):
    """Display complaint details with full activity timeline."""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Fetch histories for the timeline
    status_history = ComplaintStatusHistory.query.filter_by(
        complaint_id=complaint_id
    ).order_by(ComplaintStatusHistory.changed_at.desc()).all()
    
    assignment_history = ComplaintAssignment.query.filter_by(
        complaint_id=complaint_id
    ).order_by(ComplaintAssignment.assigned_at.desc()).all()
    
    # Fetch data for the action forms
    statuses = Status.query.filter_by(is_active=True).all()
    users = User.query.filter_by(is_active=True).all()
    
    return render_template(
        'complaints/detail.html',
        complaint=complaint,
        status_history=status_history,
        assignment_history=assignment_history,
        statuses=statuses,
        users=users,
        now=datetime.utcnow()
    )


@complaints_bp.route('/complaints/<int:complaint_id>/assign', methods=['POST'])
@login_required
@permission_required('assign_complaint')
def assign_complaint(complaint_id):
    """Assign or reassign a complaint to a user."""
    complaint = Complaint.query.get_or_404(complaint_id)
    new_assignee_id = request.form.get('assigned_to_user_id')
    reason = request.form.get('reason', 'Reassigned via system')
    
    if not new_assignee_id:
        flash('Please select a user to assign.', 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))

    # Record assignment history
    assignment = ComplaintAssignment(
        complaint_id=complaint.id,
        previous_assignee_id=complaint.assigned_to_user_id,
        new_assignee_id=new_assignee_id,
        assigned_by_user_id=current_user.id,
        reason=reason
    )
    db.session.add(assignment)
    
    # Update current assignee
    complaint.assigned_to_user_id = new_assignee_id
    complaint.assigned_at = datetime.utcnow()
    
    
    db.session.commit()
        # Send notification to assignee
    new_assignee = User.query.get(new_assignee_id)
    notify_assignment(complaint, new_assignee, current_user)
    flash('Complaint assigned successfully.', 'success')
    return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))


@complaints_bp.route('/complaints/<int:complaint_id>/status', methods=['POST'])
@login_required
def update_status(complaint_id):
    """Update complaint status with workflow validation."""
    complaint = Complaint.query.get_or_404(complaint_id)
    new_status_id = request.form.get('status_id')
    notes = request.form.get('notes', '')
    
    new_status = Status.query.get_or_404(new_status_id)
    
    # Workflow validation
    if new_status.name == 'Resolved' and not request.form.get('resolution_summary'):
        flash('Resolution summary is required to resolve a complaint.', 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))
        
    if new_status.name == 'Rejected' and not notes:
        flash('Rejection reason is required.', 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))

    # Record status history
    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        previous_status_id=complaint.status_id,
        new_status_id=new_status.id,
        changed_by_user_id=current_user.id,
        notes=notes
    )
    db.session.add(history)
    
    # Update complaint status and timestamps
    complaint.status_id = new_status.id
    
    if new_status.name == 'Resolved':
        complaint.resolved_at = datetime.utcnow()
        complaint.resolution_summary = request.form.get('resolution_summary')
    elif new_status.name == 'Closed':
        complaint.closed_at = datetime.utcnow()

        # --- SLA PAUSE / RESUME LOGIC ---
    pause_statuses = ['Pending Information', 'On Hold']
    now = datetime.utcnow()
    
    # If moving TO a pause status
    if new_status.name in pause_statuses and not complaint.sla_paused_at:
        complaint.sla_paused_at = now
        
        # Record SLA History
        sla_hist = SLAHistory(
            complaint_id=complaint.id,
            event_type='paused',
            previous_response_deadline=complaint.sla_response_deadline,
            new_response_deadline=complaint.sla_response_deadline, # Deadlines don't change yet
            previous_resolution_deadline=complaint.sla_resolution_deadline,
            new_resolution_deadline=complaint.sla_resolution_deadline,
            changed_by_user_id=current_user.id,
            notes=f"SLA paused due to status change to {new_status.name}"
        )
        db.session.add(sla_hist)
        
    # If moving FROM a pause status
    elif complaint.sla_paused_at and new_status.name not in pause_statuses:
        pause_duration = now - complaint.sla_paused_at
        pause_minutes = pause_duration.total_seconds() / 60
        
        old_response = complaint.sla_response_deadline
        old_resolution = complaint.sla_resolution_deadline
        
        # Extend deadlines by the pause duration
        if old_response:
            complaint.sla_response_deadline = old_response + pause_duration
        if old_resolution:
            complaint.sla_resolution_deadline = old_resolution + pause_duration
            
        complaint.sla_paused_at = None # Clear pause flag
        
        # Record SLA History
        sla_hist = SLAHistory(
            complaint_id=complaint.id,
            event_type='resumed',
            previous_response_deadline=old_response,
            new_response_deadline=complaint.sla_response_deadline,
            previous_resolution_deadline=old_resolution,
            new_resolution_deadline=complaint.sla_resolution_deadline,
            changed_by_user_id=current_user.id,
            notes=f"SLA resumed. Paused for {int(pause_minutes)} minutes. Deadlines extended."
        )
        db.session.add(sla_hist)
        # Capture old status name before commit

    old_status_name = Status.query.get(history.previous_status_id).name if history.previous_status_id else 'None'    
    db.session.commit()
        # Send notifications
    notify_status_change(complaint, old_status_name, new_status.name, current_user)
    
    if new_status.name == 'Resolved':
        notify_resolution(complaint, current_user)
    flash(f'Status updated to {new_status.name}.', 'success')
    return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))


@complaints_bp.route('/complaints/<int:complaint_id>/comment', methods=['POST'])
@login_required
def add_comment(complaint_id):
    """Add an internal or reporter-visible comment to a complaint."""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    comment_text = request.form.get('comment_text', '').strip()
    visibility = request.form.get('visibility', 'internal')
    
    if not comment_text:
        flash('Comment cannot be empty.', 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))
    
    if visibility not in ['internal', 'reporter_visible']:
        visibility = 'internal'
    
    comment = Comment(
        complaint_id=complaint.id,
        user_id=current_user.id,
        comment_text=comment_text,
        visibility=visibility
    )
    db.session.add(comment)
    db.session.commit()
        # Send notification
    notify_new_comment(complaint, current_user, visibility)
    
    flash('Comment added successfully.', 'success')
    return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))


@complaints_bp.route('/complaints/<int:complaint_id>/attachment', methods=['POST'])
@login_required
def upload_attachment(complaint_id):
    """Upload a file attachment to a complaint with validation."""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if 'file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))
    
    file = request.files['file']
    
    stored_filename, storage_path, file_size, mime_type, error = save_upload(file)
    
    if error:
        flash(error, 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))
    
    attachment = Attachment(
        complaint_id=complaint.id,
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        storage_path=storage_path,
        file_size=file_size,
        mime_type=mime_type
    )
    db.session.add(attachment)
    db.session.commit()
    
    flash('File uploaded successfully.', 'success')
    return redirect(url_for('complaints.view_complaint', complaint_id=complaint_id))


@complaints_bp.route('/complaints/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    """Download an attachment with authorization check and robust path resolution."""
    attachment = Attachment.query.get_or_404(attachment_id)
    complaint = Complaint.query.get_or_404(attachment.complaint_id)
    
    # Authorization check: user must have view_complaints permission or be the reporter
    if not current_user.has_permission('view_complaints'):
        if complaint.reported_by_user_id != current_user.id:
            abort(403)
    
    # ROBUST PATH RESOLUTION:
    # Reconstruct the absolute path using the configured UPLOAD_FOLDER and stored_filename.
    # This completely bypasses any old, incorrect relative paths saved in the database.
    from flask import current_app
    upload_folder = current_app.config['UPLOAD_FOLDER']
    safe_storage_path = os.path.join(upload_folder, attachment.stored_filename)
    
    # Verify file exists at the corrected, guaranteed-absolute path
    if not os.path.exists(safe_storage_path):
        current_app.logger.error(f"File not found at: {safe_storage_path}")
        flash('File not found on server.', 'danger')
        return redirect(url_for('complaints.view_complaint', complaint_id=complaint.id))
    
    # Send file with original filename
    return send_file(
        safe_storage_path,
        as_attachment=True,
        download_name=attachment.original_filename,
        mimetype=attachment.mime_type
    )