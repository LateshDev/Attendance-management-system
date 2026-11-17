from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# -------------------------------------------------------------
# 1. USERS & ROLES
# -------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # 'admin', 'hod', 'teacher', 'student'
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False, cascade='all, delete-orphan')
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# -------------------------------------------------------------
# 2. DEPARTMENTS
# -------------------------------------------------------------
class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    courses = db.relationship('Course', backref='department', lazy='dynamic')
    teachers = db.relationship('Teacher', backref='department', lazy='dynamic')
    classes = db.relationship('ClassGroup', backref='department', lazy='dynamic')


# -------------------------------------------------------------
# 3. COURSES
# -------------------------------------------------------------
class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    duration_years = db.Column(db.Integer, default=4)

    classes = db.relationship('ClassGroup', backref='course', lazy='dynamic')
    subjects = db.relationship('Subject', backref='course', lazy='dynamic')


# -------------------------------------------------------------
# 4. CLASSES (SECTIONS / BATCHES)
# -------------------------------------------------------------
class ClassGroup(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)  # e.g. "B.Tech CSE 3rd Year"
    section = db.Column(db.String(10), nullable=False)  # e.g. "V(C)"
    semester = db.Column(db.Integer, nullable=False, default=5)
    academic_year = db.Column(db.String(20), nullable=False, default="2026–27")
    room_number = db.Column(db.String(20), default="5208")

    students = db.relationship('Student', backref='class_group', lazy='dynamic')
    timetable_entries = db.relationship('Timetable', backref='class_group', lazy='dynamic')
    attendance_sessions = db.relationship('AttendanceSession', backref='class_group', lazy='dynamic')


# -------------------------------------------------------------
# 5. TEACHERS
# -------------------------------------------------------------
class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    emp_id = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    initials = db.Column(db.String(10), nullable=False, index=True)  # e.g. HBT, RPL, PMA
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation = db.Column(db.String(60), default="Assistant Professor")
    phone = db.Column(db.String(20), nullable=True)

    assigned_subjects = db.relationship('TeacherSubject', backref='teacher', lazy='dynamic', cascade='all, delete-orphan')
    timetable_slots = db.relationship('Timetable', backref='teacher', lazy='dynamic')
    sessions = db.relationship('AttendanceSession', backref='teacher', lazy='dynamic')


# -------------------------------------------------------------
# 6. STUDENTS
# -------------------------------------------------------------
class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    enroll_number = db.Column(db.String(40), unique=True, nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    semester = db.Column(db.Integer, default=5)
    admission_year = db.Column(db.Integer, default=2024)
    guardian_phone = db.Column(db.String(20), nullable=True)

    attendances = db.relationship('Attendance', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    correction_requests = db.relationship('CorrectionRequest', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    leave_applications = db.relationship('LeaveApplication', backref='student', lazy='dynamic', cascade='all, delete-orphan')


# -------------------------------------------------------------
# 7. SUBJECTS
# -------------------------------------------------------------
class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    semester = db.Column(db.Integer, nullable=False, default=5)
    code = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), default="Theory")  # Theory, Practical, Tutorial
    credits = db.Column(db.Integer, default=4)

    teacher_subjects = db.relationship('TeacherSubject', backref='subject', lazy='dynamic')
    timetable_entries = db.relationship('Timetable', backref='subject', lazy='dynamic')
    attendance_sessions = db.relationship('AttendanceSession', backref='subject', lazy='dynamic')


# -------------------------------------------------------------
# 8. TEACHER_SUBJECTS (Subject Allocations)
# -------------------------------------------------------------
class TeacherSubject(db.Model):
    __tablename__ = 'teacher_subjects'
    __table_args__ = (db.UniqueConstraint('teacher_id', 'subject_id', 'class_id', name='uq_teacher_subject_class'),)

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)


# -------------------------------------------------------------
# 9. TIMETABLE VERSIONS
# -------------------------------------------------------------
class TimetableVersion(db.Model):
    __tablename__ = 'timetable_versions'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    version_name = db.Column(db.String(60), default="Default Schedule 2026-27")
    effective_from = db.Column(db.Date, default=date(2026, 9, 12))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    slots = db.relationship('Timetable', backref='version', lazy='dynamic', cascade='all, delete-orphan')


# -------------------------------------------------------------
# 10. TIMETABLE
# -------------------------------------------------------------
class Timetable(db.Model):
    __tablename__ = 'timetable'
    __table_args__ = (
        db.UniqueConstraint('version_id', 'day_of_week', 'period_number', name='uq_version_day_period'),
    )

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('timetable_versions.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    day_of_week = db.Column(db.String(15), nullable=False)  # Monday, Tuesday, ...
    period_number = db.Column(db.Integer, nullable=False)   # 1, 2, 3, 4, 5
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)  # Nullable for Free/Library
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    room_number = db.Column(db.String(20), default="5208")
    period_type = db.Column(db.String(20), default="Theory")  # Theory, Lab, Tutorial, Free, Library


# -------------------------------------------------------------
# 11. ATTENDANCE SESSIONS
# -------------------------------------------------------------
class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    __table_args__ = (
        db.UniqueConstraint('class_id', 'subject_id', 'session_date', 'period_number', name='uq_session_class_sub_date_period'),
    )

    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False, default=date.today)
    period_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default="Open")  # Open, Closed, Cancelled
    topic_covered = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship('Attendance', backref='session', lazy='dynamic', cascade='all, delete-orphan')


# -------------------------------------------------------------
# 12. ATTENDANCE (Individual Records)
# -------------------------------------------------------------
class Attendance(db.Model):
    __tablename__ = 'attendance'
    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_session_student'),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    status = db.Column(db.String(15), nullable=False, default="Present")  # Present, Absent, Late, Leave
    remarks = db.Column(db.String(255), nullable=True)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    marker = db.relationship('User', foreign_keys=[marked_by])
    correction_requests = db.relationship('CorrectionRequest', backref='attendance_record', lazy='dynamic')
    logs = db.relationship('AttendanceLog', backref='attendance_record', lazy='dynamic')


# -------------------------------------------------------------
# 13. CORRECTION REQUESTS (4-Tier Workflow)
# -------------------------------------------------------------
class CorrectionRequest(db.Model):
    __tablename__ = 'correction_requests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    
    old_date = db.Column(db.Date, nullable=False)
    new_date = db.Column(db.Date, nullable=False)
    old_status = db.Column(db.String(15), nullable=False)
    new_status = db.Column(db.String(15), nullable=False)
    reason = db.Column(db.Text, nullable=False)

    # Teacher verification stage
    teacher_status = db.Column(db.String(20), default="Pending")  # Pending, Verified, Rejected
    teacher_remarks = db.Column(db.String(255), nullable=True)
    teacher_verified_at = db.Column(db.DateTime, nullable=True)

    # HOD approval stage
    hod_status = db.Column(db.String(20), default="Pending")  # Pending, Approved, Rejected
    hod_remarks = db.Column(db.String(255), nullable=True)
    hod_reviewed_at = db.Column(db.DateTime, nullable=True)

    # Admin exceptional override
    admin_action = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    session = db.relationship('AttendanceSession', foreign_keys=[session_id])
    teacher = db.relationship('Teacher', foreign_keys=[teacher_id])


# -------------------------------------------------------------
# 14. ATTENDANCE LOGS (Audit Trail)
# -------------------------------------------------------------
class AttendanceLog(db.Model):
    __tablename__ = 'attendance_logs'

    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    modified_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    old_status = db.Column(db.String(15), nullable=False)
    new_status = db.Column(db.String(15), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # Correction Request Approval, Admin Override, Manual Edit
    reason = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    modifier = db.relationship('User', foreign_keys=[modified_by_user_id])


# -------------------------------------------------------------
# 15. NOTIFICATIONS
# -------------------------------------------------------------
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default="info")  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------------------------------------------------
# 16. HOLIDAYS
# -------------------------------------------------------------
class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    academic_year = db.Column(db.String(20), default="2026–27")


# -------------------------------------------------------------
# 17. LEAVE APPLICATIONS
# -------------------------------------------------------------
class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

