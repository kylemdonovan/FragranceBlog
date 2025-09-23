# tests/test_main.py
import pytest
from app.models import User, Post, Comment, Tag, db
from slugify import slugify

def test_view_single_post(client, app):
    """
    GIVEN a Flask application configured for testing
    WHEN a user views a single published post
    THEN check that the post's content is displayed correctly
    """
    with app.app_context():
        # Setup: Create a user and a post
        user = User(username='testauthor', email='author@test.com', confirmed=True)
        user.set_password('password')
        post = Post(
            title='My First Test Post',
            body='This is the body of the test post.',
            author=user,
            slug='my-first-test-post',
            status=True # Published
        )
        db.session.add_all([user, post])
        db.session.commit()

    # Action: Visit the post's page
    response = client.get(f'/post/{post.slug}')

    # Assert: Check that the page loads and contains the post content
    assert response.status_code == 200
    assert b'My First Test Post' in response.data
    assert b'This is the body of the test post.' in response.data

def test_post_comment(auth_client, app):
    """
    GIVEN a logged-in user (from auth_client fixture)
    WHEN they submit a comment on a post
    THEN check that the comment is saved to the database
    """
    with app.app_context():
        # Setup: Create a post to comment on
        post_author = User.query.filter_by(username='testuser').first()
        post = Post(title='Commentable Post', body='Body.', author=post_author, slug='commentable-post', status=True)
        db.session.add(post)
        db.session.commit()
        post_id = post.id

    # Action: Submit the comment form
    response = auth_client.post(f'/post/commentable-post', data={
        'body': 'This is a test comment.',
        'submit_comment': 'Submit Comment' # Use the correct submit button name
    }, follow_redirects=True)

    # Assert: Check for success message and database entry
    assert response.status_code == 200
    assert b'Your comment has been published.' in response.data
    with app.app_context():
        comment = Comment.query.one()
        assert comment.body == 'This is a test comment.'
        assert comment.post_id == post_id
        assert comment.user_id == post_author.id # 'testuser' has id 1

def test_post_reply(auth_client, app):
    """
    GIVEN a logged-in user and an existing comment
    WHEN they submit a reply to that comment
    THEN check that the reply is saved with the correct parent
    """
    with app.app_context():
        # Setup: Create a user, post, and a top-level comment
        user = User.query.filter_by(username='testuser').first()
        post = Post(title='Reply Post', body='Body.', author=user, slug='reply-post', status=True)
        parent_comment = Comment(body='This is the parent comment.', commenter=user, post=post)
        db.session.add_all([post, parent_comment])
        db.session.commit()
        parent_comment_id = parent_comment.id

    # Action: Submit the reply form
    response = auth_client.post('/post/reply-post', data={
        'body': 'This is a reply.',
        'parent_id': parent_comment_id,
        'submit_reply': 'Submit Reply'
    }, follow_redirects=True)

    # Assert: Check for success message and correct parent_id in DB
    assert response.status_code == 200
    assert b'Your reply has been posted.' in response.data
    with app.app_context():
        reply = Comment.query.filter(Comment.body == 'This is a reply.').one()
        assert reply.parent_id == parent_comment_id

def test_search_posts(client, app):
    """
    GIVEN a Flask application with posts
    WHEN a user searches for a term
    THEN check that only matching posts are returned
    """
    with app.app_context():
        # Setup: Create a user and two posts
        user = User(username='searcher', email='searcher@test.com', confirmed=True)
        user.set_password('password')
        post1 = Post(title='A Post About Python', body='...', author=user, slug='python-post', status=True)
        post2 = Post(title='A Post About Java', body='...', author=user, slug='java-post', status=True)
        db.session.add_all([user, post1, post2])
        db.session.commit()

    # Action: Perform a search for "Python"
    response = client.get('/search?q=Python')

    # Assert: Check that the correct post is in the results
    assert response.status_code == 200
    assert b'A Post About Python' in response.data
    assert b'A Post About Java' not in response.data

def test_tag_page(client, app):
    """
    GIVEN a post associated with a tag
    WHEN a user visits the tag's page
    THEN check that the post is listed
    """
    with app.app_context():
        # Setup: Create user, post, and tag
        user = User(username='tagger', email='tagger@test.com', confirmed=True)
        user.set_password('password')
        tag = Tag(name='testing')
        post = Post(
            title='Tagged Post',
            body='This post is for testing tags.',
            author=user,
            slug='tagged-post',
            status=True
        )
        post.tags.append(tag)
        db.session.add_all([user, post, tag])
        db.session.commit()

    # Action: Visit the tag page
    response = client.get('/tag/testing')

    # Assert: Check that the page loads and contains the tagged post
    assert response.status_code == 200
    assert b'Posts Tagged: <span class="badge bg-secondary">testing</span>' in response.data
    assert b'Tagged Post' in response.data
