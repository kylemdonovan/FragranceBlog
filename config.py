import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
local_db_path = os.path.join(r"C:\Users\kd2kr\Desktop\fragranceblog",
                             'instance', 'app.db')
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    # --- CORE SETTINGS ---
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-change-this'

    # This line safely uses the Render Postgres DB in production OR your local absolute path.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + local_db_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- TINYMCE CONFIG ---
    TINYMCE_API_KEY = os.environ.get('TINYMCE_API_KEY')

    # --- CLOUDINARY CONFIG ---
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')

    # --- RECAPTCHA ---
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

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
    # These settings are hardcoded to True because the application should
    # only ever be run over HTTPS in production :) .
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    # REMEMBER_COOKIE_SAMESITE is not a standard Flask config, but does no harm.
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # --- APP SPECIFIC SETTINGS ---
    BLOG_NAME = os.environ.get('BLOG_NAME', 'My Fragrance Blog')
    GOOGLE_ANALYTICS_ID = os.environ.get('GOOGLE_ANALYTICS_ID')
    SIDEBAR_RECENT_POSTS_COUNT = 5
    SIDEBAR_POPULAR_TAGS_COUNT = 10
    SIGNUP_RATE_LIMIT = "5 per hour;20 per day"


