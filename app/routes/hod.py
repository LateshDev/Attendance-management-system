from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import (
    db, Department, ClassGroup, Student, Teacher, Attendance,
    AttendanceSession, CorrectionRequest, AttendanceLog, Notification, LeaveApplication
)
from app.routes.auth import hod_required

hod_bp = Blueprint('hod', __name__)

@hod_bp.before_request
@login_required
@hod_required
def check_hod():
    pass

@hod_bp.route('/dashboard')
def dashboard():
    dept = Department.query.first()  # Default department
    classes = ClassGroup.query.filter_by(department_id=dept.id).all() if dept else []
    teachers = Teacher.query.filter_by(department_id=dept.id).all() if dept else []
    total_students = Student.query.filter_by(department_id=dept.id).count() if dept else 0

    # Pending HOD Approvals (requests verified by teachers)
    pending_approvals = CorrectionRequest.query.filter_by(
        teacher_status='Verified',
        hod_status='Pending'
    ).order_by(CorrectionRequest.created_at.desc()).all()

    # Department-wide attendance calculation
    all_dept_sessions = AttendanceSession.query.join(ClassGroup).filter(ClassGroup.department_id == dept.id).all() if dept else []
    session_ids = [s.id for s in all_dept_sessions]
    
    total_records = Attendance.query.filter(Attendance.session_id.in_(session_ids)).count() if session_ids else 0
    attended_records = Attendance.query.filter(
        Attendance.session_id.in_(session_ids),
        Attendance.status.in_(['Present', 'Late'])
    ).count() if session_ids else 0

    dept_attendance_pct = round((attended_records / total_records * 100), 1) if total_records > 0 else 0.0

    # Recent Audit Logs
    recent_logs = AttendanceLog.query.order_by(AttendanceLog.timestamp.desc()).limit(10).all()

    return render_template(
        'hod/dashboard.html',
        dept=dept,
        classes=classes,
        teachers=teachers,
        total_students=total_students,
        pending_approvals=pending_approvals,
        total_sessions=len(all_dept_sessions),
        dept_attendance_pct=dept_attendance_pct,
        recent_logs=recent_logs
    )


@hod_bp.route('/corrections')
def corrections():
    # Show all correction requests requiring HOD action, plus history
    pending = CorrectionRequest.query.filter_by(teacher_status='Verified', hod_status='Pending').all()
    history = CorrectionRequest.query.filter(CorrectionRequest.hod_status != 'Pending').order_by(CorrectionRequest.resolved_at.desc()).limit(30).all()
    
    return render_template('hod/corrections.html', pending=pending, history=history)


@hod_bp.route('/approve-correction/<int:req_id>', methods=['POST'])
def approve_correction(req_id):
    corr = CorrectionRequest.query.get_or_404(req_id)
    action = request.form.get('action')  # 'approve' or 'reject'
    remarks = request.form.get('hod_remarks', '').strip()

    if action == 'approve':
        corr.hod_status = 'Approved'
        corr.hod_remarks = remarks
        corr.hod_reviewed_at = datetime.utcnow()
        corr.resolved_at = datetime.utcnow()

        # Update the actual attendance record
        att = Attendance.query.get(corr.attendance_id)
        if att:
            old_st = att.status
            att.status = corr.new_status
            att.remarks = f"Corrected via HOD Approval (Req #{corr.id})"

            # Audit log
            log = AttendanceLog(
                attendance_id=att.id,
                session_id=att.session_id,
                modified_by_user_id=current_user.id,
                old_status=old_st,
                new_status=corr.new_status,
                action_type="Correction Request Approval",
                reason=f"Approved by HOD: {remarks or corr.reason}"
            )
            db.session.add(log)

        # Notify Student
        notif_student = Notification(
            user_id=corr.student.user_id,
            title="Attendance Correction Approved",
            message=f"Your attendance for {corr.session.subject.name} on {corr.old_date} was approved and updated to {corr.new_status}.",
            type="success"
        )
        db.session.add(notif_student)

        # Notify Teacher
        notif_teacher = Notification(
            user_id=corr.teacher.user_id,
            title="Correction Request Approved by HOD",
            message=f"Correction for student {corr.student.full_name} ({corr.session.subject.name}) has been approved by HOD.",
            type="info"
        )
        db.session.add(notif_teacher)

        flash("Attendance correction approved and successfully applied to database!", "success")

    elif action == 'reject':
        corr.hod_status = 'Rejected'
        corr.hod_remarks = remarks
        corr.hod_reviewed_at = datetime.utcnow()
        corr.resolved_at = datetime.utcnow()

        # Notify Student
        notif_student = Notification(
            user_id=corr.student.user_id,
            title="Attendance Correction Rejected",
            message=f"Your attendance correction request for {corr.session.subject.name} was rejected by HOD: {remarks}",
            type="danger"
        )
        db.session.add(notif_student)
        flash("Correction request rejected.", "info")

    db.session.commit()
    return redirect(url_for('hod.corrections'))


@hod_bp.route('/leaves')
def leaves():
    pending_leaves = LeaveApplication.query.filter_by(status='Pending').order_by(LeaveApplication.created_at.desc()).all()
    past_leaves = LeaveApplication.query.filter(LeaveApplication.status != 'Pending').order_by(LeaveApplication.reviewed_at.desc()).limit(20).all()
    return render_template('hod/leaves.html', pending_leaves=pending_leaves, past_leaves=past_leaves)


@hod_bp.route('/review-leave/<int:leave_id>', methods=['POST'])
def review_leave(leave_id):
    leave = LeaveApplication.query.get_or_404(leave_id)
    action = request.form.get('action')

    if action == 'approve':
        leave.status = 'Approved'
        leave.reviewed_by = current_user.id
        leave.reviewed_at = datetime.utcnow()
        flash("Student leave application approved.", "success")
        notif = Notification(
            user_id=leave.student.user_id,
            title="Leave Application Approved",
            message=f"Your leave application from {leave.start_date} to {leave.end_date} has been approved.",
            type="success"
        )
        db.session.add(notif)
    else:
        leave.status = 'Rejected'
        leave.reviewed_by = current_user.id
        leave.reviewed_at = datetime.utcnow()
        flash("Student leave application rejected.", "info")
        notif = Notification(
            user_id=leave.student.user_id,
            title="Leave Application Rejected",
            message=f"Your leave application from {leave.start_date} to {leave.end_date} has been rejected.",
            type="warning"
        )
        db.session.add(notif)

    db.session.commit()
    return redirect(url_for('hod.leaves'))

