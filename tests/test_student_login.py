import pytest
from app.models import db, Student, User, Role, LeaveRequest


def test_student_login_with_roll_number(client, sample_data):
    """Verify student can log in using roll number and access attendance dashboard."""
    response = client.post('/auth/login', data={
        'login_id': 'ST-001',
        'password': 'Student@12345'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"My Attendance" in response.data
    assert b"Alice Smith" in response.data
    assert b"ST-001" in response.data


def test_student_login_case_insensitive(client, sample_data):
    """Verify student login is case-insensitive for roll number."""
    response = client.post('/auth/login', data={
        'login_id': 'st-001',
        'password': 'Student@12345'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Alice Smith" in response.data


def test_student_login_with_email(client, sample_data):
    """Verify student can log in using their email address."""
    response = client.post('/auth/login', data={
        'login_id': 'alice@test.com',
        'password': 'Student@12345'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Alice Smith" in response.data


def test_student_dashboard_redirection(student_client):
    """Verify that root dashboard `/` redirects student to `/students/my-attendance`."""
    response = student_client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b"My Attendance" in response.data
    assert b"Subject-Wise Attendance Breakdown" in response.data


def test_student_forbidden_from_admin_and_staff_routes(student_client, sample_data):
    """Verify student cannot access staff-only routes."""
    # Attempt mark attendance
    res1 = student_client.get('/attendance/mark')
    assert res1.status_code in [403, 302]

    # Attempt view all batches
    res2 = student_client.get('/batches/')
    assert res2.status_code in [403, 302]

    # Attempt create batch
    res3 = student_client.get('/batches/new')
    assert res3.status_code in [403, 302]

    # Attempt view all students list
    res4 = student_client.get('/students/')
    assert res4.status_code in [403, 302]

    # Attempt user management
    res5 = student_client.get('/auth/users')
    assert res5.status_code in [403, 302]

    # Attempt system settings
    res6 = student_client.get('/settings/')
    assert res6.status_code in [403, 302]


def test_student_cannot_view_other_student_profile(student_client, sample_data):
    """Verify student cannot view another student's profile."""
    other_id = sample_data['student2_id']
    response = student_client.get(f'/students/{other_id}')
    assert response.status_code == 403


def test_student_own_profile_redirects_to_my_attendance(student_client, sample_data):
    """Verify accessing student's own profile id redirects to my-attendance."""
    own_id = sample_data['student1_id']
    response = student_client.get(f'/students/{own_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"My Attendance" in response.data


def test_student_leave_application(student_client, sample_data):
    """Verify student can apply for leave and view their submitted request."""
    post_data = {
        'batch_id': sample_data['batch_id'],
        'student_id': sample_data['student1_id'],
        'start_date': '2026-11-10',
        'end_date': '2026-11-12',
        'reason': 'Medical checkup and doctor consultation appointment'
    }
    response = student_client.post('/leaves/new', data=post_data, follow_redirects=True)
    assert response.status_code == 200

    # Verify on leaves index
    leaves_res = student_client.get('/leaves/')
    assert leaves_res.status_code == 200
    assert b"Medical checkup" in leaves_res.data


def test_student_attendance_export(student_client):
    """Verify student can export attendance in CSV and PDF."""
    csv_res = student_client.get('/students/my-attendance/export?format=csv')
    assert csv_res.status_code == 200
    assert csv_res.mimetype == 'text/csv'
    assert b'Alice Smith' in csv_res.data
    assert b'ST-001' in csv_res.data

    pdf_res = student_client.get('/students/my-attendance/export?format=pdf')
    assert pdf_res.status_code == 200
    assert pdf_res.mimetype == 'application/pdf'
    assert pdf_res.data.startswith(b'%PDF')
