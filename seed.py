"""
Database Seed Script
Populates the database with roles, admin/teacher accounts, batches, subjects,
students, enrollments, leave requests, and 14 days of realistic attendance sessions.
"""
from datetime import date, timedelta
from app import create_app
from app.models import (
    db, Role, User, Batch, Subject, BatchSubject, Student, BatchStudent,
    AttendanceSession, AttendanceRecord, LeaveRequest, Setting, AuditLog
)

app = create_app('development')

def seed():
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()

        # 1. ROLES
        admin_role = Role.query.filter_by(name='ADMIN').first()
        if not admin_role:
            admin_role = Role(name='ADMIN', description='Full system administrator with unrestricted privileges')
            db.session.add(admin_role)

        teacher_role = Role.query.filter_by(name='TEACHER').first()
        if not teacher_role:
            teacher_role = Role(name='TEACHER', description='Academic staff with batch attendance marking access')
            db.session.add(teacher_role)

        db.session.commit()

        # 2. USERS (Admin & Teachers)
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            admin_user = User(
                email='admin@example.com',
                username='admin',
                full_name='System Administrator',
                phone='+91 9876500001',
                role_id=admin_role.id,
                is_active=True
            )
            admin_user.set_password('Admin@12345')
            db.session.add(admin_user)

        teacher1 = User.query.filter_by(email='teacher@example.com').first()
        if not teacher1:
            teacher1 = User(
                email='teacher@example.com',
                username='teacher',
                full_name='Prof. Ramesh Sharma',
                phone='+91 9876500002',
                role_id=teacher_role.id,
                is_active=True
            )
            teacher1.set_password('Teacher@12345')
            db.session.add(teacher1)

        teacher2 = User.query.filter_by(email='teacher2@example.com').first()
        if not teacher2:
            teacher2 = User(
                email='teacher2@example.com',
                username='ananya',
                full_name='Dr. Ananya Verma',
                phone='+91 9876500003',
                role_id=teacher_role.id,
                is_active=True
            )
            teacher2.set_password('Teacher@12345')
            db.session.add(teacher2)

        db.session.commit()

        # 3. SETTINGS
        Setting.set_value('institution_name', 'Metropolitan Institute of Commerce & Tech', 'Educational Institution Name')
        Setting.set_value('academic_session', '2026-2027', 'Active Academic Term')
        Setting.set_value('contact_email', 'admin@example.com', 'Admin Contact')
        Setting.set_value('low_attendance_threshold', '75.0', 'Minimum percentage for attendance warnings')

        # 4. SUBJECTS
        subjects_data = [
            ('Accountancy', 'ACC-101', 'Principles of Financial and Corporate Accounting'),
            ('Business Studies', 'BST-102', 'Management Theory and Commercial Practices'),
            ('Economics', 'ECO-103', 'Micro and Macro Economics Analysis'),
            ('English Core', 'ENG-104', 'Professional and Academic English Communication'),
            ('Computer Science', 'CS-105', 'Python Programming, SQL, and Network Architectures')
        ]
        created_subjects = {}
        for name, code, desc in subjects_data:
            s = Subject.query.filter_by(subject_code=code).first()
            if not s:
                s = Subject(subject_name=name, subject_code=code, description=desc, status='Active')
                db.session.add(s)
                db.session.flush()
            created_subjects[code] = s

        db.session.commit()

        # 5. BATCHES
        batches_data = [
            ('Commerce Batch A', 'COMM-A', 'Class 12 Commerce', teacher1.id),
            ('Commerce Batch B', 'COMM-B', 'Class 11 Commerce', teacher1.id),
            ('Computer Science Batch A', 'CS-A', 'Class 12 Computer Science', teacher2.id)
        ]
        created_batches = {}
        for b_name, b_code, c_name, t_id in batches_data:
            b = Batch.query.filter_by(batch_code=b_code).first()
            if not b:
                b = Batch(
                    batch_name=b_name,
                    batch_code=b_code,
                    course_name=c_name,
                    teacher_id=t_id,
                    start_date=date.today() - timedelta(days=60),
                    status='Active'
                )
                db.session.add(b)
                db.session.flush()
            created_batches[b_code] = b

        db.session.commit()

        # 6. BATCH-SUBJECT MAPPINGS
        mappings = [
            ('COMM-A', 'ACC-101', teacher1.id),
            ('COMM-A', 'BST-102', teacher1.id),
            ('COMM-A', 'ECO-103', teacher2.id),
            ('COMM-B', 'ACC-101', teacher1.id),
            ('COMM-B', 'ENG-104', teacher2.id),
            ('CS-A', 'CS-105', teacher2.id),
            ('CS-A', 'ENG-104', teacher1.id)
        ]
        for b_code, s_code, t_id in mappings:
            b_obj = created_batches[b_code]
            s_obj = created_subjects[s_code]
            existing = BatchSubject.query.filter_by(batch_id=b_obj.id, subject_id=s_obj.id).first()
            if not existing:
                bs = BatchSubject(batch_id=b_obj.id, subject_id=s_obj.id, teacher_id=t_id)
                db.session.add(bs)

        db.session.commit()

        # 7. STUDENTS (16 Realistic Students)
        students_info = [
            # Commerce Batch A students
            ('COM-001', 'Rahul Sharma', 'Vijay Sharma', 'Sunita Sharma', '9811001101', 'rahul.s@example.com', 'COMM-A'),
            ('COM-002', 'Aman Gupta', 'Rajesh Gupta', 'Meena Gupta', '9811001102', 'aman.g@example.com', 'COMM-A'),
            ('COM-003', 'Priya Patel', 'Suresh Patel', 'Geeta Patel', '9811001103', 'priya.p@example.com', 'COMM-A'),
            ('COM-004', 'Neha Kapoor', 'Sanjay Kapoor', 'Kiran Kapoor', '9811001104', 'neha.k@example.com', 'COMM-A'),
            ('COM-005', 'Vikram Singh', 'Mahendra Singh', 'Asha Singh', '9811001105', 'vikram.s@example.com', 'COMM-A'),
            ('COM-006', 'Aditya Joshi', 'Pramod Joshi', 'Rekha Joshi', '9811001106', 'aditya.j@example.com', 'COMM-A'),
            
            # Commerce Batch B students
            ('COM-101', 'Rohan Mehta', 'Alok Mehta', 'Seema Mehta', '9811001107', 'rohan.m@example.com', 'COMM-B'),
            ('COM-102', 'Anjali Nair', 'Soman Nair', 'Lakshmi Nair', '9811001108', 'anjali.n@example.com', 'COMM-B'),
            ('COM-103', 'Deepak Verma', 'Ramesh Verma', 'Sushma Verma', '9811001109', 'deepak.v@example.com', 'COMM-B'),
            ('COM-104', 'Kavita Rao', 'Satish Rao', 'Padma Rao', '9811001110', 'kavita.r@example.com', 'COMM-B'),
            ('COM-105', 'Manish Reddy', 'Venkat Reddy', 'Radha Reddy', '9811001111', 'manish.r@example.com', 'COMM-B'),

            # Computer Science Batch A students
            ('CS-001', 'Arjun Saxena', 'Manoj Saxena', 'Kavita Saxena', '9811001112', 'arjun.s@example.com', 'CS-A'),
            ('CS-002', 'Divya Iyer', 'Subramaniam Iyer', 'Vani Iyer', '9811001113', 'divya.i@example.com', 'CS-A'),
            ('CS-003', 'Karan Chopra', 'Harish Chopra', 'Pooja Chopra', '9811001114', 'karan.c@example.com', 'CS-A'),
            ('CS-004', 'Tanvi Bhatia', 'Deepak Bhatia', 'Renu Bhatia', '9811001115', 'tanvi.b@example.com', 'CS-A'),
            ('CS-005', 'Siddharth Jain', 'Naresh Jain', 'Anita Jain', '9811001116', 'siddharth.j@example.com', 'CS-A')
        ]

        created_students = {}
        for roll, s_name, f_name, m_name, mob, em, target_batch_code in students_info:
            st = Student.query.filter_by(roll_number=roll).first()
            if not st:
                st = Student(
                    roll_number=roll,
                    student_name=s_name,
                    father_name=f_name,
                    mother_name=m_name,
                    mobile_number=mob,
                    email=em,
                    date_of_birth=date(2006, 5, 10),
                    admission_date=date.today() - timedelta(days=60),
                    status='Active'
                )
                db.session.add(st)
                db.session.flush()

                # Enroll in target batch
                b_target = created_batches[target_batch_code]
                bs = BatchStudent(
                    batch_id=b_target.id,
                    student_id=st.id,
                    roll_number_in_batch=roll,
                    joined_date=date.today() - timedelta(days=60),
                    status='Active'
                )
                db.session.add(bs)
            created_students[roll] = st

        db.session.commit()

        # 8. LEAVE REQUESTS
        # Create an approved leave request for student Priya Patel (COM-003) for past 2 days and today
        priya = created_students.get('COM-003')
        comm_a = created_batches.get('COMM-A')
        if priya and comm_a:
            existing_leave = LeaveRequest.query.filter_by(student_id=priya.id).first()
            if not existing_leave:
                leave = LeaveRequest(
                    student_id=priya.id,
                    batch_id=comm_a.id,
                    start_date=date.today() - timedelta(days=2),
                    end_date=date.today() + timedelta(days=1),
                    reason='Fever and medical consultation with physician',
                    status='Approved',
                    reviewed_by_id=admin_user.id,
                    review_notes='Medical certificate submitted and verified.'
                )
                db.session.add(leave)
                db.session.commit()

        # 9. ATTENDANCE SESSIONS OVER PAST 10 DAYS
        # Generate rich historical attendance for COMM-A, COMM-B, CS-A
        print("Generating historical attendance sessions...")
        acc_subj = created_subjects['ACC-101']
        cs_subj = created_subjects['CS-105']

        for days_ago in range(10, 0, -1):
            sess_date = date.today() - timedelta(days=days_ago)
            # Skip Sundays
            if sess_date.weekday() == 6:
                continue

            # Batch A (Commerce)
            b_a = created_batches['COMM-A']
            exist_sess = AttendanceSession.query.filter_by(
                batch_id=b_a.id, subject_id=acc_subj.id, session_date=sess_date
            ).first()

            if not exist_sess:
                sess = AttendanceSession(
                    batch_id=b_a.id,
                    subject_id=acc_subj.id,
                    session_date=sess_date,
                    marked_by_id=teacher1.id,
                    remarks=f"Lecture {11 - days_ago}: Balance Sheet Accounting"
                )
                db.session.add(sess)
                db.session.flush()

                students_in_a = b_a.get_enrolled_students()
                for idx, st in enumerate(students_in_a):
                    # Check approved leave
                    if LeaveRequest.is_student_on_approved_leave(st.id, sess_date):
                        st_status = 'Leave'
                    elif st.roll_number == 'COM-005':
                        # Make Vikram Singh frequent defaulter (<70% attendance)
                        st_status = 'Absent' if days_ago % 2 == 0 else 'Present'
                    elif st.roll_number == 'COM-006' and days_ago <= 4:
                        # Make Aditya Joshi absent recently
                        st_status = 'Absent'
                    else:
                        st_status = 'Present'

                    rec = AttendanceRecord(
                        session_id=sess.id,
                        student_id=st.id,
                        status=st_status,
                        remarks='Regular class session'
                    )
                    db.session.add(rec)

            # CS-A Batch
            b_cs = created_batches['CS-A']
            exist_cs_sess = AttendanceSession.query.filter_by(
                batch_id=b_cs.id, subject_id=cs_subj.id, session_date=sess_date
            ).first()

            if not exist_cs_sess:
                cs_sess = AttendanceSession(
                    batch_id=b_cs.id,
                    subject_id=cs_subj.id,
                    session_date=sess_date,
                    marked_by_id=teacher2.id,
                    remarks=f"Practical Lab {11 - days_ago}: Python OOP"
                )
                db.session.add(cs_sess)
                db.session.flush()

                for st in b_cs.get_enrolled_students():
                    st_status = 'Absent' if (st.roll_number == 'CS-004' and days_ago % 3 == 0) else 'Present'
                    rec = AttendanceRecord(
                        session_id=cs_sess.id,
                        student_id=st.id,
                        status=st_status
                    )
                    db.session.add(rec)

        db.session.commit()

        # 10. AUDIT LOGS
        log_entry = AuditLog(
            user_id=admin_user.id,
            action='SYSTEM_INIT',
            module='SYSTEM',
            new_value='Database seeded successfully with demo records',
            ip_address='127.0.0.1'
        )
        db.session.add(log_entry)
        db.session.commit()

        print("=" * 60)
        print("DATABASE SEEDED SUCCESSFULLY!")
        print("Admin:   admin@example.com   / Admin@12345")
        print("Teacher: teacher@example.com / Teacher@12345")
        print("=" * 60)

if __name__ == '__main__':
    seed()
