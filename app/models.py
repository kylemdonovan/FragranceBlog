# app/models.py
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login  # This import is correct
from slugify import slugify as default_slugify
import sqlalchemy as sa
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

# -- Association Table for Posts and Tags ---
post_tags = db.Table('post_tags',
                     db.Column('post_id', db.Integer, db.ForeignKey('post.id'),
                               primary_key=True),
                     db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'),
                               primary_key=True)
                     )


# --- Flask-Login User Loader ---
@login.user_loader
def load_user(id):
    """Loads a user from the database given their ID."""
    return db.session.get(User, int(id))


# === USER MODEL ===
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.Text,
                              nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # --- Fields for Email Confirmation ---
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

    # --- Relationships ---
    posts = db.relationship('Post', backref='author', lazy='dynamic',
                            cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='commenter', lazy='dynamic',
                               cascade="all, delete-orphan")

    def set_password(self, password):
        """Creates a secure hash for the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    # --- Token Generation & Verification ---
    def get_reset_password_token(self, expires_sec=1800):
        """Generates a secure, timed token for password reset or email confirmation."""
        s = Serializer(current_app.config['SECRET_KEY'],
                       salt='password-reset-salt')
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_password_token(token, expires_sec=1800):
        """Verifies a token and returns the User if valid."""
        s = Serializer(current_app.config['SECRET_KEY'],
                       salt='password-reset-salt')
        try:
            data = s.loads(token, max_age=expires_sec)
            user_id = data.get('user_id')
            return db.session.get(User, user_id)
        except Exception:
            return None

    def __repr__(self):
        return f'<User {self.username}>'


# === TAG MODEL ===
class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, index=True, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'


# === POST MODEL ===
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(150), unique=True, index=True, nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    image_public_id = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, index=True,
                          default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # --- Fields for Draft/Publish ---
    status = db.Column(db.Boolean, default=False, nullable=False,
                       index=True)  # Default to draft
    published_at = db.Column(db.DateTime, index=True, nullable=True)

    # --- Relationships ---
    comments = db.relationship('Comment', backref='post', lazy='dynamic',
                               cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary=post_tags, lazy='select',
                           backref=db.backref('posts', lazy='dynamic'))

    @staticmethod
    def generate_unique_slug(title_to_slugify):
        """Generates a unique slug from a title, appending a counter if needed."""
        base_slug = default_slugify(title_to_slugify) or "post"
        slug_candidate = base_slug
        counter = 1
        while db.session.scalar(
                sa.select(Post.id).filter_by(slug=slug_candidate)):
            slug_candidate = f"{base_slug}-{counter}"
            counter += 1
        return slug_candidate

    def __repr__(self):
        return f'<Post {self.title}>'


# === COMMENT MODEL ===
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True,
                          default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'


# === SUBSCRIBER MODEL ===
class Subscriber(db.Model):
    __tablename__ = 'subscribers'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    subscribed_at = db.Column(db.DateTime,
                              default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Subscriber {self.email}>'
