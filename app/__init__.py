# app/__init__.py

import os
from flask import Flask, flash, redirect, url_for
from markupsafe import Markup
import re
from config import Config
from .extensions import db, migrate, login, csrf, mail, limiter
import cloudinary
from flask_wtf.csrf import CSRFError
from .context_processors import inject_sidebar_data
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

def create_app(config_class=Config):
    """The application factory."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.storage_uri = app.config.get('RATELIMIT_STORAGE_URI')    
    limiter.init_app(app)

    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            'https://cdn.jsdelivr.net',
            'https://www.google.com/recaptcha/',
            'https://www.gstatic.com/recaptcha/',
            "'unsafe-inline'"
        ],
        'style-src': [
            "'self'",
            'https://cdn.jsdelivr.net',
            'https://fonts.googleapis.com',
            'https://use.fontawesome.com',
            "'unsafe-inline'"
        ],
        'font-src': [
            "'self'",
            'https://fonts.gstatic.com',
            'https://use.fontawesome.com'
        ],
        'img-src': ["'self'", 'data:', 'https://res.cloudinary.com']
    }

    Talisman(app, content_security_policy=csp, force_https=False)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash("Your session timed out. Please try again.", "info")
        return redirect(url_for('main.index'))

    def highlight(text, query):
        if not query:
            return text
        return Markup(re.sub(f'({re.escape(query)})', r'<mark>\1</mark>', text, flags=re.IGNORECASE))

    app.jinja_env.filters['highlight'] = highlight

    if app.config.get('CLOUDINARY_CLOUD_NAME'):
        cloudinary.config(
            cloud_name=app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=app.config['CLOUDINARY_API_KEY'],
            api_secret=app.config['CLOUDINARY_API_SECRET'],
            secure=True
        )

    app.context_processor(inject_sidebar_data)

    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp)
        from . import models

    return app
