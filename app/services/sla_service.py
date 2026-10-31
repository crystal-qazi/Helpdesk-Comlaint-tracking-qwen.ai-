from datetime import datetime, timedelta, time
from ..models import WorkingSchedule, Holiday, SLAPolicy

def get_working_schedule(day_of_week):
    """Returns (is_working_day, start_time, end_time) for a given day (0=Mon, 6=Sun)."""
    schedule = WorkingSchedule.query.filter_by(day_of_week=day_of_week).first()
    if not schedule or not schedule.is_working_day:
        return False, None, None
    return True, schedule.start_time, schedule.end_time

def is_holiday(check_date):
    """Checks if a specific date is a holiday."""
    return Holiday.query.filter_by(date=check_date, is_active=True).first() is not None

def get_next_working_day_start(current_datetime):
    """Finds the start of the next valid working day."""
    check_date = current_datetime.date() + timedelta(days=1)
    while True:
        is_working, start_time, end_time = get_working_schedule(check_date.weekday())
        if is_working and not is_holiday(check_date):
            return datetime.combine(check_date, start_time)
        check_date += timedelta(days=1)

def calculate_sla_deadline(start_time, minutes_to_add):
    """
    Calculates a deadline by adding business minutes to a start time.
    Ignores weekends, holidays, and outside working hours.
    """
    if minutes_to_add <= 0:
        return start_time
        
    current_time = start_time
    
    # 1. Normalize start time to be within working hours
    while True:
        is_working, start_time_of_day, end_time_of_day = get_working_schedule(current_time.weekday())
        
        if not is_working or is_holiday(current_time.date()):
            current_time = get_next_working_day_start(current_time - timedelta(days=1))
            continue
            
        if current_time.time() < start_time_of_day:
            current_time = datetime.combine(current_time.date(), start_time_of_day)
            
        if current_time.time() >= end_time_of_day:
            current_time = get_next_working_day_start(current_time)
            continue
            
        break # We are now inside valid working hours

    # 2. Add the minutes
    remaining_minutes = minutes_to_add
    
    while remaining_minutes > 0:
        is_working, start_time_of_day, end_time_of_day = get_working_schedule(current_time.weekday())
        end_of_day = datetime.combine(current_time.date(), end_time_of_day)
        
        minutes_until_end = (end_of_day - current_time).total_seconds() / 60
        
        if remaining_minutes <= minutes_until_end:
            current_time += timedelta(minutes=remaining_minutes)
            remaining_minutes = 0
        else:
            remaining_minutes -= minutes_until_end
            current_time = get_next_working_day_start(current_time)
            
    return current_time

def get_applicable_sla_policy(priority_id, department_id=None):
    """Finds the most specific SLA policy (Department-specific first, then Global)."""
    if department_id:
        policy = SLAPolicy.query.filter_by(
            priority_id=priority_id, 
            department_id=department_id, 
            is_active=True
        ).first()
        if policy:
            return policy
            
    # Fallback to global policy for this priority
    return SLAPolicy.query.filter_by(
        priority_id=priority_id, 
        department_id=None, 
        is_active=True
    ).first()

def calculate_initial_sla(complaint):
    """Calculates and sets initial SLA deadlines for a new complaint."""
    policy = get_applicable_sla_policy(complaint.priority_id, complaint.department_id)
    if not policy:
        return None, None
        
    start_time = complaint.created_at
    response_deadline = calculate_sla_deadline(start_time, policy.response_time_minutes)
    resolution_deadline = calculate_sla_deadline(start_time, policy.resolution_time_minutes)
    
    return response_deadline, resolution_deadline