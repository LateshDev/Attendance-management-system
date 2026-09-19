from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from calendar import monthrange
from sqlalchemy import or_

from app.models import (
    db, Batch, Student, Subject, BatchStudent, BatchSubject,
    AttendanceSession, AttendanceRecord, LeaveRequest, User
)
from app.utils.decorators import teacher_or_admin_required, check_batch_access
from app.utils.audit import log_action

attendance_bp = Blueprint('attendance', __name__)


# ==========================================
# 1. MAIN ATTENDANCE MARKING SCREEN
# ==========================================

@attendance_bp.route('/mark', methods=['GET', 'POST'])
@teacher_or_admin_required
def mark():
    today_str = date.today().strftime('%Y-%m-%d')
    selected_batch_id = request.args.get('batch_id', type=int) or request.form.get('batch_id', type=int)
    selected_subject_id = request.args.get('subject_id', type=int) or request.form.get('subject_id', type=int)
    selected_date_str = request.args.get('session_date', today_str) or request.form.get('session_date', today_str)

    try:
        session_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        session_date = date.today()
        selected_date_str = today_str

    # Restrict batches for teachers
    if current_user.is_teacher:
        batches = Batch.query.filter_by(teacher_id=current_user.id, status='Active').order_by(Batch.batch_name).all()
    else:
        batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()

    # Subjects list
    subjects = Subject.query.filter_by(status='Active').order_by(Subject.subject_name).all()

    selected_batch = None
    existing_session = None
    students_data = []

    if selected_batch_id:
        selected_batch = Batch.query.get(selected_batch_id)
        if selected_batch and not check_batch_access(selected_batch, current_user):
            flash('You do not have authorization to mark attendance for this batch.', 'danger')
            abort(403)

        # Check if attendance is already marked for this batch + date + subject
        if selected_subject_id:
            existing_session = AttendanceSession.query.filter_by(
                batch_id=selected_batch_id,
                subject_id=selected_subject_id,
                session_date=session_date
            ).first()

        # Load enrolled active students
        if selected_batch:
            enrolled = selected_batch.get_enrolled_students()
            for st in enrolled:
                # Check for approved leave on this date
                is_leave = LeaveRequest.is_student_on_approved_leave(st.id, session_date)
                students_data.append({
                    'student': st,
                    'is_approved_leave': is_leave,
                    'default_status': 'Leave' if is_leave else None
                })

    # POST REQUEST: Commit attendance records
    if request.method == 'POST':
        if not selected_batch_id or not selected_subject_id or not selected_date_str:
            flash('Please select Batch, Subject, and Date to mark attendance.', 'warning')
            return redirect(url_for('attendance.mark', batch_id=selected_batch_id, subject_id=selected_subject_id, session_date=selected_date_str))

        # Check duplicate
        if existing_session:
            flash(f"Attendance has already been marked for this batch, date and subject by {existing_session.marked_by.full_name}.", 'danger')
            return redirect(url_for('attendance.mark', batch_id=selected_batch_id, subject_id=selected_subject_id, session_date=selected_date_str))

        if not students_data:
            flash('No active students enrolled in this batch to mark attendance for.', 'warning')
            return redirect(url_for('attendance.mark', batch_id=selected_batch_id, subject_id=selected_subject_id, session_date=selected_date_str))

        # Create session
        new_session = AttendanceSession(
            batch_id=selected_batch_id,
            subject_id=selected_subject_id,
            session_date=session_date,
            marked_by_id=current_user.id,
            remarks=request.form.get('session_remarks', '').strip() or None
        )
        db.session.add(new_session)
        db.session.flush()

        # Create records
        present_count = 0
        absent_count = 0
        leave_count = 0

        for item in students_data:
            st = item['student']
            status_val = request.form.get(f"status_{st.id}", 'Present')
            if status_val not in ['Present', 'Absent', 'Leave']:
                status_val = 'Present'

            rec = AttendanceRecord(
                session_id=new_session.id,
                student_id=st.id,
                status=status_val,
                remarks=request.form.get(f"remarks_{st.id}", '').strip() or None
            )
            db.session.add(rec)

            if status_val == 'Present':
                present_count += 1
            elif status_val == 'Absent':
                absent_count += 1
            else:
                leave_count += 1

        db.session.commit()

        log_action(
            'MARK_ATTENDANCE',
            'ATTENDANCE',
            new_session.id,
            None,
            f"Marked Batch {selected_batch.batch_code} ({session_date}): {present_count} P, {absent_count} A, {leave_count} L"
        )

        flash(f"Attendance marked successfully for {selected_batch.batch_name}! (Present: {present_count}, Absent: {absent_count}, Leave: {leave_count})", 'success')
        return redirect(url_for('attendance.history', batch_id=selected_batch_id, subject_id=selected_subject_id, start_date=selected_date_str, end_date=selected_date_str))

    return render_template(
        'attendance/mark.html',
        batches=batches,
        subjects=subjects,
        selected_batch_id=selected_batch_id,
        selected_subject_id=selected_subject_id,
        selected_date_str=selected_date_str,
        selected_batch=selected_batch,
        existing_session=existing_session,
        students_data=students_data,
        today_str=today_str
    )


# ==========================================
# 2. VIEW ATTENDANCE SESSION
# ==========================================

@attendance_bp.route('/session/<int:session_id>')
@teacher_or_admin_required
def view_session(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    if not check_batch_access(session_obj.batch, current_user):
        flash('You are not authorized to view this session.', 'danger')
        abort(403)

    records = AttendanceRecord.query.filter_by(session_id=session_obj.id)\
        .join(Student).order_by(Student.roll_number).all()

    return render_template('attendance/view_session.html', session=session_obj, records=records)


# ==========================================
# 3. EDIT ATTENDANCE SESSION
# ==========================================

@attendance_bp.route('/session/<int:session_id>/edit', methods=['GET', 'POST'])
@teacher_or_admin_required
def edit_session(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    if not check_batch_access(session_obj.batch, current_user):
        flash('You are not authorized to edit this session.', 'danger')
        abort(403)

    records = AttendanceRecord.query.filter_by(session_id=session_obj.id)\
        .join(Student).order_by(Student.roll_number).all()

    if request.method == 'POST':
        changes_log = []
        for rec in records:
            new_status = request.form.get(f"status_{rec.student_id}")
            new_remarks = request.form.get(f"remarks_{rec.student_id}", '').strip() or None

            if new_status in ['Present', 'Absent', 'Leave'] and new_status != rec.status:
                old_status = rec.status
                rec.status = new_status
                changes_log.append(f"{rec.student.student_name}: {old_status} -> {new_status}")

            rec.remarks = new_remarks

        session_obj.remarks = request.form.get('session_remarks', '').strip() or None
        session_obj.updated_at = datetime.utcnow()
        db.session.commit()

        if changes_log:
            log_action(
                'EDIT_ATTENDANCE',
                'ATTENDANCE',
                session_obj.id,
                None,
                f"Updated attendance for {session_obj.batch.batch_code} ({session_obj.session_date}): " + ", ".join(changes_log)
            )

        flash('Attendance session updated successfully!', 'success')
        return redirect(url_for('attendance.view_session', session_id=session_obj.id))

    return render_template('attendance/edit_session.html', session=session_obj, records=records)


# ==========================================
# 4. ATTENDANCE HISTORY
# ==========================================

@attendance_bp.route('/history')
@login_required
def history():
    batch_filter = request.args.get('batch_id', type=int)
    subject_filter = request.args.get('subject_id', type=int)
    student_filter = request.args.get('student_id', type=int)
    status_filter = request.args.get('status', '').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)

    query = AttendanceRecord.query.join(AttendanceSession).join(Student).join(Batch, AttendanceSession.batch_id == Batch.id)

    if current_user.is_teacher:
        teacher_batches = Batch.query.filter_by(teacher_id=current_user.id).all()
        t_batch_ids = [b.id for b in teacher_batches]
        query = query.filter(AttendanceSession.batch_id.in_(t_batch_ids))

    if batch_filter:
        query = query.filter(AttendanceSession.batch_id == batch_filter)
    if subject_filter:
        query = query.filter(AttendanceSession.subject_id == subject_filter)
    if student_filter:
        query = query.filter(AttendanceRecord.student_id == student_filter)
    if status_filter:
        query = query.filter(AttendanceRecord.status == status_filter)

    if start_date_str:
        try:
            sd = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(AttendanceSession.session_date >= sd)
        except ValueError:
            pass

    if end_date_str:
        try:
            ed = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(AttendanceSession.session_date <= ed)
        except ValueError:
            pass

    pagination = query.order_by(AttendanceSession.session_date.desc(), AttendanceRecord.id.desc()).paginate(page=page, per_page=20, error_out=False)

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    subjects = Subject.query.filter_by(status='Active').order_by(Subject.subject_name).all()

    return render_template(
        'attendance/history.html',
        pagination=pagination,
        records=pagination.items,
        batches=batches,
        subjects=subjects,
        batch_filter=batch_filter,
        subject_filter=subject_filter,
        student_filter=student_filter,
        status_filter=status_filter,
        start_date_str=start_date_str,
        end_date_str=end_date_str
    )


# ==========================================
# 5. MONTHLY ATTENDANCE GRID VIEW
# ==========================================

@attendance_bp.route('/monthly')
@login_required
def monthly():
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)
    selected_batch_id = request.args.get('batch_id', type=int)
    selected_subject_id = request.args.get('subject_id', type=int)

    # Days in the selected month
    _, num_days = monthrange(year, month)
    days = list(range(1, num_days + 1))

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    subjects = Subject.query.filter_by(status='Active').order_by(Subject.subject_name).all()

    selected_batch = None
    matrix = []

    if selected_batch_id:
        selected_batch = Batch.query.get_or_404(selected_batch_id)
        if not check_batch_access(selected_batch, current_user):
            flash('Access denied for this batch.', 'danger')
            abort(403)

        students = selected_batch.get_enrolled_students()

        # Fetch sessions for this batch, month, year
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        sess_query = AttendanceSession.query.filter(
            AttendanceSession.batch_id == selected_batch_id,
            AttendanceSession.session_date >= start_date,
            AttendanceSession.session_date <= end_date
        )
        if selected_subject_id:
            sess_query = sess_query.filter(AttendanceSession.subject_id == selected_subject_id)

        sessions = sess_query.all()
        session_map = {}  # date -> session_id
        for s in sessions:
            session_map[s.session_date.day] = s.id

        session_ids = [s.id for s in sessions]
        all_records = AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(session_ids)).all() if session_ids else []

        # Map: (student_id, session_id) -> status
        rec_map = {(r.student_id, r.session_id): r.status for r in all_records}

        for st in students:
            row_statuses = []
            present_count = 0
            total_classes = 0

            for d in days:
                sess_id = session_map.get(d)
                if sess_id:
                    st_status = rec_map.get((st.id, sess_id), '-')
                    row_statuses.append(st_status)
                    if st_status != '-':
                        total_classes += 1
                        if st_status == 'Present':
                            present_count += 1
                else:
                    row_statuses.append('-')

            pct = round((present_count / total_classes) * 100.0, 1) if total_classes > 0 else 0.0
            matrix.append({
                'student': st,
                'days': row_statuses,
                'total_classes': total_classes,
                'present_count': present_count,
                'percentage': pct
            })

    months_list = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    return render_template(
        'attendance/monthly.html',
        batches=batches,
        subjects=subjects,
        selected_batch=selected_batch,
        selected_batch_id=selected_batch_id,
        selected_subject_id=selected_subject_id,
        month=month,
        year=year,
        days=days,
        matrix=matrix,
        months_list=months_list
    )


# ==========================================
# 6. ASYNC API FOR CLIENT CHECKS
# ==========================================

@attendance_bp.route('/api/check-session')
@login_required
def api_check_session():
    """Returns JSON check whether session exists for batch+subject+date."""
    batch_id = request.args.get('batch_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    date_str = request.args.get('session_date', '').strip()

    if not (batch_id and subject_id and date_str):
        return jsonify({'exists': False}), 200

    try:
        s_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'exists': False, 'error': 'Invalid date'}), 400

    session_obj = AttendanceSession.query.filter_by(
        batch_id=batch_id,
        subject_id=subject_id,
        session_date=s_date
    ).first()

    if session_obj:
        return jsonify({
            'exists': True,
            'session_id': session_obj.id,
            'marked_by': session_obj.marked_by.full_name,
            'total_students': session_obj.total_records,
            'present': session_obj.present_count,
            'absent': session_obj.absent_count,
            'leave': session_obj.leave_count
        })

    return jsonify({'exists': False})

