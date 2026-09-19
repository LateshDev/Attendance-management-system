import io
from app.models import Student, BatchStudent


def test_student_creation(admin_client):
    response = admin_client.post('/students/new', data={
        'roll_number': 'TEST-500',
        'student_name': 'Carlos Santana',
        'email': 'carlos@example.com',
        'mobile_number': '9988776655',
        'admission_date': '2026-08-01',
        'status': 'Active'
    }, follow_redirects=True)
    assert response.status_code == 200

    student = Student.query.filter_by(roll_number='TEST-500').first()
    assert student is not None
    assert student.student_name == 'Carlos Santana'


def test_student_import_csv(admin_client, sample_data):
    batch_id = sample_data['batch_id']
    csv_content = (
        "roll_number,student_name,father_name,mother_name,mobile_number,email,date_of_birth,admission_date\n"
        "IMP-001,Kunal Ray,Sunil Ray,Rekha Ray,9800000001,kunal@test.com,2005-01-01,2026-01-01\n"
        "IMP-002,Simran Kaur,Jaswant Singh,Harjeet Kaur,9800000002,simran@test.com,2005-02-02,2026-01-01\n"
    )

    data = {
        'batch_id': str(batch_id),
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'students.csv')
    }

    response = admin_client.post('/students/import', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'Successfully Imported' in response.data

    st1 = Student.query.filter_by(roll_number='IMP-001').first()
    st2 = Student.query.filter_by(roll_number='IMP-002').first()
    assert st1 is not None
    assert st2 is not None

    # Check batch enrollment
    bs = BatchStudent.query.filter_by(batch_id=batch_id, student_id=st1.id).first()
    assert bs is not None
