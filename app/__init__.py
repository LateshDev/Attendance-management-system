import os
from flask import Flask
from flask_login import LoginManager
from config import Config
from app.models import db, User, Notification

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Context processors
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {
            'app_name': "Attendo Pro",
            'institute_name': app.config.get('INSTITUTE_NAME'),
            'academic_session': app.config.get('ACADEMIC_SESSION'),
            'unread_notifications_count': unread_count
        }

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.hod import hod_bp
    from app.routes.teacher import teacher_bp
    from app.routes.student import student_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(hod_bp, url_prefix='/hod')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    with app.app_context():
        db.create_all()
        # Seed initial data if database is new
        from app.seed_data import seed_database
        seed_database()

    return app

