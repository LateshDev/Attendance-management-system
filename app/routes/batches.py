from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from datetime import date

from app.models import db, Batch, User, Student, BatchStudent, Subject, BatchSubject, Role
from app.forms import BatchForm
from app.utils.decorators import admin_required, teacher_or_admin_required, check_batch_access
from app.utils.audit import log_action

batches_bp = Blueprint('batches', __name__)


@batches_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'Active').strip()

    query = Batch.query
    if current_user.is_teacher:
        query = query.filter_by(teacher_id=current_user.id)

    if search:
        query = query.filter(
            or_(
                Batch.batch_name.ilike(f'%{search}%'),
                Batch.batch_code.ilike(f'%{search}%'),
                Batch.course_name.ilike(f'%{search}%')
            )
        )
    if status_filter:
        query = query.filter(Batch.status == status_filter)

    batches = query.order_by(Batch.batch_name).all()
    return render_template('batches/index.html', batches=batches, search=search, status_filter=status_filter)


@batches_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def create():
    form = BatchForm()
    teachers = User.query.join(Role).filter(Role.name == 'TEACHER', User.is_active == True).all()
    form.teacher_id.choices = [(0, '-- Select Teacher (Optional) --')] + [(t.id, f"{t.full_name} ({t.username})") for t in teachers]

    if form.validate_on_submit():
        teacher_id = form.teacher_id.data if form.teacher_id.data != 0 else None
        batch = Batch(
            batch_name=form.batch_name.data.strip(),
            batch_code=form.batch_code.data.strip().upper(),
            course_name=form.course_name.data.strip(),
            teacher_id=teacher_id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status=form.status.data
        )
        db.session.add(batch)
        db.session.commit()

        log_action('CREATE_BATCH', 'BATCHES', batch.id, None, f"Created {batch.batch_code}: {batch.batch_name}")
        flash(f'Batch "{batch.batch_name}" created successfully.', 'success')
        return redirect(url_for('batches.view', batch_id=batch.id))

    return render_template('batches/form.html', form=form, title='Add New Batch')


@batches_bp.route('/<int:batch_id>')
@login_required
def view(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    if not check_batch_access(batch, current_user):
        flash('You are not authorized to view this batch.', 'danger')
        abort(403)

    enrolled_students = batch.get_enrolled_students()
    all_active_students = Student.query.filter_by(status='Active').order_by(Student.roll_number).all()
    
    # Students not yet enrolled
    enrolled_ids = {s.id for s in enrolled_students}
    available_students = [s for s in all_active_students if s.id not in enrolled_ids]

    subjects = Subject.query.filter_by(status='Active').order_by(Subject.subject_name).all()
    batch_subjects = BatchSubject.query.filter_by(batch_id=batch.id).all()
    assigned_subject_ids = {bs.subject_id for bs in batch_subjects}

    # Calculate overall attendance rate for this batch
    from app.models import AttendanceSession, AttendanceRecord
    sessions = AttendanceSession.query.filter_by(batch_id=batch.id).all()
    total_records = 0
    present_records = 0
    if sessions:
        s_ids = [s.id for s in sessions]
        recs = AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(s_ids)).all()
        total_records = len(recs)
        present_records = sum(1 for r in recs if r.status == 'Present')

    batch_attendance_pct = round((present_records / total_records) * 100.0, 1) if total_records > 0 else 0.0

    return render_template(
        'batches/view.html',
        batch=batch,
        enrolled_students=enrolled_students,
        available_students=available_students,
        batch_subjects=batch_subjects,
        subjects=subjects,
        assigned_subject_ids=assigned_subject_ids,
        total_sessions=len(sessions),
        batch_attendance_pct=batch_attendance_pct
    )


@batches_bp.route('/<int:batch_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    form = BatchForm(original_batch=batch, obj=batch)
    teachers = User.query.join(Role).filter(Role.name == 'TEACHER', User.is_active == True).all()
    form.teacher_id.choices = [(0, '-- Select Teacher (Optional) --')] + [(t.id, f"{t.full_name} ({t.username})") for t in teachers]

    if request.method == 'GET' and batch.teacher_id:
        form.teacher_id.data = batch.teacher_id

    if form.validate_on_submit():
        old_val = f"{batch.batch_code} ({batch.batch_name}) Status={batch.status}"
        batch.batch_name = form.batch_name.data.strip()
        batch.batch_code = form.batch_code.data.strip().upper()
        batch.course_name = form.course_name.data.strip()
        batch.teacher_id = form.teacher_id.data if form.teacher_id.data != 0 else None
        batch.start_date = form.start_date.data
        batch.end_date = form.end_date.data
        batch.status = form.status.data

        db.session.commit()
        log_action('UPDATE_BATCH', 'BATCHES', batch.id, old_val, f"{batch.batch_code} ({batch.batch_name}) Status={batch.status}")
        flash(f'Batch "{batch.batch_name}" updated successfully.', 'success')
        return redirect(url_for('batches.view', batch_id=batch.id))

    return render_template('batches/form.html', form=form, title=f'Edit Batch: {batch.batch_name}', batch=batch)


@batches_bp.route('/<int:batch_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    batch.status = 'Archived' if batch.status == 'Active' else 'Active'
    db.session.commit()
    log_action('TOGGLE_BATCH_STATUS', 'BATCHES', batch.id, None, f"Batch {batch.batch_code} status changed to {batch.status}")
    flash(f'Batch "{batch.batch_name}" is now {batch.status}.', 'info')
    return redirect(url_for('batches.index'))


@batches_bp.route('/<int:batch_id>/enroll', methods=['POST'])
@admin_required
def enroll_student(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    student_id = request.form.get('student_id', type=int)

    if not student_id:
        flash('Please select a valid student.', 'warning')
        return redirect(url_for('batches.view', batch_id=batch.id))

    student = Student.query.get_or_404(student_id)
    existing = BatchStudent.query.filter_by(batch_id=batch.id, student_id=student.id).first()

    if existing:
        if existing.status == 'Active':
            flash(f'Student "{student.student_name}" is already active in this batch.', 'warning')
        else:
            existing.status = 'Active'
            db.session.commit()
            log_action('RE_ENROLL_STUDENT', 'BATCH_STUDENT', batch.id, None, f"Re-enrolled {student.student_name} in {batch.batch_code}")
            flash(f'Student "{student.student_name}" re-enrolled in batch.', 'success')
    else:
        bs = BatchStudent(
            batch_id=batch.id,
            student_id=student.id,
            roll_number_in_batch=student.roll_number,
            joined_date=date.today(),
            status='Active'
        )
        db.session.add(bs)
        db.session.commit()
        log_action('ENROLL_STUDENT', 'BATCH_STUDENT', batch.id, None, f"Enrolled {student.student_name} in {batch.batch_code}")
        flash(f'Student "{student.student_name}" enrolled successfully.', 'success')

    return redirect(url_for('batches.view', batch_id=batch.id))


@batches_bp.route('/<int:batch_id>/remove-student/<int:student_id>', methods=['POST'])
@admin_required
def remove_student(batch_id, student_id):
    batch = Batch.query.get_or_404(batch_id)
    enrollment = BatchStudent.query.filter_by(batch_id=batch.id, student_id=student_id).first_or_404()

    student_name = enrollment.student.student_name
    enrollment.status = 'Removed'
    db.session.commit()

    log_action('REMOVE_STUDENT', 'BATCH_STUDENT', batch.id, None, f"Removed {student_name} from {batch.batch_code}")
    flash(f'Student "{student_name}" removed from batch.', 'info')
    return redirect(url_for('batches.view', batch_id=batch.id))


@batches_bp.route('/<int:batch_id>/assign-subject', methods=['POST'])
@admin_required
def assign_subject(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    subject_id = request.form.get('subject_id', type=int)

    if not subject_id:
        flash('Please select a subject to assign.', 'warning')
        return redirect(url_for('batches.view', batch_id=batch.id))

    existing = BatchSubject.query.filter_by(batch_id=batch.id, subject_id=subject_id).first()
    if existing:
        flash('Subject is already assigned to this batch.', 'warning')
    else:
        bs = BatchSubject(batch_id=batch.id, subject_id=subject_id)
        db.session.add(bs)
        db.session.commit()
        log_action('ASSIGN_SUBJECT', 'BATCH_SUBJECT', batch.id, None, f"Assigned subject {subject_id} to batch {batch.batch_code}")
        flash('Subject assigned to batch successfully.', 'success')

    return redirect(url_for('batches.view', batch_id=batch.id))


@batches_bp.route('/<int:batch_id>/remove-subject/<int:subject_id>', methods=['POST'])
@admin_required
def remove_subject(batch_id, subject_id):
    batch = Batch.query.get_or_404(batch_id)
    bs = BatchSubject.query.filter_by(batch_id=batch.id, subject_id=subject_id).first_or_404()
    db.session.delete(bs)
    db.session.commit()
    log_action('REMOVE_SUBJECT', 'BATCH_SUBJECT', batch.id, None, f"Removed subject {subject_id} from batch {batch.batch_code}")
    flash('Subject removed from batch.', 'info')
    return redirect(url_for('batches.view', batch_id=batch.id))
