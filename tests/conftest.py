# tests/conftest.py
import sys
import os

sys.path.insert(0,
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app, db
from config import Config


class TestConfig(Config):
    """Configuration for testing, inherits from the main Config."""
    TESTING = True
    # Use a fast, in-memory SQLite database for tests. This is the key.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # Disable CSRF forms for simpler tests
    RECAPTCHA_ENABLED = False  # Disable ReCaptcha during tests
    SERVER_NAME = "localhost.localdomain"  # Allows url_for to work without a request context


@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for the test suite."""
    app = create_app(config_class=TestConfig)

    with app.app_context():
        db.create_all()
        yield app  # This is where the tests will run
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()
