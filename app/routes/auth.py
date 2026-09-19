from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

from app.models import db, User, Role
from app.forms import LoginForm, UserForm, ChangePasswordForm
from app.utils.decorators import admin_required
from app.utils.audit import log_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        login_input = form.login_id.data.strip().lower()
        user = User.query.filter(
            or_(User.email.ilike(login_input), User.username.ilike(login_input))
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            log_action('LOGIN', 'AUTH', user.id, None, f"User {user.username} logged in")
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        else:
            flash('Invalid email/username or password. Please try again.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    username = current_user.username
    user_id = current_user.id
    logout_user()
    log_action('LOGOUT', 'AUTH', user_id, None, f"User {username} logged out")
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Your current password does not match.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            log_action('CHANGE_PASSWORD', 'AUTH', current_user.id, None, "Password updated")
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('dashboard.index'))
    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/users')
@admin_required
def users():
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()

    query = User.query.join(Role)
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%')
            )
        )
    if role_filter:
        query = query.filter(Role.name == role_filter)

    all_users = query.order_by(User.full_name).all()
    roles = Role.query.all()
    return render_template('auth/users.html', users=all_users, roles=roles, search=search, role_filter=role_filter)


@auth_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    form = UserForm()
    form.role_id.choices = [(r.id, r.name) for r in Role.query.all()]

    if form.validate_on_submit():
        if not form.password.data:
            flash('A password is required when creating a new user account.', 'danger')
            return render_template('auth/user_form.html', form=form, title='Create New User')

        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            username=form.username.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role_id=form.role_id.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        log_action('CREATE_USER', 'USERS', user.id, None, f"Created {user.username} ({user.role.name})")
        flash(f'User "{user.full_name}" created successfully.', 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/user_form.html', form=form, title='Create New User')


@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(original_user=user, obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.all()]

    if form.validate_on_submit():
        old_val = f"{user.full_name} ({user.email}) Active={user.is_active}"
        user.full_name = form.full_name.data.strip()
        user.email = form.email.data.strip().lower()
        user.username = form.username.data.strip().lower()
        user.phone = form.phone.data.strip() if form.phone.data else None
        user.role_id = form.role_id.data
        user.is_active = form.is_active.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        log_action('UPDATE_USER', 'USERS', user.id, old_val, f"{user.full_name} ({user.email}) Active={user.is_active}")
        flash(f'User "{user.full_name}" updated successfully.', 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/user_form.html', form=form, title=f'Edit User: {user.full_name}', user=user)


@auth_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('auth.users'))

    user.is_active = not user.is_active
    db.session.commit()
    status_str = "activated" if user.is_active else "deactivated"
    log_action('TOGGLE_USER_STATUS', 'USERS', user.id, None, f"User {user.username} {status_str}")
    flash(f'User "{user.full_name}" has been {status_str}.', 'info')
    return redirect(url_for('auth.users'))
