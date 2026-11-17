from datetime import date, datetime, time
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (
    db, Teacher, Subject, ClassGroup, Timetable, TimetableVersion,
    AttendanceSession, Attendance, Student, CorrectionRequest, AttendanceLog, Notification, Holiday
)
from app.routes.auth import teacher_required

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.before_request
@login_required
@teacher_required
def check_teacher():
    pass

@teacher_bp.route('/dashboard')
def dashboard():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher and current_user.role == 'admin':
        # Default to first teacher for admin previewing teacher dashboard
        teacher = Teacher.query.first()
    
    if not teacher:
        flash("Teacher profile not found.", "warning")
        return redirect(url_for('main.index'))

    # Determine today's day of week
    today = date.today()
    day_name = today.strftime('%A')

    # Get active timetable slots for this teacher today
    today_slots = Timetable.query.join(TimetableVersion).filter(
        TimetableVersion.is_active == True,
        Timetable.teacher_id == teacher.id,
        Timetable.day_of_week == day_name
    ).order_by(Timetable.period_number).all()

    # Check which slots have already been marked today
    marked_session_map = {}
    for slot in today_slots:
        sess = AttendanceSession.query.filter_by(
            class_id=slot.class_id,
            subject_id=slot.subject_id,
            session_date=today,
            period_number=slot.period_number
        ).first()
        if sess:
            marked_session_map[slot.id] = sess

    # Assigned subjects & classes
    assigned_allocations = teacher.assigned_subjects.all()

    # Pending correction requests assigned to this teacher
    pending_corrections = CorrectionRequest.query.filter_by(
        teacher_id=teacher.id,
        teacher_status='Pending'
    ).order_by(CorrectionRequest.created_at.desc()).all()

    # Recent sessions
    recent_sessions = AttendanceSession.query.filter_by(
        teacher_id=teacher.id
    ).order_by(AttendanceSession.session_date.desc(), AttendanceSession.period_number.desc()).limit(10).all()

    return render_template(
        'teacher/dashboard.html',
        teacher=teacher,
        today=today,
        day_name=day_name,
        today_slots=today_slots,
        marked_session_map=marked_session_map,
        assigned_allocations=assigned_allocations,
        pending_corrections=pending_corrections,
        recent_sessions=recent_sessions
    )


@teacher_bp.route('/mark/<int:slot_id>', methods=['GET', 'POST'])
def mark_attendance(slot_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    slot = Timetable.query.get_or_404(slot_id)

    # Allow assigned teacher or admin
    if teacher and slot.teacher_id != teacher.id and current_user.role != 'admin':
        flash("You can only mark attendance for your assigned timetable lectures.", "danger")
        return redirect(url_for('teacher.dashboard'))

    today = date.today()
    session_date = today

    # Check for holidays
    holiday = Holiday.query.filter(
        Holiday.start_date <= session_date,
        Holiday.end_date >= session_date
    ).first()
    if holiday:
        flash(f"Notice: Today is marked as a college holiday ({holiday.name}). Ensure this is authorized.", "warning")

    # Check if duplicate session exists
    existing_session = AttendanceSession.query.filter_by(
        class_id=slot.class_id,
        subject_id=slot.subject_id,
        session_date=session_date,
        period_number=slot.period_number
    ).first()

    students = Student.query.filter_by(class_id=slot.class_id).order_by(Student.roll_number).all()

    if request.method == 'POST':
        topic = request.form.get('topic_covered', '').strip()

        if existing_session:
            flash("Attendance has already been marked for this lecture. You can view or submit correction requests.", "warning")
            return redirect(url_for('teacher.view_session', session_id=existing_session.id))

        # Create new session
        new_session = AttendanceSession(
            timetable_id=slot.id,
            class_id=slot.class_id,
            subject_id=slot.subject_id,
            teacher_id=slot.teacher_id,
            session_date=session_date,
            period_number=slot.period_number,
            start_time=slot.start_time,
            end_time=slot.end_time,
            status="Closed",
            topic_covered=topic
        )
        db.session.add(new_session)
        db.session.flush()

        # Record attendance for each student
        for s in students:
            status = request.form.get(f'status_{s.id}', 'Present')
            remarks = request.form.get(f'remarks_{s.id}', '')
            
            rec = Attendance(
                session_id=new_session.id,
                student_id=s.id,
                status=status,
                remarks=remarks,
                marked_by=current_user.id
            )
            db.session.add(rec)

        db.session.commit()
        flash("Attendance successfully recorded and locked!", "success")
        return redirect(url_for('teacher.view_session', session_id=new_session.id))

    return render_template(
        'teacher/mark_attendance.html',
        slot=slot,
        students=students,
        existing_session=existing_session,
        session_date=session_date
    )


@teacher_bp.route('/session/<int:session_id>')
def view_session(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    records = Attendance.query.filter_by(session_id=session.id).join(Student).order_by(Student.roll_number).all()
    
    total = len(records)
    present_count = sum(1 for r in records if r.status in ['Present', 'Late'])
    absent_count = sum(1 for r in records if r.status == 'Absent')
    leave_count = sum(1 for r in records if r.status == 'Leave')

    return render_template(
        'teacher/view_session.html',
        session=session,
        records=records,
        total=total,
        present_count=present_count,
        absent_count=absent_count,
        leave_count=leave_count
    )


@teacher_bp.route('/corrections')
def corrections():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher and current_user.role == 'admin':
        requests = CorrectionRequest.query.order_by(CorrectionRequest.created_at.desc()).all()
    else:
        requests = CorrectionRequest.query.filter_by(teacher_id=teacher.id).order_by(CorrectionRequest.created_at.desc()).all()
    
    return render_template('teacher/corrections.html', requests=requests)


@teacher_bp.route('/verify-correction/<int:req_id>', methods=['POST'])
def verify_correction(req_id):
    corr = CorrectionRequest.query.get_or_404(req_id)
    action = request.form.get('action')  # 'verify' or 'reject'
    remarks = request.form.get('teacher_remarks', '').strip()

    if action == 'verify':
        corr.teacher_status = 'Verified'
        corr.teacher_remarks = remarks
        corr.teacher_verified_at = datetime.utcnow()
        flash("Correction verified and forwarded to HOD for final approval.", "success")
    elif action == 'reject':
        corr.teacher_status = 'Rejected'
        corr.teacher_remarks = remarks
        corr.teacher_verified_at = datetime.utcnow()
        corr.resolved_at = datetime.utcnow()
        flash("Correction request rejected by teacher.", "info")

        # Notify student
        notif = Notification(
            user_id=corr.student.user_id,
            title="Attendance Correction Update",
            message=f"Your request for {corr.session.subject.name} on {corr.old_date} was rejected by teacher: {remarks}",
            type="warning"
        )
        db.session.add(notif)

    db.session.commit()
    return redirect(url_for('teacher.corrections'))

