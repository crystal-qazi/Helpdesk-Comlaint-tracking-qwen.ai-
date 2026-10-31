from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime
import csv
import io
import os

from ..permissions.decorators import permission_required
from ..services.report_service import (
    get_complaints_for_report, get_report_summary, get_grouped_stats, get_date_range
)
from ..models import Department, Software, Priority, Status, User, Category

reports_bp = Blueprint('reports', __name__)


def get_filter_options():
    """Returns common filter dropdown options."""
    return {
        'departments': Department.query.filter_by(is_active=True).order_by(Department.name).all(),
        'softwares': Software.query.filter_by(is_active=True).order_by(Software.name).all(),
        'priorities': Priority.query.filter_by(is_active=True).all(),
        'statuses': Status.query.filter_by(is_active=True).all(),
        'users': User.query.filter_by(is_active=True).order_by(User.username).all(),
        'categories': Category.query.filter_by(is_active=True).order_by(Category.name).all()
    }


@reports_bp.route('/reports')
@login_required
@permission_required('export_reports')
def reports_index():
    """Landing page for all available reports."""
    return render_template('reports/index.html')


@reports_bp.route('/reports/complaints')
@login_required
@permission_required('export_reports')
def complaints_report():
    """General complaints report with all filters."""
    report_type = request.args.get('report_type', 'custom')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id', type=int)
    software_id = request.args.get('software_id', type=int)
    priority_id = request.args.get('priority_id', type=int)
    status_id = request.args.get('status_id', type=int)
    assigned_to_user_id = request.args.get('assigned_to_user_id', type=int)
    
    complaints = get_complaints_for_report(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        software_id=software_id,
        priority_id=priority_id,
        status_id=status_id,
        assigned_to_user_id=assigned_to_user_id
    )
    
    summary = get_report_summary(complaints)
    
    return render_template(
        'reports/complaints_report.html',
        complaints=complaints,
        summary=summary,
        filters={
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date,
            'department_id': department_id,
            'software_id': software_id,
            'priority_id': priority_id,
            'status_id': status_id,
            'assigned_to_user_id': assigned_to_user_id
        },
        **get_filter_options()
    )


@reports_bp.route('/reports/overdue')
@login_required
@permission_required('export_reports')
def overdue_report():
    """Overdue complaints report."""
    complaints = get_complaints_for_report(overdue_only=True)
    summary = get_report_summary(complaints)
    
    return render_template(
        'reports/overdue_report.html',
        complaints=complaints,
        summary=summary,
        report_title='Overdue Complaints Report',
        now=datetime.utcnow()
    )


@reports_bp.route('/reports/sla-compliance')
@login_required
@permission_required('export_reports')
def sla_compliance_report():
    """SLA compliance report."""
    # Get all resolved complaints to calculate compliance
    from ..models import Complaint
    all_resolved = Complaint.query.filter(Complaint.resolved_at.isnot(None)).all()
    
    on_time = [c for c in all_resolved 
               if c.sla_resolution_deadline and c.resolved_at <= c.sla_resolution_deadline]
    breached = [c for c in all_resolved 
                if c.sla_resolution_deadline and c.resolved_at > c.sla_resolution_deadline]
    no_sla = [c for c in all_resolved if not c.sla_resolution_deadline]
    
    total = len(all_resolved)
    compliance_rate = round((len(on_time) / total) * 100, 1) if total > 0 else 100.0
    
    # Group by priority
    from collections import defaultdict
    by_priority = defaultdict(lambda: {'on_time': 0, 'breached': 0, 'total': 0})
    for c in all_resolved:
        pname = c.priority.name if c.priority else 'Unknown'
        by_priority[pname]['total'] += 1
        if c.sla_resolution_deadline and c.resolved_at <= c.sla_resolution_deadline:
            by_priority[pname]['on_time'] += 1
        elif c.sla_resolution_deadline:
            by_priority[pname]['breached'] += 1
    
    # Group by department
    by_department = defaultdict(lambda: {'on_time': 0, 'breached': 0, 'total': 0})
    for c in all_resolved:
        dname = c.department.name if c.department else 'Unknown'
        by_department[dname]['total'] += 1
        if c.sla_resolution_deadline and c.resolved_at <= c.sla_resolution_deadline:
            by_department[dname]['on_time'] += 1
        elif c.sla_resolution_deadline:
            by_department[dname]['breached'] += 1
    
    return render_template(
        'reports/sla_compliance_report.html',
        total=total,
        on_time=on_time,
        breached=breached,
        no_sla=no_sla,
        compliance_rate=compliance_rate,
        by_priority=dict(by_priority),
        by_department=dict(by_department)
    )


@reports_bp.route('/reports/by-department')
@login_required
@permission_required('export_reports')
def by_department_report():
    """Complaints grouped by department."""
    complaints = get_complaints_for_report()
    grouped = get_grouped_stats(complaints, 'department')
    
    return render_template(
        'reports/grouped_report.html',
        grouped=grouped,
        group_field='Department',
        report_title='Complaints by Department',
        complaints=complaints
    )


@reports_bp.route('/reports/by-software')
@login_required
@permission_required('export_reports')
def by_software_report():
    """Complaints grouped by software."""
    complaints = get_complaints_for_report()
    grouped = get_grouped_stats(complaints, 'software')
    
    return render_template(
        'reports/grouped_report.html',
        grouped=grouped,
        group_field='Software',
        report_title='Complaints by Software',
        complaints=complaints
    )


@reports_bp.route('/reports/by-priority')
@login_required
@permission_required('export_reports')
def by_priority_report():
    """Complaints grouped by priority."""
    complaints = get_complaints_for_report()
    grouped = get_grouped_stats(complaints, 'priority')
    
    return render_template(
        'reports/grouped_report.html',
        grouped=grouped,
        group_field='Priority',
        report_title='Complaints by Priority',
        complaints=complaints
    )


@reports_bp.route('/reports/by-status')
@login_required
@permission_required('export_reports')
def by_status_report():
    """Complaints grouped by status."""
    complaints = get_complaints_for_report()
    grouped = get_grouped_stats(complaints, 'status')
    
    return render_template(
        'reports/grouped_report.html',
        grouped=grouped,
        group_field='Status',
        report_title='Complaints by Status',
        complaints=complaints
    )


@reports_bp.route('/reports/by-assignee')
@login_required
@permission_required('export_reports')
def by_assignee_report():
    """Complaints grouped by assigned user."""
    complaints = get_complaints_for_report()
    grouped = get_grouped_stats(complaints, 'assigned_to')
    
    return render_template(
        'reports/grouped_report.html',
        grouped=grouped,
        group_field='Assigned To',
        report_title='Complaints by Assigned User',
        complaints=complaints
    )


# --- EXPORT ROUTES ---

@reports_bp.route('/reports/export/csv')
@login_required
@permission_required('export_reports')
def export_csv():
    """Export current filtered complaints as CSV."""
    # Reuse the same filters as complaints_report
    report_type = request.args.get('report_type', 'custom')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id', type=int)
    software_id = request.args.get('software_id', type=int)
    priority_id = request.args.get('priority_id', type=int)
    status_id = request.args.get('status_id', type=int)
    assigned_to_user_id = request.args.get('assigned_to_user_id', type=int)
    
    complaints = get_complaints_for_report(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        software_id=software_id,
        priority_id=priority_id,
        status_id=status_id,
        assigned_to_user_id=assigned_to_user_id
    )
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        'Complaint Number', 'Title', 'Department', 'Software', 'Category',
        'Priority', 'Status', 'Severity', 'Reported By', 'Created By',
        'Assigned To', 'Created At', 'Resolved At', 'Closed At',
        'SLA Response Deadline', 'SLA Resolution Deadline', 'Location', 'Device'
    ])
    
    # Data rows
    for c in complaints:
        writer.writerow([
            c.complaint_number,
            c.title,
            c.department.name if c.department else '',
            c.software.name if c.software else '',
            c.category.name if getattr(c, 'category', None) else '',
            c.priority.name if c.priority else '',
            c.status.name if c.status else '',
            c.severity,
            c.reported_by.username if c.reported_by else '',
            c.created_by.username if c.created_by else '',
            c.assigned_to.username if c.assigned_to else '',
            c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '',
            c.resolved_at.strftime('%Y-%m-%d %H:%M') if c.resolved_at else '',
            c.closed_at.strftime('%Y-%m-%d %H:%M') if c.closed_at else '',
            c.sla_response_deadline.strftime('%Y-%m-%d %H:%M') if c.sla_response_deadline else '',
            c.sla_resolution_deadline.strftime('%Y-%m-%d %H:%M') if c.sla_resolution_deadline else '',
            c.affected_location or '',
            c.affected_device or ''
        ])
    
    # Return as downloadable file
    output.seek(0)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f'complaints_report_{timestamp}.csv'
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # BOM for Excel compatibility
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@reports_bp.route('/reports/export/pdf')
@login_required
@permission_required('export_reports')
def export_pdf():
    """Export current filtered complaints as PDF using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    # Reuse filters
    report_type = request.args.get('report_type', 'custom')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    department_id = request.args.get('department_id', type=int)
    software_id = request.args.get('software_id', type=int)
    priority_id = request.args.get('priority_id', type=int)
    status_id = request.args.get('status_id', type=int)
    assigned_to_user_id = request.args.get('assigned_to_user_id', type=int)
    
    complaints = get_complaints_for_report(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
        software_id=software_id,
        priority_id=priority_id,
        status_id=status_id,
        assigned_to_user_id=assigned_to_user_id
    )
    
    summary = get_report_summary(complaints)
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           leftMargin=0.5*inch, rightMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0ea5e9'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # Title
    elements.append(Paragraph('Hospital IT Complaint Report', title_style))
    elements.append(Paragraph(
        f'Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} | '
        f'Total Complaints: {summary["total"]} | '
        f'SLA Compliance: {summary["sla_compliance"]}%',
        subtitle_style
    ))
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary table
    summary_data = [
        ['Total', 'Open', 'Resolved', 'Closed', 'Overdue', 'SLA Compliance'],
        [str(summary['total']), str(summary['open']), str(summary['resolved']),
         str(summary['closed']), str(summary['overdue']), f'{summary["sla_compliance"]}%']
    ]
    
    summary_table = Table(summary_data, colWidths=[1.2*inch]*6)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0ea5e9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f1f5f9')),
        ('FONTSIZE', (0, 1), (-1, 1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Complaints table
    if complaints:
        elements.append(Paragraph('Complaint Details', styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))
        
        table_data = [[
            Paragraph('<b>Ticket #</b>', styles['Normal']),
            Paragraph('<b>Title</b>', styles['Normal']),
            Paragraph('<b>Department</b>', styles['Normal']),
            Paragraph('<b>Priority</b>', styles['Normal']),
            Paragraph('<b>Status</b>', styles['Normal']),
            Paragraph('<b>Assigned To</b>', styles['Normal']),
            Paragraph('<b>Created</b>', styles['Normal'])
        ]]
        
        for c in complaints[:100]:  # Limit to 100 rows for PDF
            table_data.append([
                Paragraph(c.complaint_number, styles['Normal']),
                Paragraph(c.title[:50] + ('...' if len(c.title) > 50 else ''), styles['Normal']),
                Paragraph(c.department.name if c.department else '', styles['Normal']),
                Paragraph(c.priority.name if c.priority else '', styles['Normal']),
                Paragraph(c.status.name if c.status else '', styles['Normal']),
                Paragraph(c.assigned_to.username if c.assigned_to else 'Unassigned', styles['Normal']),
                Paragraph(c.created_at.strftime('%Y-%m-%d') if c.created_at else '', styles['Normal'])
            ])
        
        col_widths = [1*inch, 2.5*inch, 1.2*inch, 0.9*inch, 1*inch, 1.2*inch, 1*inch]
        complaints_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        complaints_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(complaints_table)
        
        if len(complaints) > 100:
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(
                f'<i>Note: Showing first 100 of {len(complaints)} complaints.</i>',
                styles['Normal']
            ))
    else:
        elements.append(Paragraph('No complaints match the selected filters.', styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f'complaints_report_{timestamp}.pdf'
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )