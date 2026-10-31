from datetime import datetime, time as dtime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from ..extensions import db
from ..models import (User, Role, Permission, UserProfile, Department, Software, Category,
                      Priority, Status, SLAPolicy, WorkingSchedule, Holiday, AuditLog,
                      Complaint)
from ..permissions.decorators import permission_required
from ..services.audit_service import log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _set_roles(user, role_ids):
    """Works with both list and dynamic relationships."""
    for role in list(user.roles):
        user.roles.remove(role)
    for rid in role_ids:
        role = Role.query.get(int(rid))
        if role:
            user.roles.append(role)


def _set_permissions(role, permission_ids):
    for perm in list(role.permissions):
        role.permissions.remove(perm)
    for pid in permission_ids:
        perm = Permission.query.get(int(pid))
        if perm:
            role.permissions.append(perm)


# ---------------------------------------------------------------- USERS
@admin_bp.route('/users')
@login_required
@permission_required('manage_users')
def users():
    return render_template('admin/users.html', users=User.query.order_by(User.username).all())


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def create_user():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        email = (request.form.get('email') or '').strip() or None

        if not username or len(password) < 8:
            flash('Username is required and password must be at least 8 characters.', 'danger')
            return redirect(url_for('admin.create_user'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        if email and User.query.filter_by(email=email).first():
            flash('Email already in use.', 'danger')
            return redirect(url_for('admin.create_user'))

        user = User(username=username, email=email, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        employee_number = (request.form.get('employee_number') or '').strip() or None
        db.session.add(UserProfile(
            user_id=user.id,
            full_name=(request.form.get('full_name') or '').strip() or None,
            employee_number=employee_number
        ))
        _set_roles(user, request.form.getlist('role_ids'))

        log_action('CREATE', 'user', user.id, user.username,
                   new_values={'username': username, 'email': email,
                               'roles': [r.name for r in user.roles]},
                   details=f'User {username} created')
        db.session.commit()
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', roles=Role.query.filter_by(is_active=True).all(), user=None)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        old = {'email': user.email, 'is_active': user.is_active,
               'roles': [r.name for r in user.roles]}

        if user.id == current_user.id and request.form.get('is_active') != 'on':
            flash('You cannot deactivate your own account.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))

        user.email = (request.form.get('email') or '').strip() or None
        user.is_active = request.form.get('is_active') == 'on'

        if not user.profile:
            db.session.add(UserProfile(user_id=user.id))
            db.session.flush()
        user.profile.full_name = (request.form.get('full_name') or '').strip() or None
        user.profile.employee_number = (request.form.get('employee_number') or '').strip() or None
        user.profile.extension_number = (request.form.get('extension_number') or '').strip() or None
        user.profile.contact_info = (request.form.get('contact_info') or '').strip() or None

        new_password = request.form.get('password') or ''
        password_changed = False
        if new_password:
            if len(new_password) < 8:
                flash('Password must be at least 8 characters.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user.id))
            user.set_password(new_password)
            password_changed = True

        _set_roles(user, request.form.getlist('role_ids'))

        log_action('UPDATE', 'user', user.id, user.username,
                   old_values=old,
                   new_values={'email': user.email, 'is_active': user.is_active,
                               'roles': [r.name for r in user.roles],
                               'password_changed': password_changed},
                   details=f'User {user.username} updated')
        db.session.commit()
        flash(f'User {user.username} updated successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', roles=Role.query.all(), user=user)


# ---------------------------------------------------------------- ROLES
@admin_bp.route('/roles')
@login_required
@permission_required('manage_users')
def roles():
    return render_template('admin/roles.html', roles=Role.query.order_by(Role.name).all())


@admin_bp.route('/roles/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def create_role():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name or Role.query.filter_by(name=name).first():
            flash('Role name is required and must be unique.', 'danger')
            return redirect(url_for('admin.create_role'))

        role = Role(name=name, description=request.form.get('description'), is_active=True)
        db.session.add(role)
        db.session.flush()
        _set_permissions(role, request.form.getlist('permission_ids'))

        log_action('CREATE', 'role', role.id, role.name,
                   new_values={'permissions': [p.name for p in role.permissions]},
                   details=f'Role {name} created')
        db.session.commit()
        flash(f'Role {name} created successfully.', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/role_form.html',
                           permissions=Permission.query.order_by(Permission.name).all(), role=None)


@admin_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_users')
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)

    if request.method == 'POST':
        old_perms = [p.name for p in role.permissions]
        role.description = request.form.get('description')
        role.is_active = request.form.get('is_active') == 'on'
        _set_permissions(role, request.form.getlist('permission_ids'))

        log_action('UPDATE', 'role', role.id, role.name,
                   old_values={'permissions': old_perms},
                   new_values={'permissions': [p.name for p in role.permissions],
                               'is_active': role.is_active},
                   details=f'Role {role.name} permissions updated')
        db.session.commit()
        flash(f'Role {role.name} updated successfully.', 'success')
        return redirect(url_for('admin.roles'))

    return render_template('admin/role_form.html',
                           permissions=Permission.query.order_by(Permission.name).all(), role=role)


# ------------------------------------------------- GENERIC CONFIG HELPERS
def _config_list(model, item_name, create_endpoint, edit_endpoint):
    return render_template(
        'admin/departments.html',
        items=model.query.order_by(model.name).all(),
        item_name=item_name,
        create_url=url_for(create_endpoint),
        edit_endpoint=edit_endpoint,
    )


def _config_create(model, item_name, list_endpoint, entity_type):
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash(f'{item_name} name is required.', 'danger')
            return redirect(request.url)
        if model.query.filter_by(name=name).first():
            flash(f'{item_name} already exists.', 'danger')
            return redirect(request.url)

        item = model(name=name, is_active=True)
        db.session.add(item)
        db.session.flush()
        log_action('CREATE', entity_type, item.id, item.name,
                   new_values={'name': name}, details=f'{item_name} created')
        db.session.commit()
        flash(f'{item_name} created successfully.', 'success')
        return redirect(url_for(list_endpoint))

    return render_template('admin/config_form.html', item=None, item_name=item_name,
                           cancel_url=url_for(list_endpoint))  # <-- This is the key fix



def _config_edit(model, item_id, item_name, list_endpoint, entity_type):
    item = model.query.get_or_404(item_id)

    if request.method == 'POST':
        new_name = (request.form.get('name') or '').strip()
        if not new_name:
            flash(f'{item_name} name is required.', 'danger')
            return redirect(request.url)

        duplicate = model.query.filter(model.name == new_name, model.id != item.id).first()
        if duplicate:
            flash(f'{item_name} name already exists.', 'danger')
            return redirect(request.url)

        old = {'name': item.name, 'is_active': item.is_active}
        item.name = new_name
        item.is_active = request.form.get('is_active') == 'on'

        log_action('UPDATE', entity_type, item.id, item.name,
                   old_values=old,
                   new_values={'name': item.name, 'is_active': item.is_active},
                   details=f'{item_name} updated')
        db.session.commit()
        flash(f'{item_name} updated successfully.', 'success')
        return redirect(url_for(list_endpoint))

    return render_template('admin/config_form.html', item=item, item_name=item_name,
                           cancel_url=url_for(list_endpoint))


# ------------------------------------------------------------ DEPARTMENTS
@admin_bp.route('/departments')
@login_required
@permission_required('manage_config')
def departments():
    return _config_list(Department, 'Department', 'admin.create_department', 'admin.edit_department')


@admin_bp.route('/departments/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def create_department():
    return _config_create(Department, 'Department', 'admin.departments', 'department')


@admin_bp.route('/departments/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_department(item_id):
    return _config_edit(Department, item_id, 'Department', 'admin.departments', 'department')


# --------------------------------------------------------------- SOFTWARE
@admin_bp.route('/software')
@login_required
@permission_required('manage_config')
def software():
    return _config_list(Software, 'Software', 'admin.create_software', 'admin.edit_software')


@admin_bp.route('/software/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def create_software():
    return _config_create(Software, 'Software', 'admin.software', 'software')


@admin_bp.route('/software/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_software(item_id):
    return _config_edit(Software, item_id, 'Software', 'admin.software', 'software')


# ------------------------------------------------------------- CATEGORIES
@admin_bp.route('/categories')
@login_required
@permission_required('manage_config')
def categories():
    return _config_list(Category, 'Category', 'admin.create_category', 'admin.edit_category')


@admin_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def create_category():
    return _config_create(Category, 'Category', 'admin.categories', 'category')


@admin_bp.route('/categories/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_category(item_id):
    return _config_edit(Category, item_id, 'Category', 'admin.categories', 'category')


# ------------------------------------------------------------- PRIORITIES
@admin_bp.route('/priorities')
@login_required
@permission_required('manage_config')
def priorities():
    return render_template('admin/priorities.html',
                           priorities=Priority.query.order_by(Priority.name).all())


@admin_bp.route('/priorities/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def create_priority():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name or Priority.query.filter_by(name=name).first():
            flash('Priority name is required and must be unique.', 'danger')
            return redirect(url_for('admin.create_priority'))
        priority = Priority(name=name, color=request.form.get('color', '#6c757d'), is_active=True)
        db.session.add(priority)
        db.session.flush()
        log_action('CREATE', 'priority', priority.id, priority.name,
                   new_values={'name': name, 'color': priority.color})
        db.session.commit()
        flash('Priority created successfully.', 'success')
        return redirect(url_for('admin.priorities'))
    return render_template('admin/priority_form.html', priority=None)


@admin_bp.route('/priorities/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_priority(item_id):
    priority = Priority.query.get_or_404(item_id)
    if request.method == 'POST':
        new_name = (request.form.get('name') or priority.name).strip()
        if Priority.query.filter(Priority.name == new_name, Priority.id != priority.id).first():
            flash('Priority name already exists.', 'danger')
            return redirect(url_for('admin.edit_priority', item_id=item_id))

        old = {'name': priority.name, 'color': priority.color, 'is_active': priority.is_active}
        priority.name = new_name
        priority.color = request.form.get('color', priority.color)
        priority.is_active = request.form.get('is_active') == 'on'
        log_action('UPDATE', 'priority', priority.id, priority.name, old_values=old,
                   new_values={'name': priority.name, 'color': priority.color,
                               'is_active': priority.is_active})
        db.session.commit()
        flash('Priority updated successfully.', 'success')
        return redirect(url_for('admin.priorities'))
    return render_template('admin/priority_form.html', priority=priority)


# --------------------------------------------------------------- STATUSES
@admin_bp.route('/statuses')
@login_required
@permission_required('manage_config')
def statuses():
    return render_template('admin/statuses.html', statuses=Status.query.order_by(Status.name).all())


@admin_bp.route('/statuses/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_status(item_id):
    status = Status.query.get_or_404(item_id)
    if request.method == 'POST':
        old = {'color': status.color, 'is_active': status.is_active, 'is_closed': status.is_closed}
        status.color = request.form.get('color', status.color)
        status.is_active = request.form.get('is_active') == 'on'
        status.is_closed = request.form.get('is_closed') == 'on'
        log_action('UPDATE', 'status', status.id, status.name, old_values=old,
                   new_values={'color': status.color, 'is_active': status.is_active,
                               'is_closed': status.is_closed})
        db.session.commit()
        flash('Status updated successfully.', 'success')
        return redirect(url_for('admin.statuses'))
    return render_template('admin/status_form.html', status=status)


# ----------------------------------------------------------- SLA POLICIES
@admin_bp.route('/sla-policies')
@login_required
@permission_required('manage_config')
def sla_policies():
    policies = SLAPolicy.query.join(Priority).order_by(Priority.name).all()
    return render_template('admin/sla_policies.html', policies=policies)


@admin_bp.route('/sla-policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_sla_policy(policy_id):
    policy = SLAPolicy.query.get_or_404(policy_id)
    if request.method == 'POST':
        try:
            response_mins = int(request.form.get('response_time_minutes'))
            resolution_mins = int(request.form.get('resolution_time_minutes'))
            if response_mins <= 0 or resolution_mins <= 0:
                raise ValueError
        except (TypeError, ValueError):
            flash('SLA times must be positive whole numbers of minutes.', 'danger')
            return redirect(url_for('admin.edit_sla_policy', policy_id=policy_id))

        old = {'response_time_minutes': policy.response_time_minutes,
               'resolution_time_minutes': policy.resolution_time_minutes,
               'is_active': policy.is_active}
        policy.response_time_minutes = response_mins
        policy.resolution_time_minutes = resolution_mins
        policy.is_active = request.form.get('is_active') == 'on'
        log_action('UPDATE', 'sla_policy', policy.id, policy.priority.name,
                   old_values=old,
                   new_values={'response_time_minutes': response_mins,
                               'resolution_time_minutes': resolution_mins,
                               'is_active': policy.is_active},
                   details='Existing complaint deadlines are not recalculated automatically.')
        db.session.commit()
        flash('SLA policy updated successfully.', 'success')
        return redirect(url_for('admin.sla_policies'))
    return render_template('admin/sla_policy_form.html', policy=policy)


# ------------------------------------------------------- WORKING SCHEDULE
@admin_bp.route('/working-schedule')
@login_required
@permission_required('manage_config')
def working_schedule():
    schedules = WorkingSchedule.query.order_by(WorkingSchedule.day_of_week).all()
    return render_template('admin/working_schedule.html', schedules=schedules, day_names=DAY_NAMES)


@admin_bp.route('/working-schedule/<int:schedule_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_working_schedule(schedule_id):
    schedule = WorkingSchedule.query.get_or_404(schedule_id)
    if request.method == 'POST':
        is_working = request.form.get('is_working_day') == 'on'
        old = {'is_working_day': schedule.is_working_day,
               'start_time': str(schedule.start_time), 'end_time': str(schedule.end_time)}

        if is_working:
            try:
                start = dtime.fromisoformat(request.form.get('start_time'))
                end = dtime.fromisoformat(request.form.get('end_time'))
            except (TypeError, ValueError):
                flash('Valid start and end times are required for a working day.', 'danger')
                return redirect(url_for('admin.edit_working_schedule', schedule_id=schedule_id))
            if start >= end:
                flash('Start time must be earlier than end time.', 'danger')
                return redirect(url_for('admin.edit_working_schedule', schedule_id=schedule_id))
            schedule.start_time, schedule.end_time = start, end

        schedule.is_working_day = is_working
        log_action('UPDATE', 'working_schedule', schedule.id, DAY_NAMES[schedule.day_of_week],
                   old_values=old,
                   new_values={'is_working_day': is_working,
                               'start_time': str(schedule.start_time),
                               'end_time': str(schedule.end_time)})
        db.session.commit()
        flash('Working schedule updated successfully.', 'success')
        return redirect(url_for('admin.working_schedule'))
    return render_template('admin/working_schedule_form.html', schedule=schedule, day_names=DAY_NAMES)


# --------------------------------------------------------------- HOLIDAYS
@admin_bp.route('/holidays')
@login_required
@permission_required('manage_config')
def holidays():
    return render_template('admin/holidays.html',
                           holidays=Holiday.query.order_by(Holiday.date.desc()).all())


@admin_bp.route('/holidays/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def create_holiday():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        try:
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            flash('A valid date is required.', 'danger')
            return redirect(url_for('admin.create_holiday'))
        if not name:
            flash('Holiday name is required.', 'danger')
            return redirect(url_for('admin.create_holiday'))
        if Holiday.query.filter_by(date=date).first():
            flash('A holiday already exists for this date.', 'danger')
            return redirect(url_for('admin.create_holiday'))

        holiday = Holiday(date=date, name=name, is_active=True)
        db.session.add(holiday)
        db.session.flush()
        log_action('CREATE', 'holiday', holiday.id, holiday.name,
                   new_values={'date': str(date), 'name': name})
        db.session.commit()
        flash('Holiday created successfully.', 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_form.html', holiday=None)


@admin_bp.route('/holidays/<int:holiday_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_config')
def edit_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    if request.method == 'POST':
        old = {'name': holiday.name, 'is_active': holiday.is_active, 'date': str(holiday.date)}
        holiday.name = (request.form.get('name') or holiday.name).strip()
        holiday.is_active = request.form.get('is_active') == 'on'
        new_date = request.form.get('date')
        if new_date:
            try:
                parsed = datetime.strptime(new_date, '%Y-%m-%d').date()
                if parsed != holiday.date and Holiday.query.filter_by(date=parsed).first():
                    flash('A holiday already exists for that date.', 'danger')
                    return redirect(url_for('admin.edit_holiday', holiday_id=holiday_id))
                holiday.date = parsed
            except ValueError:
                flash('Invalid date.', 'danger')
                return redirect(url_for('admin.edit_holiday', holiday_id=holiday_id))

        log_action('UPDATE', 'holiday', holiday.id, holiday.name, old_values=old,
                   new_values={'name': holiday.name, 'is_active': holiday.is_active,
                               'date': str(holiday.date)},
                   details='Deactivating a holiday re-includes that date in SLA calculations.')
        db.session.commit()
        flash('Holiday updated successfully.', 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_form.html', holiday=holiday)


# ------------------------------------------------------------- AUDIT LOGS
@admin_bp.route('/audit-logs')
@login_required
@permission_required('view_audit_logs')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action = request.args.get('action') or None
    entity_type = request.args.get('entity_type') or None
    username = request.args.get('username') or None

    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if username:
        query = query.filter(AuditLog.username.ilike(f'%{username}%'))

    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=50, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs,
                           filters={'action': action, 'entity_type': entity_type, 'username': username})