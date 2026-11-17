from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 'ADMIN', 'TEACHER', 'STUDENT'
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
    initials = db.Column(db.String(10), nullable=True, index=True)
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
    def is_hod(self):
        return self.role is not None and self.role.name == 'HOD'

    @property
    def is_teacher(self):
        return self.role is not None and self.role.name == 'TEACHER'

    @property
    def is_student(self):
        return self.role is not None and self.role.name == 'STUDENT'

    @property
    def student(self):
        return getattr(self, 'student_profile', None)

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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('student_profile', uselist=False))
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

    def calculate_subject_wise_stats(self, threshold=75.0):
        """
        Calculate subject-wise attendance statistics with classes needed or bunk margin.
        """
        import math
        batches = self.get_batches()
        results = []
        seen_subjects = set()

        for batch in batches:
            batch_subjs = BatchSubject.query.filter_by(batch_id=batch.id).all()
            for bs in batch_subjs:
                subj = bs.subject
                if not subj or subj.status != 'Active':
                    continue
                key = (batch.id, subj.id)
                if key in seen_subjects:
                    continue
                seen_subjects.add(key)

                stats = self.calculate_attendance_stats(batch_id=batch.id, subject_id=subj.id)
                total = stats['total_classes']
                present = stats['present']
                pct = stats['percentage']

                # Target threshold calculations
                if total == 0:
                    classes_needed = 0
                    bunk_margin = 0
                elif pct < threshold:
                    t_frac = threshold / 100.0
                    needed = math.ceil((t_frac * total - present) / (1.0 - t_frac)) if (1.0 - t_frac) > 0 else 0
                    classes_needed = max(0, int(needed))
                    bunk_margin = 0
                else:
                    t_frac = threshold / 100.0
                    margin = math.floor((present - t_frac * total) / t_frac) if t_frac > 0 else 0
                    classes_needed = 0
                    bunk_margin = max(0, int(margin))

                teacher = User.query.get(bs.teacher_id) if bs.teacher_id else batch.teacher

                results.append({
                    'batch': batch,
                    'subject': subj,
                    'teacher': teacher,
                    'stats': stats,
                    'classes_needed': classes_needed,
                    'bunk_margin': bunk_margin,
                    'is_low': (total > 0 and pct < threshold)
                })

        return results

    def ensure_user_account(self, default_password='Student@12345'):
        """
        Ensure this student has an associated User account with role STUDENT.
        Sets username to lowercase roll_number and connects user_id.
        """
        student_role = Role.query.filter_by(name='STUDENT').first()
        if not student_role:
            student_role = Role(
                name='STUDENT',
                description='Student account with access to personal attendance records and leave applications'
            )
            db.session.add(student_role)
            db.session.flush()

        if self.user:
            self.user.full_name = self.student_name
            self.user.phone = self.mobile_number
            self.user.is_active = (self.status == 'Active')
            if not self.user.role_id:
                self.user.role_id = student_role.id
            return self.user

        # Generate a unique username based on roll_number
        base_username = self.roll_number.strip().lower().replace(' ', '_')
        username = base_username
        existing_u = User.query.filter_by(username=username).first()
        if existing_u and existing_u.id != self.user_id:
            username = f"{base_username}_{self.id or 1}"

        # Email determination
        if self.email and self.email.strip():
            candidate_email = self.email.strip().lower()
            existing_email = User.query.filter_by(email=candidate_email).first()
            if existing_email and existing_email.id != self.user_id:
                candidate_email = f"{base_username}@student.local"
        else:
            candidate_email = f"{base_username}@student.local"

        existing_cand = User.query.filter_by(email=candidate_email).first()
        if existing_cand and existing_cand.id != self.user_id:
            candidate_email = f"{base_username}_{self.id or 1}@student.local"

        user = User(
            email=candidate_email,
            username=username,
            full_name=self.student_name,
            phone=self.mobile_number,
            is_active=(self.status == 'Active'),
            role_id=student_role.id
        )
        user.set_password(default_password)
        db.session.add(user)
        db.session.flush()

        self.user_id = user.id
        return user

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


class TimetableVersion(db.Model):
    __tablename__ = 'timetable_versions'

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    version_name = db.Column(db.String(80), default="Official Timetable 2026-27")
    effective_from = db.Column(db.Date, default=date(2026, 9, 12))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batch = db.relationship('Batch', backref=db.backref('timetable_versions', lazy='dynamic'))
    slots = db.relationship('Timetable', backref='version', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<TimetableVersion {self.version_name}>"


class Timetable(db.Model):
    __tablename__ = 'timetable'

    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('timetable_versions.id', ondelete='CASCADE'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True)
    day_of_week = db.Column(db.String(15), nullable=False)  # Monday .. Saturday
    period_number = db.Column(db.Integer, nullable=False)   # 1 .. 5
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    room_number = db.Column(db.String(20), default="5208")
    period_type = db.Column(db.String(20), default="Theory")  # Theory, Practical, Tutorial, Free, Library

    batch = db.relationship('Batch', backref=db.backref('timetable_slots', lazy='dynamic'))
    subject = db.relationship('Subject')
    teacher = db.relationship('User', foreign_keys=[teacher_id])

    __table_args__ = (
        db.UniqueConstraint('version_id', 'day_of_week', 'period_number', name='uq_tt_version_day_period'),
    )

    def __repr__(self):
        return f"<Timetable {self.day_of_week} P{self.period_number}: {self.subject.subject_code if self.subject else 'Free'}>"


class CorrectionRequest(db.Model):
    __tablename__ = 'correction_requests'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False, index=True)
    record_id = db.Column(db.Integer, db.ForeignKey('attendance_records.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id', ondelete='CASCADE'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    old_date = db.Column(db.Date, nullable=False)
    new_date = db.Column(db.Date, nullable=False)
    old_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)

    # Teacher verification stage
    teacher_status = db.Column(db.String(20), default='Pending', nullable=False)  # Pending, Verified, Rejected
    teacher_remarks = db.Column(db.String(255), nullable=True)
    teacher_verified_at = db.Column(db.DateTime, nullable=True)

    # HOD approval stage
    hod_status = db.Column(db.String(20), default='Pending', nullable=False)  # Pending, Approved, Rejected
    hod_remarks = db.Column(db.String(255), nullable=True)
    hod_reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship('Student', backref=db.backref('correction_requests', lazy='dynamic'))
    record = db.relationship('AttendanceRecord', backref=db.backref('correction_requests', lazy='dynamic'))
    session = db.relationship('AttendanceSession', foreign_keys=[session_id])
    teacher = db.relationship('User', foreign_keys=[teacher_id])

    def __repr__(self):
        return f"<CorrectionRequest #{self.id} Student:{self.student_id} Status:{self.hod_status}>"


def auto_migrate_schema():
    """Ensure newly added columns and tables are migrated to existing databases (PostgreSQL & SQLite)."""
    from sqlalchemy import text
    try:
        dialect = db.engine.dialect.name
    except Exception:
        dialect = 'postgresql'

    print(f"Auto-migration: Starting schema migration pass for dialect '{dialect}'...")

    if dialect == 'postgresql':
        pg_statements = [
            ("users.initials", "ALTER TABLE users ADD COLUMN IF NOT EXISTS initials VARCHAR(10);"),
            ("users.ix_users_initials", "CREATE INDEX IF NOT EXISTS ix_users_initials ON users (initials);"),
            ("students.user_id", "ALTER TABLE students ADD COLUMN IF NOT EXISTS user_id INTEGER;"),
            ("students.ix_students_user_id", "CREATE INDEX IF NOT EXISTS ix_students_user_id ON students (user_id);"),
            ("students.fk_students_user_id", """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_students_user_id'
                    ) THEN
                        ALTER TABLE students
                            ADD CONSTRAINT fk_students_user_id
                            FOREIGN KEY (user_id) REFERENCES users(id)
                            ON DELETE SET NULL;
                    END IF;
                END $$;
            """),
            ("batches.course_name", "ALTER TABLE batches ADD COLUMN IF NOT EXISTS course_name VARCHAR(120);"),
            ("batches.teacher_id", "ALTER TABLE batches ADD COLUMN IF NOT EXISTS teacher_id INTEGER;"),
            ("batches.status", "ALTER TABLE batches ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Active';"),
            ("subjects.status", "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Active';"),
            ("batch_students.status", "ALTER TABLE batch_students ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Active';"),
            ("batch_students.roll_number_in_batch", "ALTER TABLE batch_students ADD COLUMN IF NOT EXISTS roll_number_in_batch VARCHAR(50);"),
            ("leave_requests.reviewed_by_id", "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS reviewed_by_id INTEGER;"),
            ("leave_requests.review_notes", "ALTER TABLE leave_requests ADD COLUMN IF NOT EXISTS review_notes VARCHAR(255);"),
            ("attendance_sessions.remarks", "ALTER TABLE attendance_sessions ADD COLUMN IF NOT EXISTS remarks VARCHAR(255);"),
            ("attendance_records.remarks", "ALTER TABLE attendance_records ADD COLUMN IF NOT EXISTS remarks VARCHAR(255);"),
        ]

        for desc, stmt in pg_statements:
            try:
                with db.engine.begin() as conn:
                    conn.execute(text(stmt))
                print(f"Auto-migration: Ensured {desc} exists (PostgreSQL).")
            except Exception as pg_err:
                print(f"Auto-migration notice for {desc} (PostgreSQL):", pg_err)

    else:
        # SQLite or other SQL databases
        sqlite_columns = [
            ("users", "initials", "VARCHAR(10)"),
            ("students", "user_id", "INTEGER"),
            ("batches", "course_name", "VARCHAR(120)"),
            ("batches", "teacher_id", "INTEGER"),
            ("batches", "status", "VARCHAR(20) DEFAULT 'Active'"),
            ("subjects", "status", "VARCHAR(20) DEFAULT 'Active'"),
            ("batch_students", "status", "VARCHAR(20) DEFAULT 'Active'"),
            ("batch_students", "roll_number_in_batch", "VARCHAR(50)"),
            ("leave_requests", "reviewed_by_id", "INTEGER"),
            ("leave_requests", "review_notes", "VARCHAR(255)"),
            ("attendance_sessions", "remarks", "VARCHAR(255)"),
            ("attendance_records", "remarks", "VARCHAR(255)"),
        ]

        for table, col, col_type in sqlite_columns:
            try:
                with db.engine.begin() as conn:
                    table_exists = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")).fetchone()
                    if table_exists:
                        existing_cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table});")).fetchall()]
                        if col not in existing_cols:
                            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                            print(f"Auto-migration: Added {col} to {table} (SQLite).")
            except Exception as sqlite_err:
                print(f"Auto-migration notice for {table}.{col} (SQLite):", sqlite_err)

    print("Auto-migration: Schema migration pass completed.")


def sync_all_student_accounts(default_password='Student@12345'):
    """Synchronize user accounts for all student records in the database."""
    students = Student.query.all()
    updated = 0
    for st in students:
        if not st.user_id or not st.user:
            st.ensure_user_account(default_password=default_password)
            updated += 1
    if updated > 0:
        db.session.commit()
    return updated

