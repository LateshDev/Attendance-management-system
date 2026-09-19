from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.models import db, Subject
from app.forms import SubjectForm
from app.utils.decorators import admin_required
from app.utils.audit import log_action

subjects_bp = Blueprint('subjects', __name__)


@subjects_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'Active').strip()

    query = Subject.query
    if search:
        query = query.filter(
            or_(
                Subject.subject_name.ilike(f'%{search}%'),
                Subject.subject_code.ilike(f'%{search}%')
            )
        )
    if status_filter:
        query = query.filter(Subject.status == status_filter)

    subjects = query.order_by(Subject.subject_name).all()
    return render_template('subjects/index.html', subjects=subjects, search=search, status_filter=status_filter)


@subjects_bp.route('/new', methods=['GET', 'POST'])
@admin_required
def create():
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(
            subject_name=form.subject_name.data.strip(),
            subject_code=form.subject_code.data.strip().upper(),
            description=form.description.data.strip() if form.description.data else None,
            status=form.status.data
        )
        db.session.add(subject)
        db.session.commit()
        log_action('CREATE_SUBJECT', 'SUBJECTS', subject.id, None, f"Created {subject.subject_code}: {subject.subject_name}")
        flash(f'Subject "{subject.subject_name}" created successfully.', 'success')
        return redirect(url_for('subjects.index'))

    return render_template('subjects/form.html', form=form, title='Add New Subject')


@subjects_bp.route('/<int:subject_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    form = SubjectForm(original_subject=subject, obj=subject)

    if form.validate_on_submit():
        old_val = f"{subject.subject_code}: {subject.subject_name}"
        subject.subject_name = form.subject_name.data.strip()
        subject.subject_code = form.subject_code.data.strip().upper()
        subject.description = form.description.data.strip() if form.description.data else None
        subject.status = form.status.data

        db.session.commit()
        log_action('UPDATE_SUBJECT', 'SUBJECTS', subject.id, old_val, f"{subject.subject_code}: {subject.subject_name}")
        flash(f'Subject "{subject.subject_name}" updated successfully.', 'success')
        return redirect(url_for('subjects.index'))

    return render_template('subjects/form.html', form=form, title=f'Edit Subject: {subject.subject_name}', subject=subject)


@subjects_bp.route('/<int:subject_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    subject.status = 'Inactive' if subject.status == 'Active' else 'Active'
    db.session.commit()
    log_action('TOGGLE_SUBJECT_STATUS', 'SUBJECTS', subject.id, None, f"Subject {subject.subject_code} status set to {subject.status}")
    flash(f'Subject "{subject.subject_name}" is now {subject.status}.', 'info')
    return redirect(url_for('subjects.index'))
