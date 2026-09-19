import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date
from app import create_app
from app.models import db, Role, User, Batch, Student, BatchStudent, Subject, Setting


@pytest.fixture
def app():
    test_app = create_app('testing')
    with test_app.app_context():
        db.create_all()

        # Seed roles
        admin_role = Role(name='ADMIN', description='Administrator')
        teacher_role = Role(name='TEACHER', description='Teacher')
        db.session.add_all([admin_role, teacher_role])
        db.session.commit()

        # Seed users
        admin_user = User(
            email='admin@test.com',
            username='admin',
            full_name='Test Admin',
            role_id=admin_role.id,
            is_active=True
        )
        admin_user.set_password('Admin@12345')

        teacher_user = User(
            email='teacher@test.com',
            username='teacher',
            full_name='Test Teacher',
            role_id=teacher_role.id,
            is_active=True
        )
        teacher_user.set_password('Teacher@12345')

        db.session.add_all([admin_user, teacher_user])
        db.session.commit()

        # Seed settings
        Setting.set_value('low_attendance_threshold', '75.0')
        Setting.set_value('institution_name', 'Test Academy')

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(app):
    c = app.test_client()
    c.post('/auth/login', data={'login_id': 'admin@test.com', 'password': 'Admin@12345'}, follow_redirects=True)
    return c


@pytest.fixture
def teacher_client(app):
    c = app.test_client()
    c.post('/auth/login', data={'login_id': 'teacher@test.com', 'password': 'Teacher@12345'}, follow_redirects=True)
    return c


@pytest.fixture
def sample_data(app):
    with app.app_context():
        teacher = User.query.filter_by(username='teacher').first()

        batch = Batch(
            batch_name='Test Batch Alpha',
            batch_code='TBA-01',
            course_name='Computer Science',
            teacher_id=teacher.id,
            start_date=date(2026, 1, 1),
            status='Active'
        )
        db.session.add(batch)
        db.session.flush()

        subject = Subject(
            subject_name='Python Programming',
            subject_code='PY-101',
            status='Active'
        )
        db.session.add(subject)
        db.session.flush()

        student1 = Student(
            roll_number='ST-001',
            student_name='Alice Smith',
            email='alice@test.com',
            admission_date=date(2026, 1, 1),
            status='Active'
        )
        student2 = Student(
            roll_number='ST-002',
            student_name='Bob Jones',
            email='bob@test.com',
            admission_date=date(2026, 1, 1),
            status='Active'
        )
        db.session.add_all([student1, student2])
        db.session.flush()

        bs1 = BatchStudent(batch_id=batch.id, student_id=student1.id, status='Active')
        bs2 = BatchStudent(batch_id=batch.id, student_id=student2.id, status='Active')
        db.session.add_all([bs1, bs2])
        db.session.commit()

        return {
            'batch_id': batch.id,
            'subject_id': subject.id,
            'student1_id': student1.id,
            'student2_id': student2.id,
            'teacher_id': teacher.id
        }
