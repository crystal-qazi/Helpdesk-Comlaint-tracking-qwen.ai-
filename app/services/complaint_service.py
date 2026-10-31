from ..extensions import db
from ..models import ComplaintSequence, Complaint, Status
from datetime import datetime

def generate_complaint_number():
    """Generates a unique complaint number like ITC-2026-000001 safely."""
    current_year = datetime.utcnow().year
    
    # Lock the row for this year to prevent race conditions
    seq = ComplaintSequence.query.filter_by(year=current_year).with_for_update().first()
    
    if not seq:
        seq = ComplaintSequence(year=current_year, current_number=1)
        db.session.add(seq)
    else:
        seq.current_number += 1
        
    # Flush to ensure it's saved before we format the string
    db.session.flush()
    
    return f"ITC-{current_year}-{seq.current_number:06d}"