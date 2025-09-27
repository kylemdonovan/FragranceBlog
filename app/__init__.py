# app/__init__.py

import os
from flask import Flask, Markup
import re # Import the regular expression module
from config import Config
from .extensions import db, migrate, login, csrf, mail, limiter
import cloudinary

from .context_processors import inject_sidebar_data

def create_app(config_class=Config):
    """The application factory."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # --- Custom Highlight Filter ---
    def highlight(text, query):
        """
        A custom Jinja2 filter to highlight a search query in a block of text.
        """
        if not query:
            return text
        # Use a case-insensitive REGEX!!! to find the query and wrap it in <mark> tags
        # Markup() is used to prevent Jinja from auto-escaping the HTML blah
        return Markup(re.sub(f'({re.escape(query)})', r'<mark>\1</mark>', text, flags=re.IGNORECASE))

    # Register the custom filter with the Jinja2 environment
    app.jinja_env.filters['highlight'] = highlight
    # --- END Custom Highlight Filter ---

    # Configure Cloudinary
    if app.config.get('CLOUDINARY_CLOUD_NAME'):
        cloudinary.config(
            cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=app.config['CLOUDINARY_API_KEY'],
            api_secret=app.config['CLOUDINARY_API_SECRET'],
            secure=True
        )

    app.context_processor(inject_sidebar_data)

    with app.app_context():
        # Import and register blueprints
        from . import routes
        app.register_blueprint(routes.bp)

        # Import models here so that they are registered with SQLAAAAAAlchemy
        from . import models

    return app
