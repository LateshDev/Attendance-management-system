from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 'ADMIN', 'TEACHER'
    description = db.Column(db.String(200), nullable=True)

    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_batches = db.relationship('Batch', backref='teacher', lazy='dynamic', foreign_keys='Batch.teacher_id')
    marked_sessions = db.relationship('AttendanceSession', backref='marked_by', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role is not None and self.role.name == 'ADMIN'

    @property
    def is_teacher(self):
        return self.role is not None and self.role.name == 'TEACHER'

    @property
    def avatar_initials(self):
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        elif len(parts) == 1 and len(parts[0]) > 0:
            return parts[0][:2].upper()
        return "U"

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"


class Batch(db.Model):
    __tablename__ = 'batches'

    id = db.Column(db.Integer, primary_key=True)
    batch_name = db.Column(db.String(120), nullable=False, index=True)
    batch_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    course_name = db.Column(db.String(120), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False)  # 'Active', 'Archived'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollments = db.relationship('BatchStudent', backref='batch', lazy='dynamic', cascade='all, delete-orphan')
    sessions = db.relationship('AttendanceSession', backref='batch', lazy='dynamic', cascade='all, delete-orphan')
    batch_subjects = db.relationship('BatchSubject', backref='batch', lazy='dynamic', cascade='all, delete-orphan')
    leave_requests = db.relationship('LeaveRequest', backref='batch', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def active_students_count(self):
        return self.enrollments.filter_by(status='Active').count()

    def get_enrolled_students(self):
        return Student.query.join(BatchStudent).filter(
            BatchStudent.batch_id == self.id,
            BatchStudent.status == 'Active',
            Student.status == 'Active'
        ).order_by(Student.roll_number).all()

    def __repr__(self):
        return f"<Batch {self.batch_code}: {self.batch_name}>"


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    student_name = db.Column(db.String(120), nullable=False, index=True)
    father_name = db.Column(db.String(120), nullable=True)
    mother_name = db.Column(db.String(120), nullable=True)
    mobile_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    admission_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), default='Active', nullable=False)  # 'Active', 'Inactive'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    enrollments = db.relationship('BatchStudent', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    leave_requests = db.relationship('LeaveRequest', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    def get_batches(self):
        return Batch.query.join(BatchStudent).filter(
            BatchStudent.student_id == self.id,
            BatchStudent.status == 'Active'
        ).all()

    def calculate_attendance_stats(self, batch_id=None, subject_id=None, start_date=None, end_date=None):
        """
        Calculate total classes, present, absent, leave, and percentage.
        Excludes future dates and ensures safe math (no division by zero).
        """
        query = AttendanceRecord.query.join(AttendanceSession).filter(
            AttendanceRecord.student_id == self.id,
            AttendanceSession.session_date <= date.today()
        )

        if batch_id:
            query = query.filter(AttendanceSession.batch_id == batch_id)
        if subject_id:
            query = query.filter(AttendanceSession.subject_id == subject_id)
        if start_date:
            query = query.filter(AttendanceSession.session_date >= start_date)
        if end_date:
            query = query.filter(AttendanceSession.session_date <= end_date)

        records = query.all()
        total_classes = len(records)
        present_count = sum(1 for r in records if r.status == 'Present')
        absent_count = sum(1 for r in records if r.status == 'Absent')
        leave_count = sum(1 for r in records if r.status == 'Leave')

        if total_classes == 0:
            percentage = 0.0
        else:
            percentage = round((present_count / total_classes) * 100.0, 2)

        # Ensure percentage never exceeds 100% and never negative
        percentage = max(0.0, min(100.0, percentage))

        return {
            'total_classes': total_classes,
            'present': present_count,
            'absent': absent_count,
            'leave': leave_count,
            'percentage': percentage
        }

    def __repr__(self):
        return f"<Student {self.roll_number}: {self.student_name}>"


class BatchStudent(db.Model):
    __tablename__ = 'batch_students'

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    roll_number_in_batch = db.Column(db.String(50), nullable=True)
    joined_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), default='Active', nullable=False)  # 'Active', 'Removed'

    __table_args__ = (
        db.UniqueConstraint('batch_id', 'student_id', name='uq_batch_student'),
    )

    def __repr__(self):
        return f"<BatchStudent Batch:{self.batch_id} Student:{self.student_id}>"


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(120), nullable=False, index=True)
    subject_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False)  # 'Active', 'Inactive'

    # Relationships
    batch_subjects = db.relationship('BatchSubject', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    sessions = db.relationship('AttendanceSession', backref='subject', lazy='dynamic')

    def __repr__(self):
        return f"<Subject {self.subject_code}: {self.subject_name}>"


class BatchSubject(db.Model):
    __tablename__ = 'batch_subjects'

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('batch_id', 'subject_id', name='uq_batch_subject'),
    )

    def __repr__(self):
        return f"<BatchSubject Batch:{self.batch_id} Subject:{self.subject_id}>"


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    session_date = db.Column(db.Date, nullable=False, index=True)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    remarks = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to individual student records
    records = db.relationship('AttendanceRecord', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('batch_id', 'subject_id', 'session_date', name='uq_batch_subject_date'),
    )

    @property
    def total_records(self):
        return self.records.count()

    @property
    def present_count(self):
        return self.records.filter_by(status='Present').count()

    @property
    def absent_count(self):
        return self.records.filter_by(status='Absent').count()

    @property
    def leave_count(self):
        return self.records.filter_by(status='Leave').count()

    @property
    def attendance_percentage(self):
        total = self.total_records
        if total == 0:
            return 0.0
        return round((self.present_count / total) * 100.0, 2)

    def __repr__(self):
        return f"<AttendanceSession Batch:{self.batch_id} Subj:{self.subject_id} Date:{self.session_date}>"


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # 'Present', 'Absent', 'Leave'
    remarks = db.Column(db.String(255), nullable=True)
    marked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('session_id', 'student_id', name='uq_session_student'),
    )

    def __repr__(self):
        return f"<AttendanceRecord Session:{self.session_id} Student:{self.student_id} Status:{self.status}>"


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending', nullable=False)  # 'Pending', 'Approved', 'Rejected'
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Reviewer relationship
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])

    @classmethod
    def is_student_on_approved_leave(cls, student_id, target_date):
        """Check if student has an approved leave request on a specific date."""
        return cls.query.filter(
            cls.student_id == student_id,
            cls.status == 'Approved',
            cls.start_date <= target_date,
            cls.end_date >= target_date
        ).first() is not None

    def __repr__(self):
        return f"<LeaveRequest Student:{self.student_id} Status:{self.status}>"


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # e.g., 'CREATE_ATTENDANCE', 'UPDATE_ATTENDANCE', etc.
    module = db.Column(db.String(50), nullable=False)   # e.g., 'ATTENDANCE', 'BATCH', 'STUDENT'
    record_id = db.Column(db.String(50), nullable=True)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.module} at {self.timestamp}>"


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_value(cls, key, default=None):
        item = cls.query.filter_by(key=key).first()
        return item.value if item else default

    @classmethod
    def set_value(cls, key, value, description=None):
        item = cls.query.filter_by(key=key).first()
        if not item:
            item = cls(key=key, value=str(value), description=description)
            db.session.add(item)
        else:
            item.value = str(value)
            if description:
                item.description = description
        db.session.commit()
        return item

    def __repr__(self):
        return f"<Setting {self.key}={self.value}>"
