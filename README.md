# Helpdesk Complaint Tracking System

A Flask-based complaint and helpdesk management application for tracking service issues, incidents, and customer complaints across departments, teams, and SLA commitments.

This project is designed for operational support environments such as hospitals, service desks, or internal IT support teams. It includes complaint intake, assignment, lifecycle tracking, SLA enforcement, notifications, reports, audit logs, and configurable admin management.

## Features

- Complaint registration with auto-generated complaint numbers
- Department, software, category, priority, and status tracking
- Complaint assignment and reassignment workflow
- SLA response and resolution deadline tracking
- Pause/resume logic for SLA while complaint is pending information or on hold
- Status history and audit trail
- Role-based access control and granular permissions
- User management and password security
- Notifications for assignments, status updates, comments, and resolution
- File attachments and document uploads
- Dashboard with KPIs and charts
- Reporting module for complaints, SLA compliance, overdue items, and grouped summaries
- Admin configuration for departments, software, priorities, statuses, holidays, working schedules, and SLA policies

## Tech Stack

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-WTF
- MySQL (default database)
- Jinja2 templates
- Alembic migrations
- ReportLab for report generation

## Project Structure

```text
.
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── middleware/
│   ├── models/
│   ├── permissions/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── templates/
│   └── validators/
├── migrations/
├── scripts/
├── tests/
├── uploads/
├── logs/
├── .gitignore
├── README.md
├── requirements.txt
├── run.py
├── run_prod.py
├── fix_structure.py
└── bandit_report.txt
```

## Main Modules

### App Initialization
- `run.py`: start the app
- `app/__init__.py`: initialize Flask, DB, login manager, CSRF, and route blueprints
- `app/config.py`: application configuration, security settings, and database configuration

### Models
The app models include:
- `Complaint`
- `User`
- `Role` / `Permission`
- `Department`
- `Software`
- `Category`
- `Priority`
- `Status`
- `SLAPolicy`
- `Notification`
- `AuditLog`
- `Attachment`
- `Comment`

### Routes
- `app/routes/auth.py`: login, logout, password change
- `app/routes/dashboard.py`: dashboard metrics and charts
- `app/routes/complaints.py`: complaint lifecycle and actions
- `app/routes/notifications.py`: notification views
- `app/routes/reports.py`: reports and summaries
- `app/routes/admin.py`: admin and configuration screens

### Services
- `auth_service.py`: login attempt lockouts and auth helpers
- `complaint_service.py`: complaint numbering and related logic
- `sla_service.py`: SLA calculation and enforcement
- `notification_service.py`: assignment and update notifications
- `report_service.py`: reporting utilities
- `audit_service.py`: audit logging
- `file_service.py`: attachment storage and validation

## Setup

### Prerequisites

- Python 3.10+
- MySQL server
- Virtual environment tool such as `venv` or `virtualenv`

### 1. Clone the repository

```bash
git clone https://github.com/crystal-qazi/Helpdesk-Comlaint-tracking-qwen.ai-.git
cd Helpdesk-Comlaint-tracking-qwen.ai-
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
# or
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root if needed.

Example:

```env
FLASK_ENV=development
SECRET_KEY=change-me-to-a-strong-secret
DATABASE_URL=mysql+pymysql://root:root@localhost/hospital_complaints?charset=utf8mb4
UPLOAD_FOLDER=./uploads
```

The default app configuration in `app/config.py` expects a MySQL database named `hospital_complaints` unless overridden.

### 5. Create the database

Make sure your MySQL server is running and the target database exists.

```sql
CREATE DATABASE hospital_complaints;
```

### 6. Run database migrations

```bash
flask db upgrade
```

If Flask CLI is not configured in your environment, use the app entrypoint and ensure migrations are initialized properly.

### 7. Start the app

```bash
python run.py
```

The application runs by default on:

```text
http://localhost:5000
```

## Default Login

This project includes authentication flow and access control. You will need to create an admin user or seed data before login.

Useful scripts include:
- `scripts/seed_data.py`
- `scripts/set_password.py`
- `scripts/upgrade_permissions.py`

## Typical Workflow

1. Create a user with appropriate permissions
2. Configure departments, software, priorities, and statuses
3. Log in to the application
4. Register a complaint
5. Assign the complaint to a team member
6. Update status as work progresses
7. Track SLA deadlines and notifications
8. Resolve or close the complaint
9. Review dashboard and reporting metrics

## Notes

- The project uses `uploads/` for complaint attachments.
- `logs/` stores application logs.
- `migrations/` contains schema change scripts for the database.
- The application supports production and testing configuration modes via `app/config.py`.

## Security Notes

The project includes a number of security controls, including:
- login throttling
- session hardening options
- CSRF protection
- security headers
- role-based authorization checks
- safe redirect validation

## License

This project does not currently declare a formal license in the repository. Please check the repository status before using it in production or redistribution.

## Contribution

This project appears to be an internal support/complaint-tracking platform and is not yet fully documented for public contribution workflows. If you are using or extending it, add migrations and test coverage for any schema or logic changes.

## Summary

This repository implements a complaint management and SLA-tracking system built with Flask. It is structured as a practical business application with a dashboard, admin configuration, role-based access, reporting, and operational workflow management.

For detailed runtime behavior, inspect the route modules and services in `app/routes/` and `app/services/`.
