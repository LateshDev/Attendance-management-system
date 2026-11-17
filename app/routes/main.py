from datetime import datetime
from flask import Blueprint, redirect, url_for, render_template, flash, request
from flask_login import login_required, current_user
from app.models import db, Notification, ClassGroup, TimetableVersion, Timetable, Holiday

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'hod':
        return redirect(url_for('hod.dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('teacher.dashboard'))
    elif current_user.role == 'student':
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    # Mark all read
    for n in user_notifications:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=user_notifications)


@main_bp.route('/timetable/view/<int:class_id>')
@login_required
def view_timetable(class_id):
    cls = ClassGroup.query.get_or_404(class_id)
    version = TimetableVersion.query.filter_by(class_id=class_id, is_active=True).first()
    
    slots_by_day = {
        "Monday": {}, "Tuesday": {}, "Wednesday": {}, "Thursday": {}, "Friday": {}, "Saturday": {}
    }
    
    if version:
        slots = Timetable.query.filter_by(version_id=version.id).all()
        for s in slots:
            slots_by_day[s.day_of_week][s.period_number] = s

    periods = [
        (1, "09:00 - 10:00 AM"),
        (2, "10:00 - 11:00 AM"),
        (3, "11:20 - 12:20 PM"),
        (4, "12:20 - 01:20 PM"),
        (5, "02:00 - 03:00 PM")
    ]

    return render_template('timetable_view.html', cls=cls, version=version, slots_by_day=slots_by_day, periods=periods)

