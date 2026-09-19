import sys
import flask
import sqlalchemy
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.models import db, Setting
from app.forms import SettingsForm
from app.utils.decorators import admin_required
from app.utils.audit import log_action

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/', methods=['GET', 'POST'])
@admin_required
def index():
    form = SettingsForm()

    if request.method == 'GET':
        form.institution_name.data = Setting.get_value('institution_name', 'Batch Attendance Academy')
        form.contact_email.data = Setting.get_value('contact_email', 'admin@example.com')
        form.academic_session.data = Setting.get_value('academic_session', '2026-2027')
        form.low_attendance_threshold.data = float(Setting.get_value('low_attendance_threshold', 75.0))

    if form.validate_on_submit():
        old_thresh = Setting.get_value('low_attendance_threshold', '75.0')
        Setting.set_value('institution_name', form.institution_name.data.strip(), 'Name of the educational institution')
        Setting.set_value('contact_email', form.contact_email.data.strip() if form.contact_email.data else '', 'Official contact email')
        Setting.set_value('academic_session', form.academic_session.data.strip(), 'Current academic cycle/term')
        Setting.set_value('low_attendance_threshold', str(form.low_attendance_threshold.data), 'Minimum acceptable attendance percentage')

        log_action('UPDATE_SETTINGS', 'SETTINGS', None, f"Threshold: {old_thresh}%", f"Threshold: {form.low_attendance_threshold.data}%")
        flash('System settings updated successfully!', 'success')
        return redirect(url_for('settings.index'))

    # System telemetry info
    sys_info = {
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'sqlalchemy_version': sqlalchemy.__version__,
        'db_dialect': db.engine.dialect.name
    }

    return render_template('settings/index.html', form=form, sys_info=sys_info)
