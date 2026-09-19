from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import date

from app.models import db, LeaveRequest, Student, Batch, BatchStudent
from app.forms import LeaveRequestForm, LeaveReviewForm
from app.utils.decorators import teacher_or_admin_required, admin_required
from app.utils.audit import log_action

leaves_bp = Blueprint('leaves', __name__)


@leaves_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '').strip()
    batch_filter = request.args.get('batch_id', type=int)

    query = LeaveRequest.query.join(Student).join(Batch)

    if current_user.is_teacher:
        teacher_batches = Batch.query.filter_by(teacher_id=current_user.id).all()
        t_batch_ids = [b.id for b in teacher_batches]
        query = query.filter(LeaveRequest.batch_id.in_(t_batch_ids))

    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    if batch_filter:
        query = query.filter(LeaveRequest.batch_id == batch_filter)

    leaves = query.order_by(LeaveRequest.created_at.desc()).all()

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    return render_template('leaves/index.html', leaves=leaves, batches=batches, status_filter=status_filter, batch_filter=batch_filter)


@leaves_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    form = LeaveRequestForm()

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    form.batch_id.choices = [(b.id, f"{b.batch_code} - {b.batch_name}") for b in batches]

    # Populate students
    students = Student.query.filter_by(status='Active').order_by(Student.student_name).all()
    form.student_id.choices = [(s.id, f"{s.roll_number} - {s.student_name}") for s in students]

    if form.validate_on_submit():
        leave = LeaveRequest(
            student_id=form.student_id.data,
            batch_id=form.batch_id.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data.strip(),
            status='Pending'
        )
        db.session.add(leave)
        db.session.commit()

        student = Student.query.get(leave.student_id)
        log_action('CREATE_LEAVE_REQUEST', 'LEAVES', leave.id, None, f"Leave request for {student.student_name} ({leave.start_date} to {leave.end_date})")
        flash(f'Leave application submitted for "{student.student_name}".', 'success')
        return redirect(url_for('leaves.index'))

    return render_template('leaves/form.html', form=form, title='Apply for Leave')


@leaves_bp.route('/<int:leave_id>/review', methods=['GET', 'POST'])
@teacher_or_admin_required
def review(leave_id):
    leave = LeaveRequest.query.get_or_404(leave_id)
    form = LeaveReviewForm()

    if form.validate_on_submit():
        old_status = leave.status
        leave.status = form.status.data
        leave.review_notes = form.review_notes.data.strip() if form.review_notes.data else None
        leave.reviewed_by_id = current_user.id
        db.session.commit()

        log_action('REVIEW_LEAVE', 'LEAVES', leave.id, old_status, f"{leave.status}: {leave.review_notes}")
        flash(f'Leave request has been marked as {leave.status}.', 'success')
        return redirect(url_for('leaves.index'))

    return render_template('leaves/review.html', leave=leave, form=form)
