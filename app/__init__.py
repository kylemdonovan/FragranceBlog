# app/__init__.py
import os
from flask import Flask
from config import Config  # Assuming Config class is defined in config.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import cloudinary
# import cloudinary.uploader # Not strictly needed here if only using cloudinary.config
# import cloudinary.api    # Not strictly needed here
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

# Create extension instances (without app)
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],  # General default limits
)

# LoginManager configuration
login.login_view = 'main.login'  # The route function name for the login page
login.login_message = 'Please log in to access this page.'
login.login_message_category = 'info'  # Bootstrap class for flash message


def create_app(config_class=Config):
    app = Flask(__name__,
                instance_relative_config=False)  # instance_relative_config=True if config files are in instance folder
    app.config.from_object(config_class)
    instance_folder_path = os.path.join(app.root_path, '..', 'instance')
    try:
        os.makedirs(instance_folder_path, exist_ok=True)
        app.instance_path = instance_folder_path  # Explicitly set instance path
        # app.logger.info(f"Instance path explicitly set to: {app.instance_path}")
    except OSError as e:
        app.logger.error(f"Error creating instance folder at {instance_folder_path}: {e}", exc_info=True)

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)  # Pass db for migrations
    login.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)  # Initialize Limiter with app

    # --- CLOUDINARY INITIALIZATION ---
    # Check if Cloudinary is configured before trying to use it
    if app.config.get('CLOUDINARY_CLOUD_NAME') and \
            app.config.get('CLOUDINARY_API_KEY') and \
            app.config.get('CLOUDINARY_API_SECRET'):
        try:
            cloudinary.config(
                cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
                api_key=app.config['CLOUDINARY_API_KEY'],
                api_secret=app.config['CLOUDINARY_API_SECRET'],
                secure=True  # Use https URLs
            )
            app.logger.info("--- Cloudinary configured successfully. ---")  # Using app.logger
        except Exception as e:
            app.logger.error(f"--- Cloudinary configuration failed: {e} ---", exc_info=True)
    else:
        app.logger.warning(
            "--- Cloudinary not configured (missing one or more API keys/cloud name in config). ---")  # Using app.logger

    # Import and register blueprints
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # --- Import and register Error Handling Blueprint ---
#    from app.errors import bp as errors_bp
#    app.register_blueprint(errors_bp)
    # --- END error handling blueprint ---

    # Import models here to ensure they are known to Flask-Migrate
    # and available for shell context.
    from app import models  # This is good.

    from app.context_processors import inject_sidebar_data
    app.context_processor(inject_sidebar_data)

    # Configure shell context
    @app.shell_context_processor
    def make_shell_context():
        # Add all models and db to the shell context for easy debugging
        return {
            'db': db,
            'User': models.User,
            'Post': models.Post,
            'Comment': models.Comment,
            'Tag': models.Tag  # Added Tag model
            # Add other models here if you create more
        }

    # --- Jinja Global Filters (Example for striptags, truncate for RSS) ---
    import re
    from markupsafe import Markup

    @app.template_filter()
    def striptags_filter(value):  # Renamed to avoid potential conflict with Jinja's internal striptags
        if value is None: return ''
        return Markup(re.sub(r'<[^>]+>', '', str(value)))

    @app.template_filter()
    def truncate_text_filter(value, length=255, end='...'):  # Renamed
        if value is None: return ''
        value_str = str(value)
        if len(value_str) <= length:
            return value_str
        return Markup(value_str[:length - len(end)] + end)  # Markup if we expect HTML output

    # --- END Jinja filters ---


    @app.template_filter()
    def striptags_filter(value):
        if value is None: return ''
        return Markup(re.sub(r'<[^>]+>', '', str(value)))

    @app.template_filter()
    def truncate_text_filter(value, length=255, end='...'):
        if value is None: return ''
        value_str = str(value)
        if len(value_str) <= length:
            return value_str
        return Markup(value_str[:length - len(end)] + end)

    # --- START: HIGHLIGHT FILTER ---
    @app.template_filter('highlight') # Explicitly naming the filter 'highlight'
    def highlight_search_term_filter(text_to_search, query_term):
        """
        Highlights occurrences of query_term in text_to_search.
        Case-insensitive. Marks with <mark> HTML tag.
        """
        if not query_term or not text_to_search:
            return text_to_search #

        text_str = str(text_to_search)
        try:

            escaped_query = re.escape(query_term)

            highlighted_text = re.sub(f'({escaped_query})', r'<mark class="search-highlight">\1</mark>', text_str, flags=re.IGNORECASE)
            return Markup(highlighted_text) # Return as Markup so HTML isn't escaped by Jinja
        except Exception as e:

            if app and hasattr(app, 'logger'):
                 app.logger.error(f"Error during highlighting: {e}", exc_info=True)
            else:
                print(f"Error during highlighting (logger not available): {e}")

            if isinstance(text_to_search, Markup): #
                return text_to_search
            return escape(text_str) #
    # --- END: HIGHLIGHT FILTER ---

    # Replace print with app.logger
    # These logs are good for verifying paths during startup
    app.logger.info(f"Flask App Root Path: {app.root_path}")
    app.logger.info(f"Flask App Instance Path: {app.instance_path}")
    app.logger.info(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    # Log if mail is configured (basic check)
    if app.config.get('MAIL_SERVER'):
        app.logger.info(f"Mail configured with server: {app.config.get('MAIL_SERVER')}")
    else:
        app.logger.warning("Mail not configured (MAIL_SERVER is not set).")

    return app
