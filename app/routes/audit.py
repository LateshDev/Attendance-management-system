from flask import Blueprint, render_template, request
from sqlalchemy import or_

from app.models import AuditLog, User
from app.utils.decorators import admin_required

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/')
@admin_required
def index():
    module_filter = request.args.get('module', '').strip()
    user_filter = request.args.get('user_id', type=int)
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    query = AuditLog.query.outerjoin(User)

    if module_filter:
        query = query.filter(AuditLog.module == module_filter)
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)
    if search:
        query = query.filter(
            or_(
                AuditLog.action.ilike(f'%{search}%'),
                AuditLog.new_value.ilike(f'%{search}%'),
                AuditLog.old_value.ilike(f'%{search}%')
            )
        )

    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=25, error_out=False)
    users = User.query.order_by(User.full_name).all()

    modules = ['AUTH', 'USERS', 'BATCHES', 'STUDENTS', 'SUBJECTS', 'ATTENDANCE', 'LEAVES', 'SETTINGS']

    return render_template(
        'audit/index.html',
        pagination=pagination,
        logs=pagination.items,
        users=users,
        modules=modules,
        module_filter=module_filter,
        user_filter=user_filter,
        search=search
    )
