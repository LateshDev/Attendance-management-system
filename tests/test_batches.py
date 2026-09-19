from datetime import date
from app.models import Batch, BatchStudent, Student


def test_batch_creation(admin_client):
    response = admin_client.post('/batches/new', data={
        'batch_name': 'Mechanical Engg 2026',
        'batch_code': 'MECH-2026',
        'course_name': 'B.Tech Mechanical',
        'start_date': '2026-08-01',
        'status': 'Active'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Mechanical Engg 2026' in response.data

    batch = Batch.query.filter_by(batch_code='MECH-2026').first()
    assert batch is not None
    assert batch.course_name == 'B.Tech Mechanical'


def test_batch_enrollment(admin_client, sample_data):
    batch_id = sample_data['batch_id']
    
    # Create new student
    student = Student(roll_number='NEW-99', student_name='New Enrollee', admission_date=date(2026, 1, 1))
    from app.models import db
    db.session.add(student)
    db.session.commit()

    response = admin_client.post(f'/batches/{batch_id}/enroll', data={
        'student_id': student.id
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'enrolled successfully' in response.data

    enrollment = BatchStudent.query.filter_by(batch_id=batch_id, student_id=student.id).first()
    assert enrollment is not None
    assert enrollment.status == 'Active'
