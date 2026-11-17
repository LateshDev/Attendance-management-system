import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'attendo-pro-secret-key-2026-secure-tech-faculty')
    
    # Database Configuration: MySQL primary, SQLite fallback for local/zero-config
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    
    if db_url:
        # Handle postgresql:// -> postgresql:// or mysql:// -> mysql+pymysql://
        if db_url.startswith('mysql://'):
            db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)
        elif db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        # Check MySQL specific env vars
        mysql_user = os.environ.get('MYSQL_USER')
        mysql_pass = os.environ.get('MYSQL_PASSWORD')
        mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
        mysql_port = os.environ.get('MYSQL_PORT', '3306')
        mysql_db = os.environ.get('MYSQL_DB', 'attendance_system')
        
        if mysql_user and mysql_pass:
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{mysql_user}:{mysql_pass}@{mysql_host}:{mysql_port}/{mysql_db}"
        else:
            # Local SQLite fallback
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'attendance.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Attendance Configuration
    ATTENDANCE_WINDOW_MINUTES = int(os.environ.get('ATTENDANCE_WINDOW_MINUTES', 60))
    MIN_ATTENDANCE_PERCENTAGE = 75.0  # College standard defaulter threshold
    
    # Institution details
    INSTITUTE_NAME = "Faculty of Technology and Computer Applications"
    ACADEMIC_SESSION = "2026–27"
    DEPARTMENT_NAME = "Computer Science & Engineering"

