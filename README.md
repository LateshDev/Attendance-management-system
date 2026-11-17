# Attendo Pro — College Attendance Management System
**Faculty of Technology and Computer Applications**  
*Academic Session: 2026–27 | Course: B.Tech (CSE) 3rd Year V(C) | Room: 5208*

---

## 🌟 Overview
**Attendo Pro** is a fully functional, production-ready, responsive web-based Attendance Management System engineered for engineering and technology faculties. It features official timetable-driven attendance scheduling, 4 role-based dashboards, a multi-tier attendance correction and date-modification workflow with HOD authorization, automated percentage tracking, low-attendance defaulter alerts (<75%), and instant PDF/Excel exports.

---

## 🚀 Technology Stack
* **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Chart.js
* **Backend:** Python 3.11+, Flask 3.0+
* **Database & ORM:** MySQL / SQLite fallback with Flask-SQLAlchemy
* **Authentication:** Flask-Login with Werkzeug secure password hashing
* **Reporting:** OpenPyXL (Excel `.xlsx`), ReportLab (Formatted PDF Reports)
* **Production Server:** Gunicorn WSGI

---

## 👥 User Roles & Access Control

| Role | Access & Key Responsibilities |
| :--- | :--- |
| **Admin** | Manage students, teachers, HODs; configure departments, classes, subjects; edit timetable slots & faculty mappings; manage academic holidays; view complete security audit logs; backup database. |
| **HOD** | Department-wide attendance monitoring; authorize/reject attendance corrections; review student leave applications; inspect audit logs. |
| **Teacher** | Access assigned timetable lectures; mark attendance (Present, Absent, Late, Leave); record topics covered; verify student correction requests before HOD review. |
| **Student** | Personal dashboard with overall and subject-wise percentage; defaulter warning notices (<75%); submit correction requests with date modification; submit leave applications. |

---

## 📅 Official Timetable Integration (B.Tech CSE V-C)
* **Class Room:** 5208  
* **Effective Date:** 12 September 2026  
* **Timings:**
  * **Period 1:** 09:00 – 10:00 AM
  * **Period 2:** 10:00 – 11:00 AM
  * **Tea Break:** 11:00 – 11:20 AM
  * **Period 3:** 11:20 AM – 12:20 PM
  * **Period 4:** 12:20 – 01:20 PM
  * **Lunch Break:** 01:20 – 02:00 PM
  * **Period 5:** 02:00 – 03:00 PM

### Weekly Timetable Grid
| Day | Period 1 | Period 2 | Period 3 | Period 4 | Period 5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Monday** | TQM (HBT) | CN (RPL) | OS (PMA) | S/W QA (SBT) | Library / Practice Lab (PM) |
| **Tuesday** | CN (RPL) | Spreadsheet Lab (DPR) | S/W QA (SBT) | OS (PMA) | S/W QA Tutorial (SBT) |
| **Wednesday** | OS Lab (PMA) | OS Lab (PMA) | TQM (HBT) | Machine Learning (AJM) | CN Tutorial (RPL) |
| **Thursday** | Machine Learning (AJM) | OS (PMA) | CN Lab (RPL) | CN Lab (RPL) | Spreadsheet Lab (DPR) |
| **Friday** | TQM (HBT) | Machine Learning (AJM) | S/W QA (SBT) | Practice Lab (PM) | OS Tutorial (PMA) |
| **Saturday** | Machine Learning (AJM) | CN (RPL) | Spreadsheet Lab (DPR) | Spreadsheet Lab (DPR) | Free Period |

---

## 🔑 Demo Login Credentials

| Role | Username / Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@example.com` | `Admin@12345` | Super Administrator |
| **HOD** | `hod.cse@example.com` | `Hod@12345` | Dr. Alok Sharma (HOD CSE) |
| **Teacher (HBT)** | `hbt@example.com` | `Teacher@12345` | Harish Bhatt Tripathi (TQM) |
| **Teacher (RPL)** | `rpl@example.com` | `Teacher@12345` | Rahul Prakash Lal (CN) |
| **Teacher (PMA)** | `pma@example.com` | `Teacher@12345` | Priya Mehta Arora (OS) |
| **Teacher (SBT)** | `sbt@example.com` | `Teacher@12345` | Sneha Bansal Tyagi (S/W QA) |
| **Teacher (DPR)** | `dpr@example.com` | `Teacher@12345` | Deepak Pratap Rawat (Spreadsheet Lab) |
| **Teacher (AJM)** | `ajm@example.com` | `Teacher@12345` | Anjali Joshi Mehta (Machine Learning) |
| **Teacher (PM)** | `pm@example.com` | `Teacher@12345` | Pankaj Mishra (Practice Lab) |
| **Student (Deepesh)** | `deepesh@example.com` | `Student@12345` | Deepesh Singh (Roll: `24BCSE001`) |
| **Student (Latesh)** | `latesh@example.com` | `Student@12345` | Latesh Sharma (Roll: `24BCSE002`) |

---

## 🗄️ Relational Database Schema (17 Tables)
1. `users` — Authentication, hashed credentials, roles, active status.
2. `departments` — Academic departments (CSE, etc.).
3. `courses` — Degree courses (B.Tech, etc.).
4. `classes` — Academic batches, semesters, room numbers.
5. `teachers` — Faculty records, initials, employee IDs.
6. `students` — Student profiles, roll numbers, guardian contact.
7. `subjects` — Course syllabus, theory/lab/tutorial type, credit hours.
8. `teacher_subjects` — Faculty-subject allocations.
9. `timetable_versions` — Timetable versioning and effective date tracking.
10. `timetable` — Day-by-day, period-by-period master schedule.
11. `attendance_sessions` — Conducted lectures, dates, lock status, topics covered.
12. `attendance` — Student-level attendance records (Present/Absent/Late/Leave).
13. `correction_requests` — 4-tier student request & verification pipeline.
14. `attendance_logs` — Immutable audit trail of every modification.
15. `notifications` — Role-based notification alerts.
16. `holidays` — College holidays preventing invalid sessions.
17. `leave_applications` — Student leave requests reviewed by HOD.

---

## 🛠️ Installation & Setup

### 1. Clone or Navigate to the Folder
```bash
cd attendance_system
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate
```

### 3. Install Requirements
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
Open your browser at **`http://localhost:5000`**.  
*The database automatically creates all 17 tables and seeds the official timetable and faculty accounts upon first run!*

---

## ☁️ Deploy to Render
1. Push this folder to a GitHub repository.
2. In your Render Dashboard, click **New + $\rightarrow$ Web Service**.
3. Select your repository.
4. Set:
   * **Runtime:** Python 3
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `gunicorn app:app`
5. Click **Deploy Web Service**!

