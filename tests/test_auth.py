# tests/test_auth.py
from app.models import User, db

def test_signup_page_loads(client):
    """Tests that the signup page loads correctly."""
    response = client.get('/signup')
    assert response.status_code == 200
    assert b"Join Today" in response.data

def test_login_page_loads(client):
    """Tests that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Log In" in response.data

def test_successful_signup(client, app):
    """
    GIVEN a Flask application
    WHEN the '/signup' page is posted to with valid data
    THEN check that the user is created and a confirmation email is simulated
    """
    # Note: We can't actually check the email, but we check for the flash message.
    response = client.post('/signup', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
        'password2': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"A confirmation email has been sent" in response.data

    # Check that the user was actually created in the database
    with app.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.username == 'testuser'

def test_login_and_logout(auth_client):
    """
    GIVEN a logged-in user (from the auth_client fixture)
    WHEN they visit the homepage
    THEN check that they are logged in.
    WHEN they log out
    THEN check that they are logged out.
    """
    # User is already logged in
    # Check that the homepage shows them as logged in.
    response = auth_client.get('/')
    assert response.status_code == 200
    assert b'Hi, testuser!' in response.data # Use the username
    assert b'Logout' in response.data

    # Test the logout.
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out.' in response.data
    assert b'Hi, testuser!' not in response.data
