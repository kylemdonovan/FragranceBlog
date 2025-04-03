# app/__init__.py
import os
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Create extension instances (without app)
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()

# LoginManager configuration
login.login_view = 'main.login' # The route function name for the login page
login.login_message = 'Please log in to access this page.'
login.login_message_category = 'info' # Bootstrap class for flash message


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False) # Changed instance path handling
    app.config.from_object(config_class)

    # Ensure the instance folder exists
    # We store the SQLite DB here if using default config
    instance_path = os.path.join(app.root_path, '..', 'instance') # Correct path relative to app package
    try:
        os.makedirs(instance_path, exist_ok=True)
        app.instance_path = instance_path # Explicitly set instance path for Flask
    except OSError:
        pass # Or handle error appropriately

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app) # Initialize CSRF protection
    
    # --- ADD CLOUDINARY INITIALIZATION ---
    if app.config.get('CLOUDINARY_CLOUD_NAME'): # Only configure if keys exist
        cloudinary.config(
            cloud_name = app.config['CLOUDINARY_CLOUD_NAME'],
            api_key = app.config['CLOUDINARY_API_KEY'],
            api_secret = app.config['CLOUDINARY_API_SECRET'],
            secure=True # Use https URLs
        )
        print("--- Cloudinary configured. ---")
    else:
        print("--- Cloudinary not configured (missing keys in config). ---")
    
    # Import and register blueprints (or routes directly for simplicity now)
    # We'll use a simple Blueprint structure for organization
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Import models here to ensure they are known to Flask-Migrate
    from app import models

    # Configure shell context (optional, useful for `flask shell`)
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'User': models.User, 'Post': models.Post, 'Comment': models.Comment}

    # Error Handlers (optional but good practice)
    # from app.errors import bp as errors_bp
    # app.register_blueprint(errors_bp)

    print(f"App instance path: {app.instance_path}") # Debug print
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}") # Debug print

    return app
