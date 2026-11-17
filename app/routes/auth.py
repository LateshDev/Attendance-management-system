from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User

auth_bp = Blueprint('auth', __name__)

# RBAC Decorators
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in allowed_roles:
                flash("Unauthorized access: You do not have permission for this section.", "danger")
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return role_required('admin')(f)

def hod_required(f):
    return role_required('admin', 'hod')(f)

def teacher_required(f):
    return role_required('admin', 'hod', 'teacher')(f)

def student_required(f):
    return role_required('student')(f)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember_me'))

        # Search by email or username
        user = User.query.filter(
            (User.email.ilike(login_id)) | (User.username.ilike(login_id))
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Contact the administrator.", "danger")
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            flash(f"Welcome back, {user.full_name}!", "success")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)

            # Route to respective dashboard
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'hod':
                return redirect(url_for('hod.dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher.dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student.dashboard'))
            return redirect(url_for('main.index'))
        else:
            flash("Invalid email/username or password. Please try again.", "danger")

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))

