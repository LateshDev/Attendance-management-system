from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def admin_required(f):
    """Decorator to enforce Admin-only access on routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            flash("Access denied: Administrative privileges required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def teacher_or_admin_required(f):
    """Decorator to allow both Teachers and Admins."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        if not (current_user.is_admin or current_user.is_teacher):
            flash("Access denied: Staff authorization required.", "danger")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def check_batch_access(batch, user):
    """Verify if user has permission to view or mark attendance for a batch."""
    if user.is_admin:
        return True
    if user.is_teacher and batch.teacher_id == user.id:
        return True
    # Also check if teacher teaches any subject in this batch
    from app.models import BatchSubject
    is_subject_teacher = BatchSubject.query.filter_by(batch_id=batch.id, teacher_id=user.id).first() is not None
    return is_subject_teacher
