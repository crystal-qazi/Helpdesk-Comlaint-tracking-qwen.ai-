import sys
import os

# Add the project root directory to the Python path so 'app' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Permission, UserProfile,
    Department, Software, Category, Priority, Status,
    SLAPolicy, WorkingSchedule
)
from datetime import time


def seed_data():
    app = create_app()
    with app.app_context():
        # 1. Create Permissions
        permissions_data = [
            ('view_complaints', 'View all complaints'),
            ('create_complaint', 'Create a new complaint'),
            ('assign_complaint', 'Assign or reassign complaints'),
            ('resolve_complaint', 'Resolve complaints'),
            ('close_complaint', 'Close complaints'),
            ('manage_users', 'Manage users and profiles'),
            ('manage_config', 'Manage system configuration'),
            ('view_audit_logs', 'View audit logs'),
            ('export_reports', 'Export reports')
        ]
        
        perms = {}
        for name, desc in permissions_data:
            perm = Permission.query.filter_by(name=name).first()
            if not perm:
                perm = Permission(name=name, description=desc)
                db.session.add(perm)
                print(f"Created permission: {name}")
            perms[name] = perm
            
        # 2. Create Roles and assign permissions
        roles_data = {
            'Admin': ['view_complaints', 'create_complaint', 'assign_complaint', 'resolve_complaint', 'close_complaint', 'manage_users', 'manage_config', 'view_audit_logs', 'export_reports'],
            'Agent': ['view_complaints', 'create_complaint', 'assign_complaint', 'resolve_complaint', 'close_complaint', 'export_reports'],
            'Call Intake User': ['view_complaints', 'create_complaint', 'assign_complaint'],
            'Software Engineer': ['view_complaints', 'create_complaint', 'resolve_complaint', 'export_reports'],
            'Internal Employee': ['create_complaint']
        }
        
        roles = {}
        for role_name, perm_names in roles_data.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, description=f"{role_name} role")
                db.session.add(role)
                print(f"Created role: {role_name}")
            roles[role_name] = role
            
            for perm_name in perm_names:
                if perms[perm_name] not in role.permissions:
                    role.permissions.append(perms[perm_name])
                    
        # 3. Create Admin User
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@hospital.local', is_active=True)
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.flush()
            
            profile = UserProfile(user_id=admin.id, full_name='System Administrator', employee_number='EMP000')
            db.session.add(profile)
            admin.roles.append(roles['Admin'])
            print("Created admin user (username: admin, password: Admin@123)")
            
        # 4. Seed Configuration Data
        depts = ['Lab', 'Radiology', 'Pharmacy', 'HIS', 'ERP', 'EMR', 'Network', 'Infrastructure']
        for d in depts:
            if not Department.query.filter_by(name=d).first():
                db.session.add(Department(name=d))
                
        softwares = ['Hospital Information System', 'Electronic Medical Record', 'Laboratory Information System', 
                     'Radiology Information System', 'Pharmacy System', 'ERP System']
        for s in softwares:
            if not Software.query.filter_by(name=s).first():
                db.session.add(Software(name=s))
                
        cats = ['Login Issue', 'Performance', 'Data Error', 'Feature Request', 'Hardware/Software Integration']
        for c in cats:
            if not Category.query.filter_by(name=c).first():
                db.session.add(Category(name=c))
                
        priorities = [('Critical', '#dc3545'), ('High', '#fd7e14'), ('Medium', '#ffc107'), ('Low', '#28a745')]
        for name, color in priorities:
            if not Priority.query.filter_by(name=name).first():
                db.session.add(Priority(name=name, color=color))
                
        statuses = [
            ('New', '#007bff', False), 
            ('Assigned', '#17a2b8', False), 
            ('In Progress', '#ffc107', False), 
            ('Pending Information', '#6c757d', False), 
            ('On Hold', '#6f42c1', False),
            ('Resolved', '#28a745', False), 
            ('Closed', '#343a40', True), 
            ('Rejected', '#dc3545', True)
        ]
        for name, color, is_closed in statuses:
            if not Status.query.filter_by(name=name).first():
                db.session.add(Status(name=name, color=color, is_closed=is_closed))

        # 5. Seed Working Schedule (Monday to Friday, 8:00 AM to 5:00 PM)
        for day in range(5):  # 0=Monday to 4=Friday
            if not WorkingSchedule.query.filter_by(day_of_week=day).first():
                db.session.add(WorkingSchedule(
                    day_of_week=day,
                    start_time=time(8, 0),
                    end_time=time(17, 0),
                    is_working_day=True
                ))
        for day in [5, 6]:  # Saturday=5, Sunday=6
            if not WorkingSchedule.query.filter_by(day_of_week=day).first():
                db.session.add(WorkingSchedule(
                    day_of_week=day,
                    is_working_day=False
                ))

        # 6. Seed SLA Policies (Global)
        sla_data = [
            ('Critical', 15, 120),    # 15 mins response, 2 hours resolution
            ('High', 30, 480),        # 30 mins response, 8 hours resolution
            ('Medium', 120, 1440),    # 2 hours response, 24 hours resolution
            ('Low', 240, 4320)        # 4 hours response, 72 hours resolution
        ]
        
        for priority_name, response_mins, resolution_mins in sla_data:
            priority = Priority.query.filter_by(name=priority_name).first()
            if priority and not SLAPolicy.query.filter_by(priority_id=priority.id, department_id=None).first():
                db.session.add(SLAPolicy(
                    priority_id=priority.id,
                    response_time_minutes=response_mins,
                    resolution_time_minutes=resolution_mins
                ))
                print(f"Created SLA policy for {priority_name}")
            
        db.session.commit()
        print("\n✅ Database seeded successfully!")


if __name__ == '__main__':
    seed_data()