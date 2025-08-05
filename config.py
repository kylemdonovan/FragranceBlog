# config.py
import os
from dotenv import load_dotenv

# This is the correct way to define the base directory of the project.
# It assumes config.py is in the project's root folder.
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    # SECRET_KEY is crucial for session security and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key-that-you-should-change'

    # --- Database configuration ---
    # This logic is now simpler and more explicit.
    # 1. Use DATABASE_URL from the environment if it's set (for Render).
    # 2. Otherwise, create a local sqlite database file named 'app.db' in an 'instance' folder.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    elif not SQLALCHEMY_DATABASE_URI:
        instance_folder = os.path.join(basedir, 'instance')
        os.makedirs(instance_folder, exist_ok=True) # Ensure the instance folder exists
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_folder, 'app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable modification tracking (saves resources)

    # --- TINYMCE CONFIG ---
    TINYMCE_API_KEY = os.environ.get('TINYMCE_API_KEY')

    # --- CLOUDINARY CONFIG ---
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

    # --- MAIL ---
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

    # --- COOKIES ---
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # --- APP SPECIFIC SETTINGS ---
    BLOG_NAME = os.environ.get('BLOG_NAME', 'My Temporarily Named Fragrance Blog')
    SIDEBAR_RECENT_POSTS_COUNT = 5
    SIDEBAR_POPULAR_TAGS_COUNT = 10
    SIGNUP_RATE_LIMIT = "5 per hour;20 per day"