# app/__init__.py
import os
import click
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
import cloudinary

# Create extension instances
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
mail = Mail()

limiter = Limiter(key_func=get_remote_address,
                  default_limits=["200 per day", "50 per hour"])

# Configure LoginManager
login.login_view = 'main.login'
login.login_message = 'Please log in to access this page.'
login.login_message_category = 'info'

def create_app(config_class=Config):
    """The application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Configure Cloudinary
    if app.config.get('CLOUDINARY_CLOUD_NAME'):
        cloudinary.config(
            cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=app.config['CLOUDINARY_API_KEY'],
            api_secret=app.config['CLOUDINARY_API_SECRET'],
            secure=True
        )

    # --- Register Blueprints, Context Processors, etc. within app context ---
    with app.app_context():
        from . import routes, models

        # Register Blueprints
        app.register_blueprint(routes.bp)

        # Register Error Handlers
        from app.errors import not_found_error, internal_error
        app.register_error_handler(404, not_found_error)
        app.register_error_handler(500, internal_error)

        # Register Context Processors
        from app.context_processors import inject_sidebar_data
        app.context_processor(inject_sidebar_data)

        @app.cli.command("init-db")
        def init_db_command():
            """Clears existing data and creates new tables."""
            # Ensure the instance folder exists for SQLite
            instance_folder = os.path.dirname(
                app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
            os.makedirs(instance_folder, exist_ok=True)

            db.create_all()
            click.echo("Initialized the database.")

        # --- Shell Context for `flask shell` ---
        @app.shell_context_processor
        def make_shell_context():
            return {'db': db, 'User': models.User, 'Post': models.Post}

    return app
