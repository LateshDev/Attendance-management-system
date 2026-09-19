import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# Ensure instance folder exists
instance_dir = os.path.join(basedir, 'instance')
os.makedirs(instance_dir, exist_ok=True)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-super-secret-key-change-in-production-attendance-system-2026'
    
    # Handle database URL with postgresql:// fix for cloud providers
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_DATABASE_URI = db_url or f"sqlite:///{os.path.join(instance_dir, 'attendance.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder
    UPLOAD_FOLDER = os.path.join(instance_dir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    
    # Default pagination
    ITEMS_PER_PAGE = 15
    
    # Default low attendance threshold
    DEFAULT_LOW_ATTENDANCE_THRESHOLD = 75.0


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'


class ProductionConfig(Config):
    DEBUG = False
    # In production, require secure secret key if not set
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        if not os.environ.get('SECRET_KEY'):
            import warnings
            warnings.warn("SECRET_KEY environment variable is not set! Using fallback.")


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
