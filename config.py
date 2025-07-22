# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # SECRET_KEY is crucial for session security and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-change-this'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    elif not SQLALCHEMY_DATABASE_URI:
        project_root = os.path.dirname(basedir)
        instance_folder_path = os.path.join(project_root, 'instance') # Store DB in instance folder
        os.makedirs(instance_folder_path, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(instance_folder_path, 'app.db')

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

    BLOG_NAME = os.environ.get('BLOG_NAME', 'My Temporarily Named Fragrance Blog')  # For title, navbar, footer
    SIDEBAR_RECENT_POSTS_COUNT = 5
    SIDEBAR_POPULAR_TAGS_COUNT = 10
