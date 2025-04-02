# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # SECRET_KEY is crucial for session security and CSRF protection
    # It should be a long, random string.
    # We'll load it from an environment variable for security.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-should-really-change-this'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db') # Store DB in instance folder
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disable modification tracking (saves resources)
    
    
    # Add other configurations here if needed later (e.g., Mail server)
    TINYMCE_API_KEY = os.environ.get('TINYMCE_API_KEY')
