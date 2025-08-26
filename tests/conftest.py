# tests/conftest.py
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models import User

import pytest
from app import create_app, db
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory DB
    WTF_CSRF_ENABLED = False
    RECAPTCHA_ENABLED = False
    SERVER_NAME = "localhost.localdomain"
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_DEFAULT_SENDER = 'test@example.com'

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for the test session."""
    app = create_app(config_class=TestConfig)
    return app

@pytest.fixture(autouse=True)
def client(app):
    """A test client for the app, with a request context."""
    with app.test_request_context():
        yield app.test_client()

@pytest.fixture(autouse=True)
def _db(app):
    """
    Fixture to set up and tear down the database for each test.
    The 'autouse=True' means this will run for every test function automatically.
    """
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def auth_client(client, app):
    """
    Provides a test client that is already logged in as a confirmed user.
    """
    with app.app_context():
        user = User(username='testuser', email='test@example.com',
                    confirmed=True)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

    client.post('/login', data={'username': 'testuser', 'password': 'password'},
                follow_redirects=True)

    yield client  # The test will run with this client

    # Logout after the test is done to clean up
    client.get('/logout', follow_redirects=True)
