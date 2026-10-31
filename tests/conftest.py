import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db as _db
from app.models import (User, Role, Permission, Department, Software, Priority, Status, Complaint)

PERMISSIONS = [
    'view_complaints', 'view_own_complaints', 'create_complaint', 'assign_complaint',
    'resolve_complaint', 'close_complaint', 'reject_complaint', 'change_status',
    'add_internal_comment', 'add_reporter_comment', 'manage_users', 'manage_config',
    'view_audit_logs', 'export_reports',
]

ROLE_MAP = {
    'Admin': PERMISSIONS,
    'Agent': ['view_complaints', 'view_own_complaints', 'create_complaint', 'assign_complaint',
              'resolve_complaint', 'close_complaint', 'change_status',
              'add_internal_comment', 'add_reporter_comment', 'export_reports'],
    'Internal Employee': ['view_own_complaints', 'create_complaint', 'add_reporter_comment'],
}


def _seed():
    perms = {}
    for name in PERMISSIONS:
        p = Permission(name=name, description=name)
        _db.session.add(p)
        perms[name] = p

    roles = {}
    for role_name, perm_names in ROLE_MAP.items():
        role = Role(name=role_name, is_active=True)
        role.permissions = [perms[p] for p in perm_names]
        _db.session.add(role)
        roles[role_name] = role

    for name in ['New', 'Assigned', 'In Progress', 'Pending Information',
                 'On Hold', 'Resolved', 'Closed', 'Rejected']:
        _db.session.add(Status(name=name, is_active=True, is_closed=name in ('Closed', 'Rejected')))

    dept = Department(name='HIS', is_active=True)
    sw = Software(name='Hospital Information System', is_active=True)
    prio = Priority(name='Critical', color='#dc3545', is_active=True)
    _db.session.add_all([dept, sw, prio])
    _db.session.flush()

    users = {}
    for username, role_name in [('admin', 'Admin'), ('agent', 'Agent'),
                                ('emp1', 'Internal Employee'), ('emp2', 'Internal Employee'),
                                ('inactive', 'Agent')]:
        u = User(username=username, email=f'{username}@test.local', is_active=(username != 'inactive'))
        u.set_password('TestPass@123')
        u.roles.append(roles[role_name])
        _db.session.add(u)
        users[username] = u

    _db.session.commit()
    return {'dept': dept, 'sw': sw, 'prio': prio, 'users': users}


@pytest.fixture
def app():
    application = create_app('testing')
    with application.app_context():
        _db.create_all()
        refs = _seed()
        application.test_refs = refs
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def refs(app):
    return app.test_refs


def login(client, username, password='TestPass@123'):
    return client.post('/login', data={'username': username, 'password': password},
                       follow_redirects=False)


def make_complaint(app, reporter='emp1', creator='agent'):
    refs = app.test_refs
    status = Status.query.filter_by(name='New').first()
    c = Complaint(
        complaint_number='ITC-TEST-000001',
        title='Test complaint',
        description='Test description',
        department_id=refs['dept'].id,
        software_id=refs['sw'].id,
        priority_id=refs['prio'].id,
        status_id=status.id,
        reported_by_user_id=refs['users'][reporter].id,
        created_by_user_id=refs['users'][creator].id,
    )
    _db.session.add(c)
    _db.session.commit()
    return c