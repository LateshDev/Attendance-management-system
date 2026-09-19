from flask import request
from flask_login import current_user
from app.models import db, AuditLog


def log_action(action, module, record_id=None, old_value=None, new_value=None):
    """
    Helper function to record system audit entries.
    Handles user ID, client IP address, and change details.
    """
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        
        # Determine IP address safely
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            record_id=str(record_id) if record_id else None,
            old_value=str(old_value) if old_value else None,
            new_value=str(new_value) if new_value else None,
            ip_address=ip
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        # Never let logging failure break application flow
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Failed to write audit log: {e}")
