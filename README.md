# Batch-wise Attendance Management System (Attendo Pro)

[![Live Demo](https://img.shields.io/badge/Live_Demo-Online-brightgreen?style=for-the-badge&logo=cloudflare)](https://sides-overnight-scenic-commissioner.trycloudflare.com)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.1-black?style=for-the-badge&logo=flask)](https://palletsprojects.com/p/flask/)
[![Tests Passing](https://img.shields.io/badge/Tests-17_Passing-success?style=for-the-badge&logo=pytest)](tests/)

A complete, production-ready, mobile-first **Batch-wise Attendance Management System** built with **Python 3.12 Flask**, **SQLAlchemy**, **Flask-Login**, **Bootstrap 5**, **Chart.js**, **ReportLab (PDF)**, **openpyxl (Excel)**, and **Progressive Web App (PWA)** capabilities.

---

### 🌐 Live Demo & Instant Access

- **Public Live URL**: **[https://sides-overnight-scenic-commissioner.trycloudflare.com](https://sides-overnight-scenic-commissioner.trycloudflare.com)**
- **Admin Login**: `admin@example.com` / `Admin@12345`
- **Teacher Login**: `teacher@example.com` / `Teacher@12345`

---

## 📸 Application Screenshots & Visual Overview

| **1. Executive Analytics Dashboard** | **2. Mobile-First Attendance Marking** |
|:---:|:---:|
| ![Executive Analytics Dashboard](docs/screenshots/dashboard.png) | ![Mobile-First Attendance Marking](docs/screenshots/mark_attendance.png) |
| *Real-time metrics, 7-day attendance trends, status doughnuts, and active batch cards* | *Batch selector, touch-friendly Present/Absent/Leave buttons & real-time counter* |

| **3. Low Attendance Defaulter Alerts (< 75%)** | **4. Monthly Attendance Register Matrix** |
|:---:|:---:|
| ![Low Attendance Defaulters](docs/screenshots/defaulters_report.png) | ![Monthly Attendance Register](docs/screenshots/monthly_register.png) |
| *Automated threshold defaulters flagging with contact details & 1-click exports* | *Day 1..31 attendance register matrix with sticky student column* |

---

## 1. Key Features

- **Mobile-First Attendance Screen**:
  - Top batch, date, and subject selectors.
  - Large touch-friendly tap buttons (🟢 PRESENT, 🔴 ABSENT, 🟡 LEAVE).
  - Quick action bar: **MARK ALL PRESENT**, **MARK ALL ABSENT**, and **RESET**.
  - Real-time live status counters (Total, Present, Absent, Leave, Unmarked).
  - Pre-save summary confirmation modal with unmarked student detection.
  - Strict duplicate attendance prevention (`Batch + Date + Subject`).
- **Academic Management**:
  - **Batch Management**: Add, edit, archive, assign teacher, enroll/remove students, and map subjects.
  - **Student Directory**: Profile views, attendance statistics, contact info, and bulk CSV/Excel import.
  - **Subject Management**: Curriculum codes, descriptions, and batch mappings.
- **Reports & Analytics Hub**:
  - **Batch Attendance Report**: Complete roster breakdown with attendance %.
  - **Low Attendance Defaulters Report**: Automatically flags students below configurable threshold (default: 75%).
  - **Daily Attendance Report**: Snapshot of all sessions marked on any given date.
  - **Monthly Attendance Register**: Classic Day 1..31 matrix view with sticky student column.
  - **Multi-Format Exports**: 1-click downloads in **PDF** (ReportLab), **Excel** (.xlsx via openpyxl), **CSV**, and clean browser print styles (`@media print`).
- **Leave Management & Auto-Sync**:
  - Submit, review, approve, or reject student leave requests.
  - Approved leaves automatically pre-select "Leave" status with an "Approved Leave" badge on the attendance marking screen.
- **Enterprise Security & Audit**:
  - Role-Based Access Control: **ADMIN** vs. **TEACHER**.
  - Teachers are restricted to their assigned batches and students.
  - Werkzeug password hashing (scrypt / pbkdf2:sha256).
  - CSRF protection enabled across all forms via Flask-WTF.
  - Comprehensive **Audit Trail**: Logs user logins, logouts, attendance marks, and individual student status edits (From: Absent -> To: Present).
- **PWA & Mobile Ready**:
  - Responsive on Android phones, tablets, and desktop.
  - Web App Manifest (`manifest.json`) and Service Worker (`sw.js`) for Add-to-Home-Screen support.

---

## 2. Directory Structure

```
attendance_system/
├── app/
│   ├── __init__.py                 # Application factory (create_app), extensions, error handlers
│   ├── models.py                   # 11 Relational SQLAlchemy models with constraints & relationships
│   ├── forms.py                    # Flask-WTF forms for auth, CRUD, validation, and file uploads
│   ├── routes/
│   │   ├── auth.py                 # Login, logout, change password, user/staff management
│   │   ├── dashboard.py            # Analytics, metric cards, Chart.js trends, low-attendance alerts
│   │   ├── batches.py              # Batch CRUD, student enrollment/removal, teacher assignment
│   │   ├── students.py             # Student CRUD, profile, CSV/Excel bulk import
│   │   ├── subjects.py             # Subject CRUD and batch associations
│   │   ├── attendance.py           # Core attendance screen, quick actions, history, monthly grid
│   │   ├── leaves.py               # Leave requests, approval workflow, auto-attendance sync
│   │   ├── reports.py              # Batch, Low Attendance, Daily, Subject reports + PDF/Excel/CSV
│   │   ├── audit.py                # Audit log viewer for administrators
│   │   └── settings.py             # Configurable parameters (threshold %, institution name)
│   ├── templates/                  # Jinja2 responsive templates (Bootstrap 5.3 + Icons)
│   ├── static/
│   │   ├── css/style.css           # Modern touch-first stylesheet, badges, responsive layout
│   │   ├── js/app.js               # Mobile sidebar toggling, toasts, PWA registration
│   │   ├── js/attendance.js        # Main attendance marking fast touch handlers & summary modal
│   │   ├── js/sw.js                # PWA Service Worker for offline asset caching
│   │   ├── manifest.json           # Web App Manifest
│   │   └── icons/                  # 192x192 and 512x512 PWA application icons
│   └── utils/
│       ├── decorators.py           # @admin_required, @teacher_or_admin_required
│       ├── exporters.py            # ReportLab PDF generator, openpyxl Excel exporter, CSV builder
│       └── audit.py                # Audit log helper
├── tests/                          # Automated Pytest test suite (17 passed)
│   ├── conftest.py                 # Fixtures: in-memory DB, admin client, teacher client
│   ├── test_auth.py                # Login, logout, role access control
│   ├── test_batches.py             # Batch CRUD and enrollment
│   ├── test_students.py            # Student CRUD and CSV import
│   ├── test_attendance.py          # Marking, duplicate prevention, editing, math safety
│   ├── test_reports.py             # PDF, Excel, CSV export endpoints
│   └── test_health.py              # /health endpoint test
├── config.py                       # Configuration classes (Development, Production, Testing)
├── run.py                          # Application entry point with CLI commands
├── seed.py                         # Comprehensive realistic seed data script
├── requirements.txt                # Pinned production and test dependencies
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── Dockerfile                      # Production container image
├── docker-compose.yml              # Local multi-container setup (Flask + PostgreSQL)
└── Procfile                        # Cloud platform entry point (Gunicorn)
```

---

## 3. Demo Login Credentials

The seed script creates realistic demo users:

| Role | Email | Password | Access Level |
|---|---|---|---|
| **Administrator** | `admin@example.com` | `Admin@12345` | Unrestricted (all batches, reports, users, settings, audit) |
| **Teacher** | `teacher@example.com` | `Teacher@12345` | Assigned batches (Commerce Batch A & B), mark attendance, view history |
| **Teacher 2** | `teacher2@example.com` | `Teacher@12345` | Assigned batches (Computer Science Batch A) |

> [!IMPORTANT]
> Change the default administrator and teacher passwords before deploying into a live production environment.

---

## 4. Local Setup on Windows

### Step 1: Clone or Navigate to Project Directory
```powershell
cd C:\Users\admin\.gemini\antigravity-ide\scratch\attendance_system
```

### Step 2: Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the example environment file:
```powershell
copy .env.example .env
```
*(By default, the application runs locally with SQLite at `instance/attendance.db`)*

### Step 5: Initialize & Seed the Database
Populate roles, demo teachers, batches, subjects, students, and 14 days of attendance history:
```powershell
python seed.py
```

### Step 6: Run the Development Server
```powershell
python run.py
```
Open your web browser at: **`http://127.0.0.1:5000`**

---

## 5. Running the Automated Test Suite

Run the full automated pytest suite:
```powershell
.\venv\Scripts\pytest.exe -v
```

All 17 test cases pass covering:
- Login authentication & invalid password handling
- Admin and Teacher role-based access boundaries
- Batch creation and student enrollment
- Student creation and CSV bulk upload
- Attendance marking, duplicate prevention, and session editing
- Math safety: zero division protection and percentage accuracy
- Report generation (PDF, Excel, CSV)
- Production health check endpoint (`/health`)

---

## 6. Running with Docker & PostgreSQL

To run the complete system locally with PostgreSQL:

```bash
# Build and start services in background
docker-compose up -d --build

# Run database migrations and seed demo data inside container
docker-compose exec web python seed.py

# View container logs
docker-compose logs -f web
```
Access the application at `http://localhost:5000`.

---

## 7. Online Deployment Guide

### Deploying to Render / Railway / Heroku / Fly.io

1. **Set Environment Variables**:
   - `SECRET_KEY`: A secure 32-byte random hex string.
   - `DATABASE_URL`: Your managed PostgreSQL connection URL (e.g., `postgresql://user:password@host:5432/dbname`).
   - `FLASK_ENV`: `production`
   - `PORT`: Provided automatically by the host (default: `5000`).

2. **Build & Start Commands**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Release Command**: `python seed.py` (or `flask init-db`)
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 3 --threads 2 --timeout 120 run:app`

3. **Health Check Endpoint**:
   Configure host health check to:
   - Path: `/health`
   - Expected Status: `200`
   - Expected Response: `{"status": "ok"}`

---

## 8. Database Backup & Restore Procedures

### PostgreSQL Production Backup
```bash
# Backup database to a compressed SQL file
pg_dump -U postgres -h localhost -d attendance_db -F c -b -v -f attendance_backup_$(date +%Y%m%d).dump

# Restore from backup
pg_restore -U postgres -h localhost -d attendance_db -v attendance_backup_20260919.dump
```

### SQLite Local Backup
Simply copy the SQLite file located in `instance/attendance.db`:
```powershell
copy instance\attendance.db instance\backups\attendance_backup.db
```

---

## 9. Security Checklist

- [x] Passwords hashed using Werkzeug (`generate_password_hash` / `check_password_hash`).
- [x] CSRF protection enabled on all POST requests via Flask-WTF.
- [x] Parameterized SQL queries via SQLAlchemy ORM (prevents SQL injection).
- [x] Role-based decorators (`@admin_required`, `@teacher_or_admin_required`).
- [x] Teacher access boundary: Teachers can only view/mark their assigned batches.
- [x] Production error handlers (403, 404, 500) that never expose raw stack traces.
- [x] Production container runs as an unprivileged `appuser` (non-root).
- [x] Health check endpoint (`/health`) for cloud monitoring.




