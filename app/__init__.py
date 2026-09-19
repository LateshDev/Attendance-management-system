from flask import Flask, jsonify, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
import os

from config import config
from app.models import db, User, Setting

migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Health Check Endpoint
    @app.route('/health')
    def health():
        return jsonify({"status": "ok"}), 200

    # Mobile App Install Landing Page
    @app.route('/install')
    def app_install():
        return render_template('install.html')

    # Context processors for global template access
    @app.context_processor
    def inject_global_settings():
        threshold = 75.0
        inst_name = "Attendance Management System"
        academic_yr = "2026-2027"
        try:
            val = Setting.get_value('low_attendance_threshold')
            if val:
                threshold = float(val)
            inst = Setting.get_value('institution_name')
            if inst:
                inst_name = inst
            yr = Setting.get_value('academic_session')
            if yr:
                academic_yr = yr
        except Exception:
            pass
        return {
            'now_year': datetime.utcnow().year,
            'low_attendance_threshold': threshold,
            'institution_name': inst_name,
            'academic_session': academic_yr
        }

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.batches import batches_bp
    from app.routes.students import students_bp
    from app.routes.subjects import subjects_bp
    from app.routes.attendance import attendance_bp
    from app.routes.leaves import leaves_bp
    from app.routes.reports import reports_bp
    from app.routes.audit import audit_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(batches_bp, url_prefix='/batches')
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(subjects_bp, url_prefix='/subjects')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(leaves_bp, url_prefix='/leaves')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(audit_bp, url_prefix='/audit')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app
