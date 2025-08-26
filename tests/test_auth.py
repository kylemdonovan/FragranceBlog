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


# in tests/test_auth.py
def test_login_and_logout(client, app):
    """
    GIVEN a confirmed user
    WHEN the '/login' page is posted to with valid credentials
    THEN check that the login is successful and logout works
    """
    # Use the app context to create the user, ensuring it's available for the login request
    with app.app_context():
        # Create a user that is already confirmed
        user = User(username='confirmeduser', email='confirmed@example.com',
                    confirmed=True)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    # Now, outside the context, simulate the user logging in
    response = client.post('/login', data={
        'username': 'confirmeduser',
        'password': 'password123'
    }, follow_redirects=True)

    # Assertions for successful login
    assert response.status_code == 200
    assert b'Hi, confirmeduser!' in response.data
    assert b'Logout' in response.data
    assert b'Sign In' not in response.data  # Make sure Sign In link is gone

    # Test Logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'You have been logged out.' in response.data
    assert b'Sign In' in response.data
    assert b'Hi, confirmeduser!' not in response.data
