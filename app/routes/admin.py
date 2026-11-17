import json
from datetime import datetime, date, time
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app.models import (
    db, User, Teacher, Student, Department, Course, ClassGroup,
    Subject, TeacherSubject, TimetableVersion, Timetable, AttendanceSession,
    Attendance, AttendanceLog, Holiday, CorrectionRequest, LeaveApplication, Notification
)
from app.routes.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@login_required
@admin_required
def check_admin():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_classes = ClassGroup.query.count()
    total_subjects = Subject.query.count()
    total_sessions = AttendanceSession.query.count()
    total_corrections = CorrectionRequest.query.count()

    recent_sessions = AttendanceSession.query.order_by(AttendanceSession.created_at.desc()).limit(8).all()
    recent_logs = AttendanceLog.query.order_by(AttendanceLog.timestamp.desc()).limit(8).all()
    holidays = Holiday.query.order_by(Holiday.start_date).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_teachers=total_teachers,
        total_classes=total_classes,
        total_subjects=total_subjects,
        total_sessions=total_sessions,
        total_corrections=total_corrections,
        recent_sessions=recent_sessions,
        recent_logs=recent_logs,
        holidays=holidays
    )


# -------------------------------------------------------------
# TEACHERS MANAGEMENT (Editable Faculty & Assignments)
# -------------------------------------------------------------
@admin_bp.route('/teachers')
def teachers():
    all_teachers = Teacher.query.join(User).all()
    departments = Department.query.all()
    return render_template('admin/teachers.html', teachers=all_teachers, departments=departments)


@admin_bp.route('/teachers/add', methods=['POST'])
def add_teacher():
    full_name = request.form.get('full_name').strip()
    initials = request.form.get('initials').strip().upper()
    email = request.form.get('email').strip()
    emp_id = request.form.get('emp_id').strip()
    dept_id = request.form.get('department_id', type=int)
    designation = request.form.get('designation', 'Assistant Professor')
    password = request.form.get('password', 'Teacher@12345')

    if User.query.filter((User.email == email) | (User.username == initials.lower())).first():
        flash("Email or initials already in use.", "danger")
        return redirect(url_for('admin.teachers'))

    user = User(
        username=initials.lower(),
        email=email,
        full_name=full_name,
        role='teacher'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    teacher = Teacher(
        user_id=user.id,
        emp_id=emp_id,
        full_name=full_name,
        initials=initials,
        department_id=dept_id,
        designation=designation
    )
    db.session.add(teacher)
    db.session.commit()
    flash(f"Teacher {full_name} ({initials}) added successfully!", "success")
    return redirect(url_for('admin.teachers'))


@admin_bp.route('/teachers/edit/<int:teacher_id>', methods=['POST'])
def edit_teacher(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    teacher.full_name = request.form.get('full_name').strip()
    teacher.initials = request.form.get('initials').strip().upper()
    teacher.designation = request.form.get('designation').strip()
    teacher.emp_id = request.form.get('emp_id').strip()
    teacher.department_id = request.form.get('department_id', type=int)

    teacher.user.full_name = teacher.full_name
    teacher.user.email = request.form.get('email').strip()

    new_pass = request.form.get('new_password')
    if new_pass:
        teacher.user.set_password(new_pass)

    db.session.commit()
    flash(f"Teacher {teacher.full_name} updated successfully!", "success")
    return redirect(url_for('admin.teachers'))


# -------------------------------------------------------------
# STUDENTS MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/students')
def students():
    all_students = Student.query.join(User).all()
    classes = ClassGroup.query.all()
    departments = Department.query.all()
    return render_template('admin/students.html', students=all_students, classes=classes, departments=departments)


@admin_bp.route('/students/add', methods=['POST'])
def add_student():
    full_name = request.form.get('full_name').strip()
    roll_number = request.form.get('roll_number').strip().upper()
    email = request.form.get('email').strip()
    class_id = request.form.get('class_id', type=int)
    dept_id = request.form.get('department_id', type=int)
    guardian_phone = request.form.get('guardian_phone', '')
    password = request.form.get('password', 'Student@12345')

    if User.query.filter((User.email == email) | (User.username == roll_number.lower())).first():
        flash("Email or Roll number already in use.", "danger")
        return redirect(url_for('admin.students'))

    user = User(
        username=roll_number.lower(),
        email=email,
        full_name=full_name,
        role='student'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    student = Student(
        user_id=user.id,
        roll_number=roll_number,
        enroll_number=f"ENR{roll_number}",
        full_name=full_name,
        class_id=class_id,
        department_id=dept_id,
        guardian_phone=guardian_phone
    )
    db.session.add(student)
    db.session.commit()
    flash(f"Student {full_name} ({roll_number}) added successfully!", "success")
    return redirect(url_for('admin.students'))


# -------------------------------------------------------------
# TIMETABLE MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/timetable')
def timetable():
    classes = ClassGroup.query.all()
    active_class_id = request.args.get('class_id', type=int) or (classes[0].id if classes else None)
    
    selected_class = ClassGroup.query.get(active_class_id) if active_class_id else None
    version = TimetableVersion.query.filter_by(class_id=active_class_id, is_active=True).first() if active_class_id else None
    
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

    subjects = Subject.query.all()
    teachers = Teacher.query.all()

    return render_template(
        'admin/timetable.html',
        classes=classes,
        selected_class=selected_class,
        version=version,
        slots_by_day=slots_by_day,
        periods=periods,
        subjects=subjects,
        teachers=teachers
    )


@admin_bp.route('/timetable/edit-slot', methods=['POST'])
def edit_timetable_slot():
    slot_id = request.form.get('slot_id', type=int)
    subject_id = request.form.get('subject_id', type=int)
    teacher_id = request.form.get('teacher_id', type=int)
    room_number = request.form.get('room_number', '5208')
    period_type = request.form.get('period_type', 'Theory')

    slot = Timetable.query.get_or_404(slot_id)
    slot.subject_id = subject_id if subject_id else None
    slot.teacher_id = teacher_id if teacher_id else None
    slot.room_number = room_number
    slot.period_type = period_type

    db.session.commit()
    flash(f"Timetable slot ({slot.day_of_week} Period {slot.period_number}) updated!", "success")
    return redirect(url_for('admin.timetable', class_id=slot.class_id))


# -------------------------------------------------------------
# HOLIDAYS MANAGEMENT
# -------------------------------------------------------------
@admin_bp.route('/holidays', methods=['GET', 'POST'])
def holidays():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        description = request.form.get('description', '')

        hol = Holiday(name=name, start_date=start_date, end_date=end_date, description=description)
        db.session.add(hol)
        db.session.commit()
        flash(f"Holiday '{name}' added successfully!", "success")
        return redirect(url_for('admin.holidays'))

    all_holidays = Holiday.query.order_by(Holiday.start_date).all()
    return render_template('admin/holidays.html', holidays=all_holidays)


@admin_bp.route('/holidays/delete/<int:hol_id>', methods=['POST'])
def delete_holiday(hol_id):
    hol = Holiday.query.get_or_404(hol_id)
    db.session.delete(hol)
    db.session.commit()
    flash("Holiday deleted.", "info")
    return redirect(url_for('admin.holidays'))


# -------------------------------------------------------------
# AUDIT LOGS & BACKUP
# -------------------------------------------------------------
@admin_bp.route('/logs')
def logs():
    all_logs = AttendanceLog.query.order_by(AttendanceLog.timestamp.desc()).all()
    return render_template('admin/logs.html', logs=all_logs)


@admin_bp.route('/backup')
def backup_database():
    data = {
        'timestamp': datetime.utcnow().isoformat(),
        'users_count': User.query.count(),
        'students_count': Student.query.count(),
        'teachers_count': Teacher.query.count(),
        'sessions_count': AttendanceSession.query.count(),
        'attendance_records_count': Attendance.query.count()
    }
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=attendance_backup.json"}
    )

