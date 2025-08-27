# app/models.py
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login
from slugify import slugify as default_slugify
import sqlalchemy as sa
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

# -- Association Table ---
# This table connects posts and tags in many-to-many relations
post_tags = db.Table('post_tags',
                     db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
                     db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
                     )


# -------------------------

# Flask-Login user loader callback
@login.user_loader
def load_user(id):
    # Use db.session.get for primary key lookup, which is efficient, probably
    return db.session.get(User, int(id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)

    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='commenter', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)



    # --- Token Generation & Verification ---
    def get_reset_password_token(self, expires_sec=1800):
        """Generates a secure, timed token for password reset or email confirmation."""
        s = Serializer(current_app.config['SECRET_KEY'], salt='password-reset-salt')
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_sec=1800):
        """Verifies a token and returns the User if valid."""
        s = Serializer(current_app.config['SECRET_KEY'], salt='password-reset-salt')
        try:
            data = s.loads(token, max_age=expires_sec)
        except Exception:
            # This handles bad signatures, expired tokens, etc.
            return None
        user_id = data.get('user_id')
        return db.session.get(User, user_id)

    def __repr__(self):
        return f'<User {self.username}>'


# -- Tag Model ---
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'


# -----------------

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    image_public_id = db.Column(db.String(255), nullable=True)  # <-- NEW FIELD ADDED HERE
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # FIELDS FOR DRAFT/PUBLISH
    status = db.Column(db.Boolean, default=True, nullable=False, index=True)
    published_at = db.Column(db.DateTime, index=True, nullable = True)

    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=post_tags, lazy='select',
                           backref=db.backref('posts', lazy='dynamic'))

    @staticmethod
    def generate_unique_slug(title_to_slugify):
        """Generates a unique slug from a title, appending a counter if needed."""
        base_slug = default_slugify(title_to_slugify)
        if not base_slug:
            base_slug = "post"

        slug_candidate = base_slug
        counter = 1

        while db.session.scalar(
                sa.select(Post.id).filter_by(slug=slug_candidate).limit(1)):
            slug_candidate = f"{base_slug}-{counter}"
            counter += 1
        return slug_candidate

    def __repr__(self):
        return f'<Post {self.title}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} by User {self.user_id} on Post {self.post_id}>'

# === SUBSCRIBER MODEL FOR NEWSLETTER ===
class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    subscribed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Subscriber {self.email}>'
