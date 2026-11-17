from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (
    db, Student, Attendance, AttendanceSession, Subject, Timetable,
    TimetableVersion, CorrectionRequest, LeaveApplication, Notification, Holiday
)
from app.routes.auth import student_required

student_bp = Blueprint('student', __name__)

@student_bp.before_request
@login_required
@student_required
def check_student():
    pass

@student_bp.route('/dashboard')
def dashboard():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Calculate Subject-wise & Overall Attendance
    # Total conducted sessions for this class
    all_class_sessions = AttendanceSession.query.filter_by(class_id=student.class_id).all()
    session_ids = [s.id for s in all_class_sessions]

    # Student's attendance records
    student_records = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.session_id.in_(session_ids) if session_ids else False
    ).all()

    total_conducted = len(student_records)
    # Attended = Present or Late
    total_attended = sum(1 for r in student_records if r.status in ['Present', 'Late'])
    overall_percentage = round((total_attended / total_conducted * 100), 1) if total_conducted > 0 else 100.0

    # Low attendance alert
    is_defaulter = overall_percentage < 75.0 and total_conducted >= 5

    # Subject-wise calculation
    subjects = Subject.query.filter_by(course_id=student.class_group.course_id, semester=student.semester).all()
    subject_stats = []

    for sub in subjects:
        sub_sessions = [s.id for s in all_class_sessions if s.subject_id == sub.id]
        if sub_sessions:
            sub_records = [r for r in student_records if r.session_id in sub_sessions]
            conducted = len(sub_records)
            attended = sum(1 for r in sub_records if r.status in ['Present', 'Late'])
            pct = round((attended / conducted * 100), 1) if conducted > 0 else 0.0
            subject_stats.append({
                'subject': sub,
                'conducted': conducted,
                'attended': attended,
                'absent': conducted - attended,
                'percentage': pct,
                'is_low': pct < 75.0 and conducted > 0
            })

    # Today's timetable
    today = date.today()
    day_name = today.strftime('%A')
    today_slots = Timetable.query.join(TimetableVersion).filter(
        TimetableVersion.is_active == True,
        Timetable.class_id == student.class_id,
        Timetable.day_of_week == day_name
    ).order_by(Timetable.period_number).all()

    # Recent attendance logs for student
    recent_records = Attendance.query.filter_by(student_id=student.id).join(AttendanceSession).order_by(
        AttendanceSession.session_date.desc(), AttendanceSession.period_number.desc()
    ).limit(10).all()

    # Active correction requests
    my_corrections = CorrectionRequest.query.filter_by(student_id=student.id).order_by(CorrectionRequest.created_at.desc()).limit(5).all()

    return render_template(
        'student/dashboard.html',
        student=student,
        total_conducted=total_conducted,
        total_attended=total_attended,
        overall_percentage=overall_percentage,
        is_defaulter=is_defaulter,
        subject_stats=subject_stats,
        today=today,
        day_name=day_name,
        today_slots=today_slots,
        recent_records=recent_records,
        my_corrections=my_corrections
    )


@student_bp.route('/history')
def history():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Filters
    subject_id = request.args.get('subject_id', type=int)
    status_filter = request.args.get('status')

    query = Attendance.query.filter_by(student_id=student.id).join(AttendanceSession)
    
    if subject_id:
        query = query.filter(AttendanceSession.subject_id == subject_id)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)

    records = query.order_by(AttendanceSession.session_date.desc(), AttendanceSession.period_number.desc()).all()
    subjects = Subject.query.filter_by(course_id=student.class_group.course_id, semester=student.semester).all()

    return render_template('student/history.html', student=student, records=records, subjects=subjects, selected_subject=subject_id, selected_status=status_filter)


@student_bp.route('/request-correction', methods=['GET', 'POST'])
def request_correction():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        attendance_id = request.form.get('attendance_id', type=int)
        requested_status = request.form.get('new_status')
        new_date_str = request.form.get('new_date')
        reason = request.form.get('reason', '').strip()

        att = Attendance.query.get_or_404(attendance_id)
        if att.student_id != student.id:
            flash("Unauthorized: You can only request correction for your own attendance.", "danger")
            return redirect(url_for('student.history'))

        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date() if new_date_str else att.session.session_date

        corr = CorrectionRequest(
            student_id=student.id,
            attendance_id=att.id,
            session_id=att.session_id,
            teacher_id=att.session.teacher_id,
            old_date=att.session.session_date,
            new_date=new_date,
            old_status=att.status,
            new_status=requested_status,
            reason=reason
        )
        db.session.add(corr)
        db.session.commit()

        # Notify Teacher
        notif = Notification(
            user_id=att.session.teacher.user_id,
            title="New Attendance Correction Request",
            message=f"Student {student.full_name} ({student.roll_number}) requested correction for {att.session.subject.name} on {att.session.session_date}.",
            type="info"
        )
        db.session.add(notif)
        db.session.commit()

        flash("Attendance correction request submitted to your teacher for verification.", "success")
        return redirect(url_for('student.dashboard'))

    # GET: fetch records eligible for correction
    records = Attendance.query.filter_by(student_id=student.id).join(AttendanceSession).order_by(AttendanceSession.session_date.desc()).limit(30).all()
    return render_template('student/request_correction.html', student=student, records=records)


@student_bp.route('/leave', methods=['GET', 'POST'])
def leave():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        reason = request.form.get('reason', '').strip()

        app = LeaveApplication(
            student_id=student.id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status="Pending"
        )
        db.session.add(app)
        db.session.commit()
        flash("Leave application submitted successfully for review.", "success")
        return redirect(url_for('student.leave'))

    my_leaves = LeaveApplication.query.filter_by(student_id=student.id).order_by(LeaveApplication.created_at.desc()).all()
    return render_template('student/leave.html', student=student, leaves=my_leaves)

