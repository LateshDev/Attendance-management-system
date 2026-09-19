import os
from app import create_app
from app.models import db

env_mode = os.environ.get('FLASK_ENV', 'development')
app = create_app(env_mode)


@app.cli.command('init-db')
def init_db_command():
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        print("Initialized the database tables.")


@app.cli.command('seed-db')
def seed_db_command():
    """Seed the database with default roles, admin/teacher accounts, and demo data."""
    import seed
    seed.seed()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
