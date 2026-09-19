from datetime import date
from app.models import db, AttendanceSession, AttendanceRecord


def test_batch_report_exports(admin_client, sample_data):
    b_id = sample_data['batch_id']
    sub_id = sample_data['subject_id']
    st1_id = sample_data['student1_id']

    # Create an attendance session
    sess = AttendanceSession(
        batch_id=b_id,
        subject_id=sub_id,
        session_date=date.today(),
        marked_by_id=sample_data['teacher_id']
    )
    db.session.add(sess)
    db.session.flush()

    rec = AttendanceRecord(session_id=sess.id, student_id=st1_id, status='Present')
    db.session.add(rec)
    db.session.commit()

    # CSV Export
    csv_res = admin_client.get(f'/reports/batch?batch_id={b_id}&export=csv')
    assert csv_res.status_code == 200
    assert 'text/csv' in csv_res.content_type
    assert b'Alice Smith' in csv_res.data

    # Excel Export
    xlsx_res = admin_client.get(f'/reports/batch?batch_id={b_id}&export=excel')
    assert xlsx_res.status_code == 200
    assert 'spreadsheetml' in xlsx_res.content_type

    # PDF Export
    pdf_res = admin_client.get(f'/reports/batch?batch_id={b_id}&export=pdf')
    assert pdf_res.status_code == 200
    assert 'application/pdf' in pdf_res.content_type
    assert pdf_res.data.startswith(b'%PDF')


def test_low_attendance_report(admin_client, sample_data):
    b_id = sample_data['batch_id']
    sub_id = sample_data['subject_id']
    st2_id = sample_data['student2_id']

    # Mark student2 Absent (0% attendance)
    sess = AttendanceSession(
        batch_id=b_id,
        subject_id=sub_id,
        session_date=date.today(),
        marked_by_id=sample_data['teacher_id']
    )
    db.session.add(sess)
    db.session.flush()

    rec = AttendanceRecord(session_id=sess.id, student_id=st2_id, status='Absent')
    db.session.add(rec)
    db.session.commit()

    # Low attendance report page
    res = admin_client.get('/reports/low-attendance?threshold=75')
    assert res.status_code == 200
    assert b'Bob Jones' in res.data

    # PDF Export of Low Attendance
    pdf_res = admin_client.get('/reports/low-attendance?threshold=75&export=pdf')
    assert pdf_res.status_code == 200
    assert pdf_res.data.startswith(b'%PDF')
