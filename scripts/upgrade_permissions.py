import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import Role, Permission

NEW_PERMISSIONS = [
    ('view_own_complaints', 'View own reported/created/assigned complaints'),
    ('add_internal_comment', 'Add internal (IT-only) comments'),
    ('add_reporter_comment', 'Add reporter-visible comments'),
    ('change_status', 'Change complaint technical status'),
    ('reject_complaint', 'Reject complaints'),
    ('reopen_complaint', 'Reopen resolved/closed complaints'),
    ('edit_complaint', 'Edit complaint details'),
]

ROLE_GRANTS = {
    'Admin': [p[0] for p in NEW_PERMISSIONS],
    'Agent': ['view_own_complaints', 'add_internal_comment', 'add_reporter_comment',
              'change_status', 'reject_complaint', 'reopen_complaint', 'edit_complaint'],
    'Call Intake User': ['view_own_complaints', 'add_internal_comment',
                         'add_reporter_comment', 'edit_complaint'],
    'Software Engineer': ['view_own_complaints', 'add_internal_comment',
                          'add_reporter_comment', 'change_status', 'reopen_complaint'],
    'Internal Employee': ['view_own_complaints', 'add_reporter_comment'],
}


def run():
    app = create_app()
    with app.app_context():
        perms = {}
        for name, desc in NEW_PERMISSIONS:
            perm = Permission.query.filter_by(name=name).first()
            if not perm:
                perm = Permission(name=name, description=desc)
                db.session.add(perm)
                print(f'Created permission: {name}')
            perms[name] = perm
        db.session.flush()

        for role_name, perm_names in ROLE_GRANTS.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                print(f'⚠️ Role not found, skipped: {role_name}')
                continue
            for pname in perm_names:
                if perms[pname] not in role.permissions:
                    role.permissions.append(perms[pname])
            print(f'Updated role: {role_name}')

        db.session.commit()
        print('\n✅ Permission upgrade complete.')


if __name__ == '__main__':
    run()