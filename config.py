# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(basedir, '.env'))

# --- START: HELPER FUNCTION TO FIX THE ERROR ---
def get_database_uri():
    """Determines the database URI, prioritizing DATABASE_URL and falling back to SQLite."""
    uri = os.environ.get('DATABASE_URL')
    if uri and uri.startswith("postgres://"):
        # Correct the prefix for SQLAlchemy compatibility with Render/Heroku
        return uri.replace("postgres://", "postgresql://", 1)
    elif uri:
        # If DATABASE_URL is set for something else (e.g., mysql), just use it
        return uri
    else:
        # Fallback to SQLite for local development
        # 'basedir' is now defined as the project root, so this path is simple and correct.
        instance_folder = os.path.join(basedir, 'instance')
        os.makedirs(instance_folder, exist_ok=True)
        db_path = os.path.join(instance_folder, 'app.db')
        return 'sqlite:///' + db_path
# --- END: HELPER FUNCTION ---


class Config:
    # SECRET_KEY is crucial for session security and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-change-this'

    # --- Database configuration ---
    # MODIFIED: Call the helper function to get the correct URI, removing the complex if/elif block
    SQLALCHEMY_DATABASE_URI = get_database_uri()
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

    SIGNUP_RATE_LIMIT = os.environ.get('SIGNUP_RATE_LIMIT')