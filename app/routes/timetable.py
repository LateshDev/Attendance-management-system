from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (
    db, Batch, TimetableVersion, Timetable, Subject, User,
    CorrectionRequest, AttendanceRecord, AttendanceSession, AuditLog
)

timetable_bp = Blueprint('timetable', __name__)

@timetable_bp.route('/')
@login_required
def view_schedule():
    # Find active B.Tech batch
    batch = Batch.query.filter_by(batch_code='BTECH-CSE-3C').first() or Batch.query.first()
    if not batch:
        flash("No batch or timetable version found.", "warning")
        return redirect(url_for('dashboard.index'))

    version = TimetableVersion.query.filter_by(batch_id=batch.id, is_active=True).first()

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

    return render_template(
        'timetable/view.html',
        batch=batch,
        version=version,
        slots_by_day=slots_by_day,
        periods=periods
    )


# -------------------------------------------------------------
# ATTENDANCE CORRECTION WORKFLOW (Student -> Teacher -> HOD)
# -------------------------------------------------------------
@timetable_bp.route('/corrections')
@login_required
def corrections_list():
    if current_user.is_admin or current_user.is_hod:
        pending = CorrectionRequest.query.filter_by(teacher_status='Verified', hod_status='Pending').all()
        history = CorrectionRequest.query.filter(CorrectionRequest.hod_status != 'Pending').order_by(CorrectionRequest.resolved_at.desc()).limit(30).all()
    elif current_user.is_teacher:
        pending = CorrectionRequest.query.filter_by(teacher_id=current_user.id, teacher_status='Pending').all()
        history = CorrectionRequest.query.filter_by(teacher_id=current_user.id).filter(CorrectionRequest.teacher_status != 'Pending').order_by(CorrectionRequest.created_at.desc()).limit(30).all()
    else:
        # Student view
        st = current_user.student
        pending = CorrectionRequest.query.filter_by(student_id=st.id, hod_status='Pending').all() if st else []
        history = CorrectionRequest.query.filter_by(student_id=st.id).filter(CorrectionRequest.hod_status != 'Pending').order_by(CorrectionRequest.resolved_at.desc()).all() if st else []

    return render_template('timetable/corrections.html', pending=pending, history=history)


@timetable_bp.route('/corrections/request', methods=['GET', 'POST'])
@login_required
def request_correction():
    if not current_user.is_student:
        flash("Only students can submit attendance dispute requests.", "warning")
        return redirect(url_for('dashboard.index'))

    student = current_user.student
    if request.method == 'POST':
        record_id = request.form.get('record_id', type=int)
        new_status = request.form.get('new_status', 'Present')
        reason = request.form.get('reason', '').strip()

        rec = AttendanceRecord.query.get_or_404(record_id)
        if rec.student_id != student.id:
            flash("Unauthorized access to attendance record.", "danger")
            return redirect(url_for('timetable.corrections_list'))

        # Find teacher of session
        session = rec.session
        teacher_user_id = session.marked_by_id

        corr = CorrectionRequest(
            student_id=student.id,
            record_id=rec.id,
            session_id=session.id,
            teacher_id=teacher_user_id,
            old_date=session.session_date,
            new_date=session.session_date,
            old_status=rec.status,
            new_status=new_status,
            reason=reason
        )
        db.session.add(corr)
        db.session.commit()
        flash("Correction request submitted to teacher for verification.", "success")
        return redirect(url_for('timetable.corrections_list'))

    # Eligible records (absences or disputable)
    records = AttendanceRecord.query.filter_by(student_id=student.id).join(AttendanceSession).order_by(AttendanceSession.session_date.desc()).limit(30).all()
    return render_template('timetable/request_correction.html', records=records, student=student)


@timetable_bp.route('/corrections/teacher-verify/<int:req_id>', methods=['POST'])
@login_required
def teacher_verify(req_id):
    if not (current_user.is_teacher or current_user.is_admin):
        flash("Unauthorized action.", "danger")
        return redirect(url_for('dashboard.index'))

    corr = CorrectionRequest.query.get_or_404(req_id)
    action = request.form.get('action')  # 'verify' or 'reject'
    remarks = request.form.get('teacher_remarks', '').strip()

    from datetime import datetime
    if action == 'verify':
        corr.teacher_status = 'Verified'
        corr.teacher_remarks = remarks
        corr.teacher_verified_at = datetime.utcnow()
        flash("Correction verified and forwarded to HOD for final authorization.", "success")
    else:
        corr.teacher_status = 'Rejected'
        corr.teacher_remarks = remarks
        corr.teacher_verified_at = datetime.utcnow()
        corr.resolved_at = datetime.utcnow()
        flash("Correction request rejected by teacher.", "info")

    db.session.commit()
    return redirect(url_for('timetable.corrections_list'))


@timetable_bp.route('/corrections/hod-approve/<int:req_id>', methods=['POST'])
@login_required
def hod_approve(req_id):
    if not (current_user.is_hod or current_user.is_admin):
        flash("Unauthorized: Only HOD or Admin can authorize attendance modifications.", "danger")
        return redirect(url_for('dashboard.index'))

    corr = CorrectionRequest.query.get_or_404(req_id)
    action = request.form.get('action')  # 'approve' or 'reject'
    remarks = request.form.get('hod_remarks', '').strip()

    from datetime import datetime
    if action == 'approve':
        corr.hod_status = 'Approved'
        corr.hod_remarks = remarks
        corr.hod_reviewed_at = datetime.utcnow()
        corr.resolved_at = datetime.utcnow()

        # Update the actual attendance record in database
        rec = AttendanceRecord.query.get(corr.record_id)
        if rec:
            old_st = rec.status
            rec.status = corr.new_status
            rec.remarks = f"Modified via HOD Approval (Req #{corr.id})"

            # Insert audit log
            log = AuditLog(
                user_id=current_user.id,
                action="UPDATE_ATTENDANCE_CORRECTION",
                module="ATTENDANCE",
                record_id=str(rec.id),
                old_value=old_st,
                new_value=corr.new_status
            )
            db.session.add(log)

        flash("Attendance correction authorized and database record updated!", "success")
    else:
        corr.hod_status = 'Rejected'
        corr.hod_remarks = remarks
        corr.hod_reviewed_at = datetime.utcnow()
        corr.resolved_at = datetime.utcnow()
        flash("Correction request rejected by HOD.", "info")

    db.session.commit()
    return redirect(url_for('timetable.corrections_list'))
