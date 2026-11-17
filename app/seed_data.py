from datetime import date, time
from app.models import (
    db, User, Department, Course, ClassGroup, Teacher, Student,
    Subject, TeacherSubject, TimetableVersion, Timetable, Holiday
)

def seed_database():
    # Only seed if no Admin user exists
    if User.query.filter_by(role='admin').first():
        return

    print("--- Seeding Initial Database Data ---")

    # 1. Admin User
    admin = User(
        username="admin",
        email="admin@example.com",
        full_name="System Administrator",
        role="admin",
        phone="9876543210"
    )
    admin.set_password("Admin@12345")
    db.session.add(admin)

    # 2. Department
    dept_cse = Department(
        name="Computer Science & Engineering",
        code="CSE",
        description="Department of Computer Science & Engineering"
    )
    db.session.add(dept_cse)
    db.session.flush()

    # 3. HOD User & Profile
    hod_user = User(
        username="hod_cse",
        email="hod.cse@example.com",
        full_name="Dr. Alok Sharma",
        role="hod",
        phone="9876543211"
    )
    hod_user.set_password("Hod@12345")
    db.session.add(hod_user)
    db.session.flush()

    # 4. Course
    course_btech = Course(
        name="Bachelor of Technology",
        code="B.Tech",
        department_id=dept_cse.id,
        duration_years=4
    )
    db.session.add(course_btech)
    db.session.flush()

    # 5. Class: B.Tech CSE 3rd Year V(C)
    class_vc = ClassGroup(
        course_id=course_btech.id,
        department_id=dept_cse.id,
        name="B.Tech CSE 3rd Year",
        section="V(C)",
        semester=5,
        academic_year="2026–27",
        room_number="5208"
    )
    db.session.add(class_vc)
    db.session.flush()

    # 6. Sample Teacher Accounts (7 Sample Teachers)
    teacher_specs = [
        ("HBT", "Harish Bhatt Tripathi", "hbt@example.com", "EMP101"),
        ("RPL", "Rahul Prakash Lal", "rpl@example.com", "EMP102"),
        ("PMA", "Priya Mehta Arora", "pma@example.com", "EMP103"),
        ("SBT", "Sneha Bansal Tyagi", "sbt@example.com", "EMP104"),
        ("DPR", "Deepak Pratap Rawat", "dpr@example.com", "EMP105"),
        ("AJM", "Anjali Joshi Mehta", "ajm@example.com", "EMP106"),
        ("PM", "Pankaj Mishra", "pm@example.com", "EMP107")
    ]

    teacher_map = {}
    for initials, name, email, emp_id in teacher_specs:
        user = User(
            username=initials.lower(),
            email=email,
            full_name=name,
            role="teacher",
            phone="9811122233"
        )
        user.set_password("Teacher@12345")
        db.session.add(user)
        db.session.flush()

        t_prof = Teacher(
            user_id=user.id,
            emp_id=emp_id,
            full_name=name,
            initials=initials,
            department_id=dept_cse.id,
            designation="Assistant Professor"
        )
        db.session.add(t_prof)
        db.session.flush()
        teacher_map[initials] = t_prof

    # 7. Subjects
    subject_specs = [
        ("TQM", "Fundamentals of TQM", "Theory", "HBT"),
        ("CN", "Computer Networks", "Theory", "RPL"),
        ("OS", "Operating System", "Theory", "PMA"),
        ("S/W QA", "Software Engineering and QA", "Theory", "SBT"),
        ("Spreadsheet Lab", "Data Analysis Using Spreadsheet LAB", "Practical", "DPR"),
        ("Machine Learning", "Machine Learning", "Theory", "AJM"),
        ("OS Lab", "Operating System Lab", "Practical", "PMA"),
        ("CN Lab", "Computer Networks Lab", "Practical", "RPL"),
        ("Practice Lab", "Practice Lab / Library", "Practical", "PM"),
        ("CN Tutorial", "Computer Networks Tutorial", "Tutorial", "RPL"),
        ("OS Tutorial", "Operating System Tutorial", "Tutorial", "PMA"),
        ("S/W QA Tutorial", "Software Engineering and QA Tutorial", "Tutorial", "SBT")
    ]

    subject_map = {}
    for code, name, stype, primary_teacher in subject_specs:
        sub = Subject(
            course_id=course_btech.id,
            semester=5,
            code=code,
            name=name,
            type=stype,
            credits=4 if stype == "Theory" else 2
        )
        db.session.add(sub)
        db.session.flush()
        subject_map[code] = sub

        # Map teacher subject allocation
        t_inst = teacher_map.get(primary_teacher)
        if t_inst:
            alloc = TeacherSubject(
                teacher_id=t_inst.id,
                subject_id=sub.id,
                class_id=class_vc.id
            )
            db.session.add(alloc)

    # 8. Timetable Version
    tt_version = TimetableVersion(
        class_id=class_vc.id,
        version_name="Official Timetable (Effective 12 Sep 2026)",
        effective_from=date(2026, 9, 12),
        is_active=True
    )
    db.session.add(tt_version)
    db.session.flush()

    # Periods Definition:
    # Period 1: 09:00 - 10:00
    # Period 2: 10:00 - 11:00
    # Tea Break: 11:00 - 11:20
    # Period 3: 11:20 - 12:20
    # Period 4: 12:20 - 13:20
    # Lunch: 13:20 - 14:00
    # Period 5: 14:00 - 15:00
    p_times = {
        1: (time(9, 0), time(10, 0)),
        2: (time(10, 0), time(11, 0)),
        3: (time(11, 20), time(12, 20)),
        4: (time(12, 20), time(13, 20)),
        5: (time(14, 0), time(15, 0))
    }

    # Weekly Timetable Schedule from Official Requirements:
    # Monday: TQM, CN, OS, S/W QA, Library/Practice Lab
    # Tuesday: CN, Spreadsheet Lab, S/W QA, OS, S/W QA Tutorial
    # Wednesday: OS Lab, OS Lab, TQM, Machine Learning, CN Tutorial
    # Thursday: Machine Learning, OS, CN Lab, CN Lab, Spreadsheet Lab
    # Friday: TQM, Machine Learning, S/W QA, Practice Lab, OS Tutorial
    # Saturday: Machine Learning, CN, Spreadsheet Lab, Spreadsheet Lab, Free
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
            (4, "Machine Learning", "AJM", "Theory"),
            (5, "CN Tutorial", "RPL", "Tutorial")
        ],
        "Thursday": [
            (1, "Machine Learning", "AJM", "Theory"),
            (2, "OS", "PMA", "Theory"),
            (3, "CN Lab", "RPL", "Practical"),
            (4, "CN Lab", "RPL", "Practical"),
            (5, "Spreadsheet Lab", "DPR", "Practical")
        ],
        "Friday": [
            (1, "TQM", "HBT", "Theory"),
            (2, "Machine Learning", "AJM", "Theory"),
            (3, "S/W QA", "SBT", "Theory"),
            (4, "Practice Lab", "PM", "Practical"),
            (5, "OS Tutorial", "PMA", "Tutorial")
        ],
        "Saturday": [
            (1, "Machine Learning", "AJM", "Theory"),
            (2, "CN", "RPL", "Theory"),
            (3, "Spreadsheet Lab", "DPR", "Practical"),
            (4, "Spreadsheet Lab", "DPR", "Practical"),
            (5, None, None, "Free")
        ]
    }

    for day, slots in weekly_schedule.items():
        for period_num, sub_code, t_init, p_type in slots:
            st, et = p_times[period_num]
            sub_id = subject_map[sub_code].id if sub_code else None
            t_id = teacher_map[t_init].id if t_init else None
            
            slot = Timetable(
                version_id=tt_version.id,
                class_id=class_vc.id,
                day_of_week=day,
                period_number=period_num,
                start_time=st,
                end_time=et,
                subject_id=sub_id,
                teacher_id=t_id,
                room_number="5208",
                period_type=p_type
            )
            db.session.add(slot)

    # 9. Sample Students
    student_specs = [
        ("24BCSE001", "Deepesh Singh", "deepesh@example.com"),
        ("24BCSE002", "Latesh Sharma", "latesh@example.com"),
        ("24BCSE003", "Aarav Gupta", "aarav@example.com"),
        ("24BCSE004", "Riya Patel", "riya@example.com"),
        ("24BCSE005", "Vikram Malhotra", "vikram@example.com"),
        ("24BCSE006", "Ananya Verma", "ananya@example.com"),
        ("24BCSE007", "Rohan Joshi", "rohan@example.com")
    ]

    for roll, sname, semail in student_specs:
        s_user = User(
            username=roll.lower(),
            email=semail,
            full_name=sname,
            role="student",
            phone="9876543220"
        )
        s_user.set_password("Student@12345")
        db.session.add(s_user)
        db.session.flush()

        s_prof = Student(
            user_id=s_user.id,
            roll_number=roll,
            enroll_number=f"ENR{roll}",
            full_name=sname,
            class_id=class_vc.id,
            department_id=dept_cse.id,
            semester=5,
            admission_year=2024,
            guardian_phone="9988776655"
        )
        db.session.add(s_prof)

    # 10. Sample Holidays
    holidays = [
        ("Mahatma Gandhi Jayanti", date(2026, 10, 2), date(2026, 10, 2), "National Holiday"),
        ("Dussehra Vacation", date(2026, 10, 19), date(2026, 10, 21), "Festival Break"),
        ("Diwali Break", date(2026, 11, 8), date(2026, 11, 12), "Deepawali Holidays")
    ]
    for hname, hs, he, hdesc in holidays:
        hol = Holiday(
            name=hname,
            start_date=hs,
            end_date=he,
            description=hdesc,
            academic_year="2026–27"
        )
        db.session.add(hol)

    db.session.commit()
    print("--- Database Initialized & Seeded Successfully! ---")

