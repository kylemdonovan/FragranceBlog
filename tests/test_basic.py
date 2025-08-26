# tests/test_basic.py
from app import create_app, db

def test_app_exists():
    """
    Tests if the application factory creates an app without crashing.
    """
    app = create_app()
    assert app is not None

def test_homepage_loads(client):
    """
    Tests if the homepage returns a successful (200 OK) response.
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = client.get('/')
    assert response.status_code == 200
    # We can also check that some expected text is on the page
    assert b"Latest Fragrance Reviews" in response.data
    assert b"Subscribe to Liquid Blossom" in response.data
