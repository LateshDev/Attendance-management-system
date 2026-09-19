from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date, timedelta
from sqlalchemy import func

from app.models import db, User, Batch, Student, Subject, AttendanceSession, AttendanceRecord, Setting, Role

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()

    # Scope batches if user is teacher
    if current_user.is_teacher:
        batches_query = Batch.query.filter_by(teacher_id=current_user.id, status='Active')
    else:
        batches_query = Batch.query.filter_by(status='Active')

    active_batches = batches_query.order_by(Batch.batch_name).all()
    batch_ids = [b.id for b in active_batches]

    total_batches = len(active_batches)
    total_teachers = User.query.join(Role).filter(Role.name == 'TEACHER', User.is_active == True).count()
    
    if current_user.is_teacher:
        # Count unique students enrolled in teacher's batches
        from app.models import BatchStudent
        total_students = Student.query.join(BatchStudent).filter(
            BatchStudent.batch_id.in_(batch_ids) if batch_ids else False,
            BatchStudent.status == 'Active',
            Student.status == 'Active'
        ).distinct().count()
    else:
        total_students = Student.query.filter_by(status='Active').count()

    # Today's attendance sessions
    today_sessions_query = AttendanceSession.query.filter(AttendanceSession.session_date == today)
    if current_user.is_teacher and batch_ids:
        today_sessions_query = today_sessions_query.filter(AttendanceSession.batch_id.in_(batch_ids))

    today_sessions = today_sessions_query.all()
    today_session_ids = [s.id for s in today_sessions]

    today_present = 0
    today_absent = 0
    today_leave = 0

    if today_session_ids:
        records = AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(today_session_ids)).all()
        today_present = sum(1 for r in records if r.status == 'Present')
        today_absent = sum(1 for r in records if r.status == 'Absent')
        today_leave = sum(1 for r in records if r.status == 'Leave')

    total_marked_today = today_present + today_absent + today_leave
    overall_percentage_today = round((today_present / total_marked_today) * 100.0, 1) if total_marked_today > 0 else 0.0

    # Batch-wise detailed statistics for today and overall
    batch_stats = []
    for b in active_batches:
        students_count = b.active_students_count
        # Today's session for this batch
        b_session = next((s for s in today_sessions if s.batch_id == b.id), None)
        if b_session:
            b_present = b_session.present_count
            b_absent = b_session.absent_count
            b_leave = b_session.leave_count
            b_pct = b_session.attendance_percentage
            is_marked_today = True
        else:
            b_present = 0
            b_absent = 0
            b_leave = 0
            b_pct = 0.0
            is_marked_today = False

        batch_stats.append({
            'batch': b,
            'students_count': students_count,
            'present': b_present,
            'absent': b_absent,
            'leave': b_leave,
            'percentage': b_pct,
            'is_marked_today': is_marked_today
        })

    # Recent 5 sessions
    recent_sessions_query = AttendanceSession.query
    if current_user.is_teacher and batch_ids:
        recent_sessions_query = recent_sessions_query.filter(AttendanceSession.batch_id.in_(batch_ids))
    recent_sessions = recent_sessions_query.order_by(AttendanceSession.session_date.desc(), AttendanceSession.id.desc()).limit(5).all()

    # 7-day attendance trend data for Chart.js
    trend_labels = []
    trend_present = []
    trend_absent = []
    trend_leave = []

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        trend_labels.append(d.strftime("%b %d"))

        d_query = AttendanceRecord.query.join(AttendanceSession).filter(AttendanceSession.session_date == d)
        if current_user.is_teacher and batch_ids:
            d_query = d_query.filter(AttendanceSession.batch_id.in_(batch_ids))

        day_records = d_query.all()
        p = sum(1 for r in day_records if r.status == 'Present')
        a = sum(1 for r in day_records if r.status == 'Absent')
        l = sum(1 for r in day_records if r.status == 'Leave')

        trend_present.append(p)
        trend_absent.append(a)
        trend_leave.append(l)

    # Low attendance students alert (overall threshold)
    threshold = float(Setting.get_value('low_attendance_threshold', 75.0))
    low_attendance_students = []

    # Get sample students with low attendance
    all_active_students = Student.query.filter_by(status='Active').all()
    for st in all_active_students:
        stats = st.calculate_attendance_stats()
        if stats['total_classes'] >= 3 and stats['percentage'] < threshold:
            low_attendance_students.append({
                'student': st,
                'stats': stats
            })

    # Sort lowest percentage first and take top 5
    low_attendance_students.sort(key=lambda x: x['stats']['percentage'])
    low_attendance_students = low_attendance_students[:5]

    return render_template(
        'dashboard.html',
        total_batches=total_batches,
        total_students=total_students,
        total_teachers=total_teachers,
        today=today,
        today_sessions_count=len(today_sessions),
        today_present=today_present,
        today_absent=today_absent,
        today_leave=today_leave,
        total_marked_today=total_marked_today,
        overall_percentage_today=overall_percentage_today,
        batch_stats=batch_stats,
        recent_sessions=recent_sessions,
        trend_labels=trend_labels,
        trend_present=trend_present,
        trend_absent=trend_absent,
        trend_leave=trend_leave,
        low_attendance_students=low_attendance_students,
        threshold=threshold
    )
