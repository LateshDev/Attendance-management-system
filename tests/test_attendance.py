from datetime import date
from app.models import db, AttendanceSession, AttendanceRecord, Student, AuditLog


def test_attendance_creation(admin_client, sample_data):
    b_id = sample_data['batch_id']
    sub_id = sample_data['subject_id']
    st1_id = sample_data['student1_id']
    st2_id = sample_data['student2_id']
    today_str = date.today().strftime('%Y-%m-%d')

    post_data = {
        'batch_id': str(b_id),
        'subject_id': str(sub_id),
        'session_date': today_str,
        f'status_{st1_id}': 'Present',
        f'status_{st2_id}': 'Absent',
        'session_remarks': 'Unit Test Session'
    }

    response = admin_client.post('/attendance/mark', data=post_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Attendance marked successfully' in response.data

    session_obj = AttendanceSession.query.filter_by(batch_id=b_id, subject_id=sub_id, session_date=date.today()).first()
    assert session_obj is not None
    assert session_obj.total_records == 2
    assert session_obj.present_count == 1
    assert session_obj.absent_count == 1
    assert session_obj.attendance_percentage == 50.0


def test_duplicate_attendance_prevention(admin_client, sample_data):
    b_id = sample_data['batch_id']
    sub_id = sample_data['subject_id']
    st1_id = sample_data['student1_id']
    today_str = date.today().strftime('%Y-%m-%d')

    # First mark
    admin_client.post('/attendance/mark', data={
        'batch_id': str(b_id),
        'subject_id': str(sub_id),
        'session_date': today_str,
        f'status_{st1_id}': 'Present'
    }, follow_redirects=True)

    # Attempt duplicate mark on same date, batch, and subject
    response = admin_client.post('/attendance/mark', data={
        'batch_id': str(b_id),
        'subject_id': str(sub_id),
        'session_date': today_str,
        f'status_{st1_id}': 'Present'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Attendance has already been marked' in response.data


def test_edit_attendance_with_audit(admin_client, sample_data):
    b_id = sample_data['batch_id']
    sub_id = sample_data['subject_id']
    st1_id = sample_data['student1_id']
    st2_id = sample_data['student2_id']
    today_str = date.today().strftime('%Y-%m-%d')

    # Create session
    admin_client.post('/attendance/mark', data={
        'batch_id': str(b_id),
        'subject_id': str(sub_id),
        'session_date': today_str,
        f'status_{st1_id}': 'Absent',
        f'status_{st2_id}': 'Absent'
    }, follow_redirects=True)

    session_obj = AttendanceSession.query.filter_by(batch_id=b_id, subject_id=sub_id, session_date=date.today()).first()

    # Edit student1 from Absent to Present
    edit_response = admin_client.post(f'/attendance/session/{session_obj.id}/edit', data={
        f'status_{st1_id}': 'Present',
        f'status_{st2_id}': 'Absent',
        'session_remarks': 'Corrected attendance'
    }, follow_redirects=True)

    assert edit_response.status_code == 200

    rec1 = AttendanceRecord.query.filter_by(session_id=session_obj.id, student_id=st1_id).first()
    assert rec1.status == 'Present'

    # Check audit log
    audit = AuditLog.query.filter_by(action='EDIT_ATTENDANCE').first()
    assert audit is not None
    assert 'Absent -> Present' in audit.new_value


def test_attendance_math_safety(app, sample_data):
    with app.app_context():
        st = Student.query.get(sample_data['student1_id'])
        # 0 classes held
        stats_zero = st.calculate_attendance_stats()
        assert stats_zero['total_classes'] == 0
        assert stats_zero['percentage'] == 0.0
        assert not isinstance(stats_zero['percentage'], str)
