# tests/test_admin.py
from app.models import User, Post


def test_admin_can_access_dashboard(client, app):
    """
    GIVEN an admin user
    WHEN they log in and access the admin dashboard
    THEN check that the response is valid
    """
    # Create an admin user
    with app.app_context():
        admin = User(username='admin', email='admin@example.com', is_admin=True,
                     confirmed=True)
        admin.set_password('adminpass')
        db.session.add(admin)
        db.session.commit()

    # Log in as admin
    client.post('/login', data={'username': 'admin', 'password': 'adminpass'},
                follow_redirects=True)

    # Access dashboard
    response = client.get('/admin')
    assert response.status_code == 200
    assert b"Admin Dashboard - Manage Posts" in response.data


def test_admin_can_create_post(client, app):
    """
    GIVEN a logged-in admin
    WHEN they submit the new post form
    THEN check that the post is created in the database
    """
    with app.app_context():
        # Ensure an admin user exists and is logged in
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com',
                         is_admin=True, confirmed=True)
            admin.set_password('adminpass')
            db.session.add(admin)
            db.session.commit()

    client.post('/login', data={'username': 'admin', 'password': 'adminpass'},
                follow_redirects=True)

    # Create a new post
    response = client.post('/admin/post/new', data={
        'title': 'My Test Post',
        'body': 'This is the body of the test post.',
        'tags': 'testing, flask',
        'status': True  # True for 'Publish Immediately'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Your post has been created!" in response.data

    # Verify the post exists in the database
    with app.app_context():
        post = Post.query.filter_by(title='My Test Post').first()
        assert post is not None
        assert post.body == 'This is the body of the test post.'
        assert post.status is True
        assert len(post.tags) == 2
