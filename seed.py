"""
Database Seed Script
Populates the database with roles, admin/HOD/teacher accounts, B.Tech CSE 3rd Year V(C) batch,
official subjects, the complete Monday-Saturday timetable, students, and demo attendance.
"""
from datetime import date, time, timedelta
from app.models import (
    db, Role, User, Batch, Subject, BatchSubject, Student, BatchStudent,
    AttendanceSession, AttendanceRecord, LeaveRequest, Setting, AuditLog,
    TimetableVersion, Timetable
)

def seed(target_app=None):
    def run_seed():
        from app.models import auto_migrate_schema
        auto_migrate_schema()

        print("Ensuring all database tables exist...")
        db.create_all()

        # -------------------------------------------------------------
        # 1. ROLES (ADMIN, HOD, TEACHER, STUDENT)
        # -------------------------------------------------------------
        roles_data = [
            ('ADMIN', 'Full system administrator with unrestricted privileges'),
            ('HOD', 'Head of Department with attendance correction authorization and academic oversight'),
            ('TEACHER', 'Academic faculty member with timetable lecture marking access'),
            ('STUDENT', 'Student account with access to attendance records, correction disputes, and leave requests')
        ]
        roles_map = {}
        for rname, rdesc in roles_data:
            role = Role.query.filter_by(name=rname).first()
            if not role:
                role = Role(name=rname, description=rdesc)
                db.session.add(role)
                db.session.flush()
            roles_map[rname] = role

        db.session.commit()

        # -------------------------------------------------------------
        # 2. SETTINGS (Faculty of Technology and Computer Applications)
        # -------------------------------------------------------------
        Setting.set_value('institution_name', 'Faculty of Technology and Computer Applications', 'Institution Name')
        Setting.set_value('academic_session', '2026–27', 'Active Academic Session')
        Setting.set_value('contact_email', 'admin@example.com', 'Admin Contact')
        Setting.set_value('low_attendance_threshold', '75.0', 'Defaulter Warning Threshold Percentage')

        # -------------------------------------------------------------
        # 3. USERS (Admin & HOD)
        # -------------------------------------------------------------
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            admin_user = User(
                email='admin@example.com',
                username='admin',
                full_name='System Administrator',
                phone='+91 9876500001',
                role_id=roles_map['ADMIN'].id,
                is_active=True
            )
            admin_user.set_password('Admin@12345')
            db.session.add(admin_user)

        hod_user = User.query.filter_by(email='hod.cse@example.com').first()
        if not hod_user:
            hod_user = User(
                email='hod.cse@example.com',
                username='hod_cse',
                full_name='Dr. Alok Verma',
                phone='+91 9876500002',
                role_id=roles_map['HOD'].id,
                is_active=True
            )
            hod_user.set_password('Hod@12345')
            db.session.add(hod_user)

        db.session.commit()

        # -------------------------------------------------------------
        # 4. SAMPLE TEACHER ACCOUNTS (7 Sample Teachers from Spec)
        # -------------------------------------------------------------
        teachers_data = [
            ("HBT", "Harish Bhatt Tripathi", "hbt@example.com", "EMP101"),
            ("RPL", "Rahul Prakash Lal", "rpl@example.com", "EMP102"),
            ("PMA", "Priya Mehta Arora", "pma@example.com", "EMP103"),
            ("SBT", "Sneha Bansal Tyagi", "sbt@example.com", "EMP104"),
            ("DPR", "Deepak Pratap Rawat", "dpr@example.com", "EMP105"),
            ("AJM", "Anjali Joshi Mehta", "ajm@example.com", "EMP106"),
            ("PM", "Pankaj Mishra", "pm@example.com", "EMP107")
        ]

        teacher_map = {}
        for initials, name, email, emp_id in teachers_data:
            t_user = User.query.filter_by(email=email).first()
            if not t_user:
                t_user = User(
                    email=email,
                    username=initials.lower(),
                    full_name=name,
                    phone='+91 9811122233',
                    initials=initials,
                    role_id=roles_map['TEACHER'].id,
                    is_active=True
                )
                t_user.set_password('Teacher@12345')
                db.session.add(t_user)
                db.session.flush()
            else:
                t_user.initials = initials
            teacher_map[initials] = t_user

        db.session.commit()

        # -------------------------------------------------------------
        # 5. BATCH: B.Tech CSE 3rd Year V(C) (Room 5208)
        # -------------------------------------------------------------
        batch_vc = Batch.query.filter_by(batch_code='BTECH-CSE-3C').first()
        if not batch_vc:
            batch_vc = Batch(
                batch_name='B.Tech CSE 3rd Year V(C)',
                batch_code='BTECH-CSE-3C',
                course_name='B.Tech (Computer Science & Engineering)',
                teacher_id=teacher_map['HBT'].id,
                start_date=date(2026, 9, 12),
                status='Active'
            )
            db.session.add(batch_vc)
            db.session.flush()

        # -------------------------------------------------------------
        # 6. SUBJECTS (Official Timetable Curriculum)
        # -------------------------------------------------------------
        subjects_data = [
            ("Fundamentals of TQM", "TQM", "HBT"),
            ("Computer Networks", "CN", "RPL"),
            ("Operating System", "OS", "PMA"),
            ("Software Engineering and QA", "S/W QA", "SBT"),
            ("Data Analysis Using Spreadsheet LAB", "Spreadsheet Lab", "DPR"),
            ("Machine Learning", "ML", "AJM"),
            ("Operating System Lab", "OS Lab", "PMA"),
            ("Computer Networks Lab", "CN Lab", "RPL"),
            ("Practice Lab / Library", "Practice Lab", "PM"),
            ("Computer Networks Tutorial", "CN Tutorial", "RPL"),
            ("Operating System Tutorial", "OS Tutorial", "PMA"),
            ("Software Engineering and QA Tutorial", "S/W QA Tutorial", "SBT")
        ]

        subject_map = {}
        for sname, scode, t_init in subjects_data:
            subj = Subject.query.filter_by(subject_code=scode).first()
            if not subj:
                subj = Subject(
                    subject_name=sname,
                    subject_code=scode,
                    description=f"{sname} ({scode}) for B.Tech CSE 3rd Year",
                    status='Active'
                )
                db.session.add(subj)
                db.session.flush()
            subject_map[scode] = subj

            # Link subject to batch
            bs = BatchSubject.query.filter_by(batch_id=batch_vc.id, subject_id=subj.id).first()
            if not bs:
                t_usr = teacher_map.get(t_init)
                bs = BatchSubject(
                    batch_id=batch_vc.id,
                    subject_id=subj.id,
                    teacher_id=t_usr.id if t_usr else None
                )
                db.session.add(bs)

        db.session.commit()

        # -------------------------------------------------------------
        # 7. OFFICIAL WEEKLY TIMETABLE
        # -------------------------------------------------------------
        tt_version = TimetableVersion.query.filter_by(batch_id=batch_vc.id).first()
        if not tt_version:
            tt_version = TimetableVersion(
                batch_id=batch_vc.id,
                version_name="Official Timetable (Effective 12 Sep 2026)",
                effective_from=date(2026, 9, 12),
                is_active=True
            )
            db.session.add(tt_version)
            db.session.flush()

        p_times = {
            1: (time(9, 0), time(10, 0)),
            2: (time(10, 0), time(11, 0)),
            3: (time(11, 20), time(12, 20)),
            4: (time(12, 20), time(13, 20)),
            5: (time(14, 0), time(15, 0))
        }

        weekly_schedule = {
            "Monday": [
                (1, "TQM", "HBT", "Theory"),
                (2, "CN", "RPL", "Theory"),
                (3, "OS", "PMA", "Theory"),
                (4, "S/W QA", "SBT", "Theory"),
                (5, "Practice Lab", "PM", "Practical")
            ],
            "Tuesday": [
                (1, "CN", "RPL", "Theory"),
                (2, "Spreadsheet Lab", "DPR", "Practical"),
                (3, "S/W QA", "SBT", "Theory"),
                (4, "OS", "PMA", "Theory"),
                (5, "S/W QA Tutorial", "SBT", "Tutorial")
            ],
            "Wednesday": [
                (1, "OS Lab", "PMA", "Practical"),
                (2, "OS Lab", "PMA", "Practical"),
                (3, "TQM", "HBT", "Theory"),
                (4, "ML", "AJM", "Theory"),
                (5, "CN Tutorial", "RPL", "Tutorial")
            ],
            "Thursday": [
                (1, "ML", "AJM", "Theory"),
                (2, "OS", "PMA", "Theory"),
                (3, "CN Lab", "RPL", "Practical"),
                (4, "CN Lab", "RPL", "Practical"),
                (5, "Spreadsheet Lab", "DPR", "Practical")
            ],
            "Friday": [
                (1, "TQM", "HBT", "Theory"),
                (2, "ML", "AJM", "Theory"),
                (3, "S/W QA", "SBT", "Theory"),
                (4, "Practice Lab", "PM", "Practical"),
                (5, "OS Tutorial", "PMA", "Tutorial")
            ],
            "Saturday": [
                (1, "ML", "AJM", "Theory"),
                (2, "CN", "RPL", "Theory"),
                (3, "Spreadsheet Lab", "DPR", "Practical"),
                (4, "Spreadsheet Lab", "DPR", "Practical"),
                (5, None, None, "Free")
            ]
        }

        for day, slots in weekly_schedule.items():
            for p_num, s_code, t_init, p_type in slots:
                existing_slot = Timetable.query.filter_by(
                    version_id=tt_version.id,
                    day_of_week=day,
                    period_number=p_num
                ).first()
                if not existing_slot:
                    st, et = p_times[p_num]
                    sub = subject_map.get(s_code)
                    t_usr = teacher_map.get(t_init)
                    slot = Timetable(
                        version_id=tt_version.id,
                        batch_id=batch_vc.id,
                        day_of_week=day,
                        period_number=p_num,
                        start_time=st,
                        end_time=et,
                        subject_id=sub.id if sub else None,
                        teacher_id=t_usr.id if t_usr else None,
                        room_number="5208",
                        period_type=p_type
                    )
                    db.session.add(slot)

        db.session.commit()

        # -------------------------------------------------------------
        # 8. SAMPLE STUDENTS
        # -------------------------------------------------------------
        students_data = [
            ("24BCSE001", "Deepesh Singh", "deepesh@example.com", "+91 7827865981"),
            ("24BCSE002", "Latesh Sharma", "latesh@example.com", "+91 9876543210"),
            ("24BCSE003", "Aarav Gupta", "aarav@example.com", "+91 9876543211"),
            ("24BCSE004", "Riya Patel", "riya@example.com", "+91 9876543212"),
            ("24BCSE005", "Vikram Malhotra", "vikram@example.com", "+91 9876543213")
        ]

        for roll, sname, semail, sphone in students_data:
            st = Student.query.filter_by(roll_number=roll).first()
            if not st:
                st = Student(
                    roll_number=roll,
                    student_name=sname,
                    email=semail,
                    mobile_number=sphone,
                    admission_date=date(2024, 8, 1),
                    status='Active'
                )
                db.session.add(st)
                db.session.flush()

                # Enroll in Batch V(C)
                bs = BatchStudent(
                    batch_id=batch_vc.id,
                    student_id=st.id,
                    roll_number_in_batch=roll,
                    joined_date=date(2024, 8, 1),
                    status='Active'
                )
                db.session.add(bs)

                # Ensure student user account
                st.ensure_user_account('Student@12345')

        db.session.commit()
        print("Database seeding completed with official B.Tech CSE V(C) Timetable & Faculty!")

    if target_app:
        with target_app.app_context():
            run_seed()
    else:
        run_seed()

if __name__ == '__main__':
    import os
    import sys
    from app import create_app
    config_name = os.environ.get('FLASK_CONFIG') or ('production' if os.environ.get('DATABASE_URL') else 'development')
    standalone_app = create_app(config_name)
    try:
        seed(standalone_app)
    except Exception as e:
        print("Warning: seed encountered an issue but continuing:", e)
        import traceback
        traceback.print_exc()
